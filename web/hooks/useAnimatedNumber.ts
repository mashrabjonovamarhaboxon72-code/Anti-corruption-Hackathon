"use client";
import { useEffect, useRef, useState } from "react";

/**
 * rAF-based ease-out cubic interpolation between successive `target` values.
 * Returns the integer current value. Reuses the previous value on retarget so
 * counters don't snap back to zero when stats refresh.
 */
export function useAnimatedNumber(target: number, durationMs = 1500): number {
  const [current, setCurrent] = useState<number>(0);
  const fromRef = useRef<number>(0);
  const startRef = useRef<number | null>(null);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    fromRef.current = current;
    startRef.current = null;
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);

    const tick = (now: number) => {
      if (startRef.current === null) startRef.current = now;
      const elapsed = now - startRef.current;
      const progress = Math.min(1, elapsed / durationMs);
      const eased = 1 - Math.pow(1 - progress, 3);
      const value = fromRef.current + (target - fromRef.current) * eased;
      setCurrent(Math.round(value));
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        rafRef.current = null;
      }
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, durationMs]);

  return current;
}
