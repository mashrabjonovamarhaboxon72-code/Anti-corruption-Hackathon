"""In-memory sliding-window rate limiter.

This is a deliberately simple defense — every keyed bucket holds the
monotonic timestamps of recent allowed hits inside a deque, and on each
new hit we drop entries older than the window before counting. No Redis,
no Lua, no cluster coordination.

Limitations to know before relying on this in production:

  - Per-process state. With N replicas an attacker gets N × max_attempts
    before being throttled. Promote to Redis or memcached when you scale
    horizontally.
  - In-process memory grows with the number of distinct keys until the
    window-aged entries are dropped on next use of that key. We GC empty
    deques on every call; otherwise the table is bounded by the number
    of distinct keys seen within the window.
  - Keys are caller-supplied (typically the client IP). If your app
    sits behind a reverse proxy, the immediate peer is the proxy and
    every request looks like one client. Wire X-Forwarded-For parsing
    upstream of this limiter, with allowlisted trusted proxies.
"""

from __future__ import annotations

from collections import defaultdict, deque
from functools import wraps
from threading import Lock
from time import monotonic
from typing import Callable

from fastapi import HTTPException, Request


class SlidingWindowRateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int):
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")

        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def hit(self, key: str) -> tuple[bool, int]:
        """Record one hit for `key`. Returns (allowed, retry_after_seconds).

        retry_after_seconds is 0 when the call is allowed; otherwise it
        is the smallest integer number of seconds until the oldest entry
        in the bucket falls out of the window.
        """
        with self._lock:
            now = monotonic()
            cutoff = now - self.window_seconds

            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = deque()
                self._buckets[key] = bucket

            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= self.max_attempts:
                retry_after = int(self.window_seconds - (now - bucket[0])) + 1
                # Don't record a hit for blocked attempts — otherwise an
                # attacker keeps the window pegged forever by polling.
                return False, max(1, retry_after)

            bucket.append(now)
            return True, 0

    def reset(self) -> None:
        """Wipe state. Tests use this; production should not."""
        with self._lock:
            self._buckets.clear()

    def remaining(self, key: str) -> int:
        with self._lock:
            now = monotonic()
            cutoff = now - self.window_seconds
            bucket = self._buckets.get(key)
            if not bucket:
                return self.max_attempts
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            return max(0, self.max_attempts - len(bucket))


def _client_ip(request: Request) -> str:
    """Extract the caller's IP, defaulting to a constant when unknown."""
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def rate_limit(limiter: SlidingWindowRateLimiter, key_fn: Callable[[Request], str] = _client_ip):
    """Decorator that throttles calls to a FastAPI route.

    The decorated function MUST declare `request: Request` in its signature;
    otherwise FastAPI will not inject the Request and we have no key to use.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            request: Request | None = kwargs.get("request")
            if request is None:
                for a in args:
                    if isinstance(a, Request):
                        request = a
                        break
            if request is None:
                # No Request available — fail open rather than break the route.
                # Production should treat this as a configuration error.
                return func(*args, **kwargs)

            key = key_fn(request)
            allowed, retry_after = limiter.hit(key)
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail=(
                        f"Too many attempts. Try again in {retry_after} seconds."
                    ),
                    headers={"Retry-After": str(retry_after)},
                )
            return func(*args, **kwargs)

        return wrapper

    return decorator
