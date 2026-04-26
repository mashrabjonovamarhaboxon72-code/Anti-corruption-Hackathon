"use client";
import { useMemo, useRef, useState } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { CodeSnippetOverlay } from "./CodeSnippetOverlay";
import { useBroadcast } from "@/contexts/BroadcastContext";
import { SNIPPETS, type CodeSnippet } from "@/lib/codeSnippets";

/*
  WorkflowExplorer — the demo's narrative spine.

  Layout: glassmorphic vertical timeline on a deep-charcoal (#0a0a0a)
  base. A vertical rail runs down the left; an Integrity Green
  (#00ff88) line draws itself downward as the user scrolls, in
  lockstep with scrollYProgress so the line never overshoots or lags
  the reader's gaze.

  Per stage:
    - Plain-language one-liner for citizens
    - "Technical Deep-Dive" button revealing the actual backend code
      behind that step (real excerpt, not pseudocode)

  Broadcast mode:
    - Buttons + tooltips disappear (the camera doesn't tap UI)
    - Transition durations stretch ~3× for cinematic pacing
    - Card variants reveal more deliberately, one at a time
*/

interface Stage {
  id: string;
  number: string;
  title: string;
  citizen: string;
  insight: string;
  snippetId: string;
}

const STAGES: Stage[] = [
  {
    id: "anonymous-signup",
    number: "01",
    title: "Anonymous Sign-Up",
    citizen:
      "Register with your national ID. The system gives you back a private identifier — your real ID is never stored.",
    insight: "Powered by HMAC-SHA256",
    snippetId: "anonymous-signup",
  },
  {
    id: "recovery-phrase",
    number: "02",
    title: "Save Your Recovery Phrase",
    citizen:
      "You'll see 24 words once. Write them down — it's the only way back into your account if you lose your session.",
    insight: "BIP39 Enabled",
    snippetId: "recovery-phrase",
  },
  {
    id: "evidence-upload",
    number: "03",
    title: "Upload Evidence Safely",
    citizen:
      "Drop in a photo. We strip location and any hidden camera info before saving — your image becomes pixels and nothing else.",
    insight: "Hash-Anchored Sanitization",
    snippetId: "evidence-upload",
  },
  {
    id: "submit-report",
    number: "04",
    title: "Submit a Report",
    citizen:
      "Describe what happened. The system checks if anyone else has reported the same case so duplicates don't waste auditor time.",
    insight: "ML Duplicate Detection",
    snippetId: "submit-report",
  },
  {
    id: "auditor-review",
    number: "05",
    title: "Independent Auditor Review",
    citizen:
      "An auditor from outside the department reviews your report. The system blocks anyone with a conflict of interest before they can see it.",
    insight: "COI-Screened Assignment",
    snippetId: "auditor-review",
  },
  {
    id: "earn-points",
    number: "06",
    title: "Earn Reputation-Weighted Points",
    citizen:
      "Verified reports earn you points. Trustworthy reporters get more per report than first-timers; bad reports cost you reputation.",
    insight: "RI-Weighted Scoring",
    snippetId: "earn-points",
  },
  {
    id: "redeem-privately",
    number: "07",
    title: "Redeem Rewards Privately",
    citizen:
      "Spend points on real benefits. After you use a voucher, the link between you and that voucher is permanently destroyed.",
    insight: "Self-Destructing Audit Logs",
    snippetId: "redeem-privately",
  },
];

interface StageCardProps {
  stage: Stage;
  isBroadcast: boolean;
  onDeepDive: (stage: Stage) => void;
}

function StageCard({ stage, isBroadcast, onDeepDive }: StageCardProps) {
  // Broadcast pacing: ~3× slower transitions, gentler thresholds, and an
  // amount=0.6 viewport so a card "lights up" once it's clearly center-frame.
  const cardDuration = isBroadcast ? 1.6 : 0.55;
  const badgeDelay = isBroadcast ? 0.55 : 0.18;
  const viewportAmount = isBroadcast ? 0.6 : 0.4;

  return (
    <motion.div
      initial="hidden"
      whileInView="visible"
      viewport={{ once: false, amount: viewportAmount, margin: "-8% 0px -8% 0px" }}
      variants={{
        hidden: {
          borderColor: "rgba(255,255,255,0.08)",
          backgroundColor: "rgba(10,10,10,0.55)",
          boxShadow: "0 0 0 0 rgba(0,255,136,0)",
          y: 16,
          opacity: 0.4,
        },
        visible: {
          borderColor: "#00ff88",
          backgroundColor: "rgba(0,255,136,0.04)",
          // Outer glow + drop-shadow for the "lit" state
          boxShadow:
            "0 8px 36px -12px rgba(0,255,136,0.35), 0 0 0 1px rgba(0,255,136,0.12) inset",
          y: 0,
          opacity: 1,
          transition: { duration: cardDuration, ease: [0.16, 1, 0.3, 1] },
        },
      }}
      className="relative rounded-2xl border backdrop-blur-xl p-6 sm:p-7 overflow-hidden"
    >
      {/* Subtle internal radial — gives the glassmorphic plate some interior depth. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.08]"
        style={{
          background:
            "radial-gradient(60% 80% at 0% 0%, #00ff88 0%, transparent 50%)",
        }}
      />

      {/* Numbered chip — sits on the left, overlapping the connecting rail. */}
      <motion.div
        variants={{
          hidden: {
            backgroundColor: "rgba(10,10,10,0.85)",
            color: "rgba(255,255,255,0.50)",
            borderColor: "rgba(255,255,255,0.10)",
            scale: 0.95,
          },
          visible: {
            backgroundColor: "rgba(0,255,136,0.18)",
            color: "#00ff88",
            borderColor: "#00ff88",
            scale: 1,
            transition: { duration: cardDuration * 0.7 },
          },
        }}
        className="absolute -left-[44px] top-7 hidden sm:flex w-9 h-9 rounded-full border items-center justify-center font-mono text-xs font-semibold"
      >
        {stage.number}
      </motion.div>

      <div className="relative">
        <div className="flex items-baseline gap-2 flex-wrap">
          <span className="sm:hidden font-mono text-xs text-integrity">
            {stage.number}
          </span>
          <h3 className="text-lg sm:text-xl font-medium tracking-tight text-white">
            {stage.title}
          </h3>
        </div>

        <p className="mt-3 text-sm sm:text-[15px] leading-relaxed text-white/75 text-pretty">
          {stage.citizen}
        </p>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <motion.div
            variants={{
              hidden: { opacity: 0, y: 8 },
              visible: {
                opacity: 1,
                y: 0,
                transition: { duration: cardDuration * 0.7, delay: badgeDelay, ease: "easeOut" },
              },
            }}
            className="inline-flex items-center gap-1.5 rounded-full border border-integrity/40 bg-integrity/10 px-3 py-1 text-[10px] font-mono uppercase tracking-[0.15em] text-integrity"
          >
            <span
              aria-hidden
              className="inline-block w-1.5 h-1.5 rounded-full bg-integrity animate-pulse"
            />
            {stage.insight}
          </motion.div>

          {!isBroadcast && (
            <motion.button
              type="button"
              onClick={() => onDeepDive(stage)}
              variants={{
                hidden: { opacity: 0, y: 8 },
                visible: {
                  opacity: 1,
                  y: 0,
                  transition: { duration: 0.4, delay: badgeDelay + 0.08, ease: "easeOut" },
                },
              }}
              className="inline-flex items-center gap-1.5 rounded-full border border-white/15 hover:border-integrity/40 bg-white/[0.03] hover:bg-integrity/10 px-3 py-1 text-[11px] text-white/70 hover:text-integrity transition-colors"
            >
              <svg viewBox="0 0 16 16" width="11" height="11" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
                <path d="M5.5 2L2 8l3.5 6M10.5 2L14 8l-3.5 6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Technical Deep-Dive
            </motion.button>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export function WorkflowExplorer() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { isBroadcast } = useBroadcast();
  const [openStage, setOpenStage] = useState<Stage | null>(null);

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start 0.85", "end 0.15"],
  });
  const lineHeight = useTransform(scrollYProgress, [0, 1], ["0%", "100%"]);

  const activeSnippet: CodeSnippet | null = useMemo(
    () => (openStage ? SNIPPETS[openStage.snippetId] ?? null : null),
    [openStage],
  );

  return (
    <section
      ref={containerRef}
      className="mt-20 sm:mt-28 mb-16 max-w-3xl mx-auto"
      aria-label="Workflow Explorer"
    >
      <header className="text-center mb-12 sm:mb-16">
        <div className="text-xs uppercase tracking-[0.4em] text-integrity">
          Workflow Explorer
        </div>
        <h2 className="mt-3 text-3xl sm:text-4xl font-semibold tracking-tight text-balance">
          Seven stages,
          <span className="block text-white/60 font-normal mt-1">
            built so we can&apos;t identify you even if we wanted to.
          </span>
        </h2>
        {!isBroadcast && (
          <p className="mt-4 text-sm text-white/40">
            Tap any stage&apos;s{" "}
            <span className="inline-flex items-center gap-1 align-middle text-white/60">
              <svg viewBox="0 0 16 16" width="10" height="10" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
                <path d="M5.5 2L2 8l3.5 6M10.5 2L14 8l-3.5 6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Technical Deep-Dive
            </span>{" "}
            to see the actual backend code.
          </p>
        )}
      </header>

      <div className="relative pl-0 sm:pl-16">
        {/* Track + drawn line. The track is faint white/8; the green line draws
            on top tied to scrollYProgress, with a glow halo so it reads on camera. */}
        <div className="hidden sm:block absolute left-[20px] top-2 bottom-2 w-px bg-white/8" />
        <motion.div
          className="hidden sm:block absolute left-[20px] top-2 w-px bg-integrity origin-top shadow-[0_0_14px_rgba(0,255,136,0.6)]"
          style={{ height: lineHeight }}
        />

        <div className="space-y-6 sm:space-y-8">
          {STAGES.map((stage) => (
            <StageCard
              key={stage.id}
              stage={stage}
              isBroadcast={isBroadcast}
              onDeepDive={setOpenStage}
            />
          ))}
        </div>
      </div>

      <CodeSnippetOverlay
        snippet={activeSnippet}
        stepTitle={openStage?.title}
        onClose={() => setOpenStage(null)}
      />
    </section>
  );
}
