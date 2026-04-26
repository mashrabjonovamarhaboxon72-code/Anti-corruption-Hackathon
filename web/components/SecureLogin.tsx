"use client";
import { FormEvent, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useAuth } from "@/contexts/AuthContext";
import { ApiError } from "@/lib/api";

interface Props {
  onSuccess?: () => void;
}

const REQUIRED_WORDS = 24;

export function SecureLogin({ onSuccess }: Props) {
  const { recover, hasCachedIdentity, pt } = useAuth();

  const [nationalId, setNationalId] = useState("");
  const [mnemonic, setMnemonic] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wordCount = useMemo(
    () => mnemonic.trim().split(/\s+/).filter(Boolean).length,
    [mnemonic],
  );
  const wordsValid = wordCount === REQUIRED_WORDS;
  const idValid = nationalId.trim().length > 0;
  const canSubmit = wordsValid && idValid && !submitting;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      await recover(nationalId.trim(), mnemonic);
      // Clear sensitive form state immediately on success.
      setMnemonic("");
      setNationalId("");
      onSuccess?.();
    } catch (err) {
      // Backend returns identical bodies for "no such id" vs "wrong mnemonic"
      // by design. Mirror that here — don't render a more specific message.
      let msg = "Recovery failed. Check your national ID and 24-word phrase.";
      if (err instanceof ApiError) {
        if (err.status === 429) {
          const detail =
            typeof err.body === "object" && err.body && "detail" in err.body
              ? String((err.body as { detail: unknown }).detail)
              : "Too many attempts. Try again shortly.";
          msg = detail;
        } else if (err.status >= 500) {
          msg = "Server error. Try again in a moment.";
        }
      } else if (err instanceof TypeError) {
        msg = "Couldn't reach the server. Is the backend running?";
      }
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <motion.form
      onSubmit={onSubmit}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      autoComplete="off"
      className="w-full max-w-md mx-auto"
    >
      <div>
        <div className="text-xs uppercase tracking-[0.18em] text-white/50">
          Secure Recovery · Sign In
        </div>
        <p className="mt-2 text-sm text-white/70 text-pretty">
          Enter your national ID and the 24-word recovery phrase you saved at
          registration. Your phrase never leaves this tab; the server stores
          only its salted hash.
        </p>
      </div>

      {hasCachedIdentity && pt && (
        <div className="mt-4 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-[11px] font-mono text-white/60">
          You were last signed in as
          <span className="ml-1.5 px-1.5 py-0.5 rounded bg-accent-500/15 text-accent-400">
            ◆ {pt.slice(0, 8)}…{pt.slice(-4)}
          </span>
          <span className="block mt-1 text-white/40 normal-case">
            Re-enter your phrase to mint a new session.
          </span>
        </div>
      )}

      <label className="block mt-5">
        <span className="text-xs uppercase tracking-wider text-white/50">
          National ID
        </span>
        <input
          type="text"
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="off"
          spellCheck={false}
          value={nationalId}
          onChange={(e) => setNationalId(e.target.value)}
          disabled={submitting}
          placeholder="AA1234567"
          className="mt-1.5 w-full rounded-lg bg-white/[0.04] border border-white/10 focus:border-accent-400/60 focus:bg-white/[0.06] outline-none px-3 py-2.5 text-sm font-mono text-white placeholder:text-white/25 transition-colors"
        />
      </label>

      <label className="block mt-4">
        <div className="flex items-baseline justify-between">
          <span className="text-xs uppercase tracking-wider text-white/50">
            24-Word Recovery Phrase
          </span>
          <span
            className={`text-[10px] font-mono tabular-nums ${
              wordsValid
                ? "text-accent-400"
                : wordCount > REQUIRED_WORDS
                  ? "text-rose-300"
                  : "text-white/40"
            }`}
          >
            {wordCount} / {REQUIRED_WORDS}
          </span>
        </div>
        <textarea
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="off"
          spellCheck={false}
          value={mnemonic}
          onChange={(e) => setMnemonic(e.target.value)}
          disabled={submitting}
          rows={4}
          placeholder="word1 word2 word3 word4 word5 word6 …"
          className="mt-1.5 w-full rounded-lg bg-white/[0.04] border border-white/10 focus:border-accent-400/60 focus:bg-white/[0.06] outline-none px-3 py-2.5 text-sm font-mono text-white placeholder:text-white/25 transition-colors resize-none break-words"
        />
        <p className="mt-1.5 text-[10px] text-white/40">
          Words are normalized (whitespace, case) before hashing — paste from any
          source.
        </p>
      </label>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 rounded-lg border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200"
        >
          {error}
        </motion.div>
      )}

      <button
        type="submit"
        disabled={!canSubmit}
        className={[
          "mt-5 w-full rounded-lg px-4 py-2.5 text-sm font-medium transition-colors",
          canSubmit
            ? "bg-accent-500 hover:bg-accent-400 text-ink-950"
            : "bg-white/[0.04] text-white/30 cursor-not-allowed",
        ].join(" ")}
      >
        {submitting ? "Verifying…" : "Recover session"}
      </button>

      <p className="mt-3 text-[10px] text-white/30 text-center">
        Mnemonic & national ID are POST&apos;d to /auth/recover · session token
        kept in memory only.
      </p>
    </motion.form>
  );
}
