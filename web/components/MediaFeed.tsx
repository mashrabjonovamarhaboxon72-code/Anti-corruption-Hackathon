"use client";
import { CSSProperties } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { useBroadcast } from "@/contexts/BroadcastContext";
import { useMediaFeed, type MediaFeedItem } from "@/hooks/useMediaFeed";
import { tierLabel, timeAgo } from "@/lib/format";

const TIER_STYLE: Record<
  number,
  { ring: string; bg: string; text: string; label: string }
> = {
  1: { ring: "ring-zinc-500/40", bg: "bg-zinc-500/15", text: "text-zinc-200", label: "T1" },
  2: { ring: "ring-sky-400/40", bg: "bg-sky-500/15", text: "text-sky-200", label: "T2" },
  3: { ring: "ring-amber-400/50", bg: "bg-amber-500/15", text: "text-amber-200", label: "T3" },
  4: { ring: "ring-rose-400/60", bg: "bg-rose-500/20", text: "text-rose-100", label: "T4" },
};

function TierBadge({ tier }: { tier: number }) {
  const style = TIER_STYLE[tier] ?? TIER_STYLE[1];
  return (
    <span
      className={[
        "inline-flex items-center justify-center",
        "min-w-[2.25rem] h-7 px-2",
        "rounded-md font-mono font-bold text-sm tracking-tight",
        "ring-1",
        style.ring,
        style.bg,
        style.text,
      ].join(" ")}
    >
      {style.label}
    </span>
  );
}

function VerifiedBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-accent-500/15 ring-1 ring-accent-400/40 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-accent-400">
      <svg
        viewBox="0 0 16 16"
        className="w-3 h-3"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden
      >
        <path d="M3 8.5l3.5 3.5L13 5" />
      </svg>
      Verified
    </span>
  );
}

/* ============================================================
   Standard Bento variant — technical, dense, with metadata
   ============================================================ */

function FeedRow({ item, index }: { item: MediaFeedItem; index: number }) {
  return (
    <motion.article
      layout
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -12 }}
      transition={{ duration: 0.35, delay: index * 0.06, ease: "easeOut" }}
      className="rounded-xl border border-white/5 bg-white/[0.025] p-4 hover:bg-white/[0.05] transition-colors"
    >
      <header className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <TierBadge tier={item.tier} />
          <div className="flex flex-col">
            <span className="text-xs font-mono text-white/70">
              {item.target_department_id ?? "UNSPECIFIED"}
            </span>
            <span className="text-[10px] font-mono text-white/40">
              trust {item.trust_score.toFixed(2)} · {timeAgo(item.created_at)}
            </span>
          </div>
        </div>
        {item.verification_status === "Verified" && <VerifiedBadge />}
      </header>
      <p className="mt-3 text-sm leading-relaxed text-white/85 text-pretty">
        {item.text}
      </p>
    </motion.article>
  );
}

/* ============================================================
   Broadcast variant — slow vertical marquee, no tech metadata
   ============================================================ */

function BroadcastCase({ item }: { item: MediaFeedItem }) {
  // Department names without the DEPT- prefix or hyphens, title-cased.
  const dept = (item.target_department_id ?? "Government Agency")
    .replace(/^DEPT-/i, "")
    .replace(/[-_]/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <article className="px-6 py-8 sm:px-10 sm:py-12 max-w-4xl">
      <div className="text-xs sm:text-sm uppercase tracking-[0.4em] text-accent-400/80">
        {tierLabel(item.tier)}
      </div>
      <div className="mt-3 text-2xl sm:text-3xl font-medium tracking-tight text-white/95">
        {dept}
      </div>
      <p className="mt-5 text-lg sm:text-xl leading-relaxed text-white/80 text-pretty">
        {item.text}
      </p>
    </article>
  );
}

function BroadcastFeed({ reports }: { reports: MediaFeedItem[] }) {
  // Pace: ~10s per item is comfortable for camera readability.
  const durationSeconds = Math.max(40, reports.length * 10);
  const style = { "--marquee-duration": `${durationSeconds}s` } as CSSProperties;

  if (reports.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-white/40 text-sm uppercase tracking-[0.3em]">
          Awaiting verified cases
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-full overflow-hidden">
      {/* Top + bottom fade-outs so items appear/disappear gracefully on camera. */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-ink-950 to-transparent z-10" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-ink-950 to-transparent z-10" />

      <div
        className="animate-broadcast-marquee will-change-transform hover:[animation-play-state:paused]"
        style={style}
      >
        {/* Duplicate the list so the -50% loop in the keyframes is seamless. */}
        {[...reports, ...reports].map((item, i) => (
          <BroadcastCase
            key={`${item.report_id}-${i < reports.length ? "a" : "b"}`}
            item={item}
          />
        ))}
      </div>
    </div>
  );
}

/* ============================================================ */

export function MediaFeed() {
  const { data, error, isLoading } = useMediaFeed(5);
  const { isBroadcast } = useBroadcast();

  if (isBroadcast) {
    return (
      <div className="h-full flex flex-col">
        <div className="text-center mb-4">
          <div className="text-xs uppercase tracking-[0.4em] text-white/40">
            Recent Verified Cases
          </div>
        </div>
        <div className="flex-1 min-h-0">
          {error && (
            <div className="text-sm text-white/50 text-center">
              Feed temporarily unavailable.
            </div>
          )}
          {data && <BroadcastFeed reports={data.reports} />}
          {isLoading && !data && (
            <div className="text-sm text-white/40 text-center">Loading…</div>
          )}
        </div>
      </div>
    );
  }

  return (
    <GlassCard className="p-6 lg:p-7 h-full flex flex-col">
      <div className="flex items-baseline justify-between mb-4">
        <div>
          <div className="text-xs uppercase tracking-[0.18em] text-white/50">
            Transparency Feed
          </div>
          <div className="mt-1 text-sm text-white/60">
            Latest 5 high-impact reports · Tier 3+ · trust above 0.9
          </div>
        </div>
        {data && (
          <div className="text-[10px] font-mono uppercase tracking-wider text-white/40">
            {data.count} live
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto pr-1 -mr-2">
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
            No high-impact reports yet. Verified Tier&nbsp;3/4 reports with high
            trust land here for transparency broadcasts.
          </div>
        )}
        <div className="space-y-3">
          <AnimatePresence initial={false}>
            {data?.reports.slice(0, 5).map((item, i) => (
              <FeedRow key={item.report_id} item={item} index={i} />
            ))}
          </AnimatePresence>
        </div>
      </div>
    </GlassCard>
  );
}
