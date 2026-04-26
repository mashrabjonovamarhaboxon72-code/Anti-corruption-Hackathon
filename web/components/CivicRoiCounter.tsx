"use client";
import { useEffect, useRef, useState } from "react";
import { animate, motion, useMotionValue, useTransform } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { usePublicStats } from "@/hooks/usePublicStats";
import { formatCount, formatUZS } from "@/lib/format";

/**
 * Rolling counter via framer-motion's MotionValue. We tween a numeric
 * MotionValue and project it through useTransform into a formatted string,
 * then render with a non-React-state motion.span — the DOM updates run on
 * framer's animation loop without re-rendering the whole tree.
 *
 * `animate(motionValue, target, ...)` returns an Animation handle that we
 * cancel on cleanup so successive SWR refreshes don't stack tweens.
 */
function RollingNumber({ value, durationSeconds = 1.8 }: { value: number; durationSeconds?: number }) {
  const motionValue = useMotionValue(0);
  const formatted = useTransform(motionValue, (latest) => formatUZS(Math.round(latest)));

  useEffect(() => {
    const controls = animate(motionValue, value, {
      duration: durationSeconds,
      ease: [0.16, 1, 0.3, 1], // ease-out-expo-ish; punchy at start, smooth landing
    });
    return controls.stop;
  }, [value, durationSeconds, motionValue]);

  return <motion.span>{formatted}</motion.span>;
}

export function CivicRoiCounter() {
  const { data, isLoading, error } = usePublicStats();
  const target = data?.civic_roi_summary.total_estimated_funds_protected ?? 0;

  // Pulse the headline for ~600ms whenever the value changes (subtle glow).
  const [pulseKey, setPulseKey] = useState(0);
  const lastValueRef = useRef(target);
  useEffect(() => {
    if (target !== lastValueRef.current) {
      lastValueRef.current = target;
      setPulseKey((k) => k + 1);
    }
  }, [target]);

  return (
    <GlassCard className="p-8 lg:p-10 h-full flex flex-col justify-between">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs uppercase tracking-[0.18em] text-white/50">
            Civic ROI · Public Funds Protected
          </div>
          <div className="mt-2 text-sm text-white/60">
            Estimated impact across Verified reports.
          </div>
        </div>
        <div className="hidden sm:flex items-center gap-2 text-xs text-white/40">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent-400 animate-pulse" />
          live · 30s refresh
        </div>
      </div>

      <div className="my-6">
        <motion.div
          key={pulseKey}
          initial={{ opacity: 0.6, filter: "drop-shadow(0 0 0 rgba(52,211,153,0))" }}
          animate={{
            opacity: 1,
            filter: [
              "drop-shadow(0 0 0 rgba(52,211,153,0))",
              "drop-shadow(0 0 24px rgba(52,211,153,0.45))",
              "drop-shadow(0 0 0 rgba(52,211,153,0))",
            ],
          }}
          transition={{ duration: 0.9, ease: "easeOut" }}
          className="font-mono text-4xl sm:text-6xl lg:text-7xl xl:text-8xl tabular-nums tracking-tight bg-gradient-to-br from-white via-white to-accent-400 bg-clip-text text-transparent"
        >
          {error ? "—" : <RollingNumber value={target} />}
        </motion.div>
        <div className="mt-2 text-sm text-white/50">
          {data?.civic_roi_summary.currency ?? "UZS"}
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {(data?.civic_roi_summary.by_tier ?? []).map((t) => (
          <motion.div
            key={t.tier}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 + t.tier * 0.05 }}
            className="rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2.5"
          >
            <div className="flex items-baseline justify-between">
              <span className="text-xs uppercase tracking-wider text-white/40">
                Tier&nbsp;{t.tier}
              </span>
              <span className="font-mono text-sm tabular-nums text-white/80">
                {formatCount(t.verified_report_count)}
              </span>
            </div>
            <div className="mt-1 text-[10px] font-mono text-white/30">
              × {formatUZS(t.impact_per_report_uzs)}
            </div>
          </motion.div>
        ))}
      </div>

      {isLoading && !data && (
        <div className="mt-4 text-xs text-white/40">Loading from /public/stats…</div>
      )}
      {error && (
        <div className="mt-4 text-xs text-red-300/80">
          Couldn&apos;t reach {process.env.NEXT_PUBLIC_API_URL ?? "the API"}. Is the FastAPI server running?
        </div>
      )}
    </GlassCard>
  );
}
