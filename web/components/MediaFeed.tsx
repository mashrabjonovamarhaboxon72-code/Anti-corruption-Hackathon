"use client";
import { GlassCard } from "./GlassCard";
import { useMediaFeed, type MediaFeedItem } from "@/hooks/useMediaFeed";
import { timeAgo } from "@/lib/format";

const TIER_LABEL: Record<number, string> = {
  1: "T1",
  2: "T2",
  3: "T3",
  4: "T4",
};

const TIER_TINT: Record<number, string> = {
  1: "border-zinc-500/30 text-zinc-300",
  2: "border-sky-400/30 text-sky-200",
  3: "border-amber-400/30 text-amber-200",
  4: "border-rose-400/30 text-rose-200",
};

function FeedRow({ item }: { item: MediaFeedItem }) {
  return (
    <article className="rounded-xl border border-white/5 bg-white/[0.02] p-4 hover:bg-white/[0.05] transition-colors">
      <header className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span
            className={`px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded border ${
              TIER_TINT[item.tier] ?? TIER_TINT[1]
            }`}
          >
            {TIER_LABEL[item.tier] ?? `T${item.tier}`}
          </span>
          <span className="text-xs text-white/50 font-mono">
            {item.target_department_id ?? "UNSPECIFIED"}
          </span>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-white/40 font-mono">
          <span>trust {item.trust_score.toFixed(2)}</span>
          <span>·</span>
          <span>{timeAgo(item.created_at)}</span>
        </div>
      </header>
      <p className="mt-2 text-sm leading-relaxed text-white/85 text-pretty">
        {item.text}
      </p>
      {item.verification_status && (
        <div className="mt-2 text-[10px] uppercase tracking-wider text-accent-400/80">
          ✓ {item.verification_status}
        </div>
      )}
    </article>
  );
}

export function MediaFeed() {
  const { data, error, isLoading } = useMediaFeed(20);

  return (
    <GlassCard className="p-6 lg:p-7 h-full flex flex-col">
      <div className="flex items-baseline justify-between mb-4">
        <div>
          <div className="text-xs uppercase tracking-[0.18em] text-white/50">
            High-Impact Feed
          </div>
          <div className="mt-1 text-sm text-white/60">
            Tier 3+ reports · trust score above 0.9
          </div>
        </div>
        {data && (
          <div className="text-xs font-mono text-white/40">
            {data.count} item{data.count === 1 ? "" : "s"}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto pr-1 space-y-3 -mr-2">
        {isLoading && !data && (
          <div className="text-sm text-white/40">Loading feed…</div>
        )}
        {error && (
          <div className="text-sm text-red-300/80">
            Couldn&apos;t load /admin/media-feed.
          </div>
        )}
        {data && data.reports.length === 0 && (
          <div className="rounded-xl border border-dashed border-white/10 p-6 text-sm text-white/50 text-center">
            No high-impact reports yet. Verified Tier 3/4 reports with high trust
            land here for transparency broadcasts.
          </div>
        )}
        {data?.reports.map((item) => (
          <FeedRow key={item.report_id} item={item} />
        ))}
      </div>
    </GlassCard>
  );
}
