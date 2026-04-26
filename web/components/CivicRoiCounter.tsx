"use client";
import { GlassCard } from "./GlassCard";
import { useAnimatedNumber } from "@/hooks/useAnimatedNumber";
import { usePublicStats } from "@/hooks/usePublicStats";
import { formatCount, formatUZS } from "@/lib/format";

export function CivicRoiCounter() {
  const { data, isLoading, error } = usePublicStats();
  const target = data?.civic_roi_summary.total_estimated_funds_protected ?? 0;
  const animated = useAnimatedNumber(target, 1800);

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
        <div className="font-mono text-4xl sm:text-6xl lg:text-7xl xl:text-8xl tabular-nums tracking-tight bg-gradient-to-br from-white via-white to-accent-400 bg-clip-text text-transparent">
          {error ? "—" : formatUZS(animated)}
        </div>
        <div className="mt-2 text-sm text-white/50">
          {data?.civic_roi_summary.currency ?? "UZS"}
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {(data?.civic_roi_summary.by_tier ?? []).map((t) => (
          <div
            key={t.tier}
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
          </div>
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
