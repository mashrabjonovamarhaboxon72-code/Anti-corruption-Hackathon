"use client";
import { useRef, useState } from "react";
import { motion, useScroll, useTransform } from "framer-motion";

/*
  WorkflowSection narrates the citizen-side journey through Integrity Shield
  in seven steps. Two readers in mind simultaneously:

    Citizens — short, plain-language one-sentence copy. No jargon.
    Judges   — hover the (i) icon to surface a "Technical Insight" tooltip
               that names the concrete primitive (HMAC-SHA256, BIP39, etc).

  As each step scrolls into the viewport:
    - The card border animates from white/10 to #00ff88 (Integrity Green).
    - The "Technical Insight" badge slides up + fades in.
    - A vertical SVG line on the left fills downward, tracking
      scrollYProgress over the section. The fill stays in lockstep with the
      reader's position so the line literally "draws" as they scroll.
*/

interface Step {
  number: string;
  title: string;
  citizen: string;
  technical: string;
  badge: string;
}

const STEPS: Step[] = [
  {
    number: "01",
    title: "Anonymous Sign-Up",
    citizen:
      "Register with your national ID. The system gives you back a private identifier — your real ID is never stored.",
    technical:
      "PT = HMAC-SHA256(key=PT_SALT, message=normalize(national_id)). The raw national_id never touches the database; the 64-char pseudonymous token is the only identity the server keeps. Three independent secrets (PT_SALT, RECOVERY_SALT, PROTECTION_ORDER_SIGNING_KEY) enforce key separation at startup — compromise of one does not collapse the others.",
    badge: "Powered by HMAC-SHA256",
  },
  {
    number: "02",
    title: "Save Your Recovery Phrase",
    citizen:
      "You'll see 24 words once. Write them down — it's the only way back into your account if you lose your session.",
    technical:
      "BIP39 24-word mnemonic = 256 bits of entropy with an 8-bit SHA-256 checksum. Stored as HMAC-SHA256(RECOVERY_SALT, normalize(mnemonic)) in User.recovery_hash. Plaintext appears exactly once in the /auth/register response and is never logged. Recovery via /auth/recover requires both the national_id (factor 1) and the mnemonic (factor 2); failure responses are byte-identical for unknown-id and wrong-mnemonic, with constant-ish timing via a dummy-hash comparison when the user is missing.",
    badge: "BIP39 Enabled",
  },
  {
    number: "03",
    title: "Upload Evidence Safely",
    citizen:
      "Drop in a photo. We remove location and any hidden camera info before saving — your image becomes pixels and nothing else.",
    technical:
      "Pillow Image.new + paste reconstructs the image from raw pixels. EXIF, GPS, XMP, IPTC, and ICC ancillary chunks live outside the pixel grid and cannot follow into the new Image object. SHA-256 of the cleansed bytes is computed in memory before the file is written (no TOCTOU race) and persisted as Evidence.integrity_hash. ReportPriorityService re-hashes on every priority decision; a tampered file loses its +0.10 trust contribution and any media-broadcast eligibility it had.",
    badge: "Hash-Anchored Sanitization",
  },
  {
    number: "04",
    title: "Submit a Report",
    citizen:
      "Describe what happened. The system checks if anyone else has reported the same case so duplicates don't waste auditor time.",
    technical:
      "sentence-transformers/all-mpnet-base-v2 vectorizes the text into a 768-dim embedding; cosine similarity against every existing report is computed in-process. Above the configured threshold (default 0.88), the new report is marked Potential Duplicate and no points are awarded. Trust score is computed from a 4-signal composite: 0.50×(RI/1000) + 0.30×(1−similarity) + 0.10×evidence_verified + 0.10×has_target_department.",
    badge: "ML Duplicate Detection",
  },
  {
    number: "05",
    title: "Independent Auditor Review",
    citizen:
      "An auditor from outside the department reviews your report. The system blocks anyone with a conflict of interest before they can even see it.",
    technical:
      "COI engine evaluates auditor.department_id against report.target_department_id and runs case-insensitive substring matching of auditor.named_relatives against report.text. Block decisions write a COI_BLOCK row to the append-only audit_ledger before the assignment is rejected. Auditor profiles are looked up from a JSON-backed mock of the National HR registry (production swaps to a real API call, same interface).",
    badge: "COI-Screened Assignment",
  },
  {
    number: "06",
    title: "Earn Reputation-Weighted Points",
    citizen:
      "Verified reports earn you points. Trustworthy reporters get more per report than first-timers; bad reports cost you reputation.",
    technical:
      "Points = tier_base × (RI/500), clamped 0×–2× (T1=100, T2=250, T3=500, T4=1000 base). RI is recomputed by a 30-second asyncio loop reading auditor verdicts: Verified +50 (capped at 1000), Malicious −150 (floored at 0). Every award appends a POINTS_AWARDED row to the immutable audit_ledger; ORM before_update and before_delete listeners raise on any attempt to mutate the ledger.",
    badge: "RI-Weighted Scoring",
  },
  {
    number: "07",
    title: "Redeem Rewards Privately",
    citizen:
      "Spend points on real benefits. After you use a voucher, the link between you and that voucher is permanently destroyed.",
    technical:
      "self_destruct_transaction nulls Voucher.redeemer_pt and stamps self_destructed_at the moment status flips to Used. The voucher row survives for cohort-level fraud detection (audit_ledger keeps only an 8-char PT prefix — 32 bits, far too few for re-identification across the user base). Even an operator with full DB read access cannot answer 'which citizen redeemed voucher X' after the destruct fires, because the link no longer exists.",
    badge: "Self-Destructing Audit Logs",
  },
];

function InfoIcon() {
  return (
    <svg
      viewBox="0 0 16 16"
      width="14"
      height="14"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden
    >
      <circle cx="8" cy="8" r="6.5" />
      <path d="M8 7.5v3.5M8 5.2v.6" strokeLinecap="round" />
    </svg>
  );
}

function TechnicalTooltip({ children, label }: { children: React.ReactNode; label: string }) {
  // Hover OR keyboard-focus reveals — accessible without mouse.
  // The tooltip is a sibling of the trigger so it can size itself based on
  // its own content rather than the trigger's box.
  const [open, setOpen] = useState(false);
  return (
    <span className="relative inline-flex items-center">
      <button
        type="button"
        aria-label={`Technical detail: ${label}`}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        className="ml-2 inline-flex items-center justify-center w-5 h-5 rounded-full text-white/40 hover:text-integrity hover:bg-integrity/10 focus:outline-none focus:text-integrity focus:bg-integrity/10 transition-colors"
      >
        <InfoIcon />
      </button>
      {open && (
        <motion.span
          role="tooltip"
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.15 }}
          className="absolute left-1/2 top-full z-30 mt-2 -translate-x-1/2 w-[min(36rem,90vw)] rounded-lg border border-integrity/30 bg-ink-900/98 backdrop-blur-md shadow-glass p-4 text-[12px] leading-relaxed text-white/85 font-mono"
        >
          <div className="text-[10px] uppercase tracking-[0.18em] text-integrity mb-2">
            Technical Insight
          </div>
          {children}
        </motion.span>
      )}
    </span>
  );
}

function StepCard({ step, index }: { step: Step; index: number }) {
  return (
    <motion.div
      // viewport.amount=0.4 → fires when 40% of the card is in view; flips
      // back when it leaves so re-scrolling works for repeated demos.
      initial="hidden"
      whileInView="visible"
      viewport={{ once: false, amount: 0.4, margin: "-10% 0px -10% 0px" }}
      variants={{
        hidden: {
          borderColor: "rgba(255,255,255,0.08)",
          backgroundColor: "rgba(255,255,255,0.02)",
          y: 12,
          opacity: 0.45,
        },
        visible: {
          borderColor: "#00ff88",
          backgroundColor: "rgba(0,255,136,0.04)",
          y: 0,
          opacity: 1,
          transition: { duration: 0.55, ease: [0.16, 1, 0.3, 1] },
        },
      }}
      className="relative rounded-2xl border p-6 sm:p-7"
    >
      {/* The numbered chip sits on the left, overlapping the connecting line so
          it visually punches through the rail. */}
      <motion.div
        variants={{
          hidden: {
            backgroundColor: "rgba(255,255,255,0.04)",
            color: "rgba(255,255,255,0.50)",
            borderColor: "rgba(255,255,255,0.10)",
          },
          visible: {
            backgroundColor: "rgba(0,255,136,0.15)",
            color: "#00ff88",
            borderColor: "#00ff88",
            transition: { duration: 0.4 },
          },
        }}
        className="absolute -left-[44px] top-7 hidden sm:flex w-9 h-9 rounded-full border items-center justify-center font-mono text-xs font-semibold"
      >
        {step.number}
      </motion.div>

      <div className="flex items-baseline gap-3 flex-wrap">
        <span className="sm:hidden font-mono text-xs text-integrity">
          {step.number}
        </span>
        <h3 className="text-lg sm:text-xl font-medium tracking-tight text-white">
          {step.title}
        </h3>
        <TechnicalTooltip label={step.title}>{step.technical}</TechnicalTooltip>
      </div>

      <p className="mt-3 text-sm sm:text-[15px] leading-relaxed text-white/75 text-pretty">
        {step.citizen}
      </p>

      {/* Badge slides up + fades in only after the card is in view. */}
      <motion.div
        variants={{
          hidden: { opacity: 0, y: 8 },
          visible: {
            opacity: 1,
            y: 0,
            transition: { duration: 0.45, delay: 0.18, ease: "easeOut" },
          },
        }}
        className="mt-5 inline-flex items-center gap-1.5 rounded-full border border-integrity/40 bg-integrity/10 px-3 py-1 text-[10px] font-mono uppercase tracking-[0.15em] text-integrity"
      >
        <span
          aria-hidden
          className="inline-block w-1.5 h-1.5 rounded-full bg-integrity animate-pulse"
        />
        {step.badge}
      </motion.div>
    </motion.div>
  );
}

export function WorkflowSection() {
  const containerRef = useRef<HTMLDivElement>(null);

  // Map scroll progress to line height. The offset values mean: progress=0
  // when the section's top hits 85% down the viewport, progress=1 when the
  // section's bottom hits 15% from the top. So the line draws while the
  // reader's eyes are actually traversing the steps, not before/after.
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start 0.85", "end 0.15"],
  });
  const lineHeight = useTransform(scrollYProgress, [0, 1], ["0%", "100%"]);

  return (
    <section
      ref={containerRef}
      className="mt-20 sm:mt-28 mb-16 max-w-3xl mx-auto"
    >
      <header className="text-center mb-12 sm:mb-16">
        <div className="text-xs uppercase tracking-[0.4em] text-integrity">
          How Integrity Shield Works
        </div>
        <h2 className="mt-3 text-3xl sm:text-4xl font-semibold tracking-tight text-balance">
          A seven-step pipeline,
          <span className="block text-white/60 font-normal mt-1">
            built so we can&apos;t identify you even if we wanted to.
          </span>
        </h2>
        <p className="mt-4 text-sm text-white/40">
          Hover any{" "}
          <span className="inline-flex items-center justify-center align-middle w-5 h-5 rounded-full bg-white/[0.04] text-white/40">
            <InfoIcon />
          </span>{" "}
          for the technical detail behind the step.
        </p>
      </header>

      <div className="relative pl-0 sm:pl-16">
        {/* Track + drawn line. The track is a faint background rail; the
            drawn line sits on top and grows with scrollYProgress. */}
        <div className="hidden sm:block absolute left-[20px] top-2 bottom-2 w-px bg-white/8" />
        <motion.div
          className="hidden sm:block absolute left-[20px] top-2 w-px bg-integrity origin-top shadow-[0_0_12px_rgba(0,255,136,0.5)]"
          style={{ height: lineHeight }}
        />

        <div className="space-y-6 sm:space-y-8">
          {STEPS.map((step, i) => (
            <StepCard key={step.number} step={step} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
