"use client";
import { CivicRoiCounter } from "@/components/CivicRoiCounter";
import { Header } from "@/components/Header";
import { MediaFeed } from "@/components/MediaFeed";
import { QuickReportPortal } from "@/components/QuickReportPortal";
import { useBroadcast } from "@/contexts/BroadcastContext";

export default function DashboardPage() {
  const { isBroadcast } = useBroadcast();

  if (isBroadcast) {
    return <BroadcastView />;
  }
  return <BentoView />;
}

/**
 * Standard Bento dashboard.
 *   ROI       — cols 1..8, rows 1..2 (headline)
 *   Feed      — cols 9..12, rows 1..3 (tall sidebar)
 *   QuickRep  — cols 1..8,  rows 3..4 (under ROI)
 */
function BentoView() {
  return (
    <main className="min-h-screen px-6 sm:px-8 lg:px-12 py-8 lg:py-12 max-w-[1600px] mx-auto">
      <Header />
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 lg:gap-6 lg:auto-rows-[minmax(180px,auto)]">
        <div className="lg:col-span-8 lg:row-span-2">
          <CivicRoiCounter />
        </div>
        <div className="lg:col-span-4 lg:row-span-3">
          <MediaFeed />
        </div>
        <div className="lg:col-span-8 lg:row-span-1">
          <QuickReportPortal />
        </div>
      </div>
      <footer className="mt-10 text-center text-[11px] font-mono text-white/30">
        zero-knowledge identity · hash-anchored evidence · self-destructing
        rewards
      </footer>
    </main>
  );
}

/**
 * Broadcast layout — viewport-sized, no Quick Report tile, no footer
 * chrome, no API URL pill. ROI hero takes the dominant top section; the
 * High-Impact Feed scrolls slowly underneath as a vertical marquee. The
 * header still renders so the operator can exit, but everything else
 * irrelevant to a viewer is suppressed.
 */
function BroadcastView() {
  return (
    <main className="h-screen flex flex-col px-4 sm:px-8 py-4 sm:py-6 max-w-[1800px] mx-auto">
      <Header />
      <section className="flex-1 grid grid-rows-[3fr_2fr] gap-4 min-h-0">
        <div className="min-h-0 flex">
          <CivicRoiCounter />
        </div>
        <div className="min-h-0">
          <MediaFeed />
        </div>
      </section>
    </main>
  );
}
