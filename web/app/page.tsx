import { CivicRoiCounter } from "@/components/CivicRoiCounter";
import { Header } from "@/components/Header";
import { MediaFeed } from "@/components/MediaFeed";
import { QuickReportPortal } from "@/components/QuickReportPortal";

export default function DashboardPage() {
  return (
    <main className="min-h-screen px-6 sm:px-8 lg:px-12 py-8 lg:py-12 max-w-[1600px] mx-auto">
      <Header />

      {/*
        Bento layout:
        - mobile: single column, stacked
        - lg+:    12-col grid
            ROI       spans cols 1..8, rows 1..2  (the headline)
            Feed      spans cols 9..12, rows 1..3 (tall sidebar)
            QuickRep  spans cols 1..8,  rows 3..4 (under ROI)
      */}
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
        zero-knowledge identity · hash-anchored evidence · self-destructing rewards
      </footer>
    </main>
  );
}
