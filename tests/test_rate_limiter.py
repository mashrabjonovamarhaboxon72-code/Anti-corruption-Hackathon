import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from app.services.rate_limiter import SlidingWindowRateLimiter


def test_first_n_attempts_allowed():
    rl = SlidingWindowRateLimiter(max_attempts=5, window_seconds=60)
    for _ in range(5):
        allowed, _ = rl.hit("ip-A")
        assert allowed is True


def test_attempt_n_plus_one_blocked_with_retry_after():
    rl = SlidingWindowRateLimiter(max_attempts=5, window_seconds=60)
    for _ in range(5):
        rl.hit("ip-A")
    allowed, retry_after = rl.hit("ip-A")
    assert allowed is False
    assert retry_after >= 1
    assert retry_after <= 60


def test_distinct_keys_track_independently():
    rl = SlidingWindowRateLimiter(max_attempts=2, window_seconds=60)
    assert rl.hit("ip-A")[0] is True
    assert rl.hit("ip-A")[0] is True
    assert rl.hit("ip-A")[0] is False  # A blocked
    assert rl.hit("ip-B")[0] is True   # B unaffected
    assert rl.hit("ip-B")[0] is True
    assert rl.hit("ip-B")[0] is False


def test_window_slides_after_expiry():
    rl = SlidingWindowRateLimiter(max_attempts=2, window_seconds=1)
    assert rl.hit("ip-A")[0] is True
    assert rl.hit("ip-A")[0] is True
    assert rl.hit("ip-A")[0] is False  # blocked
    time.sleep(1.05)  # window expires
    assert rl.hit("ip-A")[0] is True   # re-allowed


def test_blocked_attempts_do_not_extend_window():
    """If polling kept extending the window, an attacker would be locked
    out perpetually. Blocked hits must NOT be recorded."""
    rl = SlidingWindowRateLimiter(max_attempts=2, window_seconds=1)
    rl.hit("ip-A"); rl.hit("ip-A")
    # Hammer the limiter while blocked
    for _ in range(10):
        allowed, _ = rl.hit("ip-A")
        assert allowed is False
    time.sleep(1.05)
    # Should be unblocked exactly window_seconds after the 2nd ALLOWED hit,
    # not window_seconds after the most recent blocked hit.
    assert rl.hit("ip-A")[0] is True


def test_remaining_reflects_current_state():
    rl = SlidingWindowRateLimiter(max_attempts=5, window_seconds=60)
    assert rl.remaining("ip-A") == 5
    rl.hit("ip-A"); rl.hit("ip-A")
    assert rl.remaining("ip-A") == 3
    for _ in range(3):
        rl.hit("ip-A")
    assert rl.remaining("ip-A") == 0


def test_reset_clears_state():
    rl = SlidingWindowRateLimiter(max_attempts=2, window_seconds=60)
    rl.hit("ip-A"); rl.hit("ip-A")
    assert rl.hit("ip-A")[0] is False
    rl.reset()
    assert rl.hit("ip-A")[0] is True


def test_validators_reject_bad_config():
    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(max_attempts=0, window_seconds=60)
    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(max_attempts=5, window_seconds=0)
