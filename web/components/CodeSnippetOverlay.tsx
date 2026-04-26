"use client";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { CodeSnippet } from "@/lib/codeSnippets";
import { tokenizePython, type TokenType } from "@/lib/highlightPython";

const TOKEN_CLASS: Record<TokenType, string> = {
  comment: "text-white/35 italic",
  string: "text-emerald-300/85",
  keyword: "text-fuchsia-300/95 font-medium",
  builtin: "text-sky-300/90",
  decorator: "text-amber-300/85",
  number: "text-orange-300/85",
  punct: "text-white/55",
  operator: "text-white/55",
  ident: "text-white/85",
  whitespace: "",
};

/**
 * Renders Python source with line numbers and syntax-colored tokens.
 * Whitespace tokens are emitted verbatim so indentation survives.
 */
function HighlightedCode({ source, language }: { source: string; language: string }) {
  // Tokenize first; then split rendered tokens by line so we can prepend
  // line numbers without re-tokenizing per line.
  const tokens = language === "python" ? tokenizePython(source) : null;

  if (!tokens) {
    return (
      <pre className="font-mono text-[12.5px] leading-[1.65] text-white/85 whitespace-pre">
        {source}
      </pre>
    );
  }

  const lines: { type: TokenType; value: string }[][] = [[]];
  for (const t of tokens) {
    if (t.type === "whitespace" && t.value.includes("\n")) {
      const parts = t.value.split("\n");
      // Trailing whitespace on the current line (before the first \n)
      if (parts[0]) lines[lines.length - 1].push({ type: "whitespace", value: parts[0] });
      // Each \n starts a new line; intermediate parts are leading whitespace.
      for (let p = 1; p < parts.length; p++) {
        lines.push([]);
        if (parts[p]) lines[lines.length - 1].push({ type: "whitespace", value: parts[p] });
      }
    } else {
      lines[lines.length - 1].push(t);
    }
  }

  return (
    <pre className="font-mono text-[12.5px] leading-[1.7] whitespace-pre overflow-x-auto">
      <code>
        {lines.map((line, i) => (
          <div key={i} className="flex">
            <span className="select-none text-white/20 pr-4 text-right tabular-nums w-8 shrink-0">
              {i + 1}
            </span>
            <span className="flex-1 min-w-0">
              {line.length === 0 ? (
                <span>&nbsp;</span>
              ) : (
                line.map((t, j) => (
                  <span key={j} className={TOKEN_CLASS[t.type]}>
                    {t.value}
                  </span>
                ))
              )}
            </span>
          </div>
        ))}
      </code>
    </pre>
  );
}

interface Props {
  snippet: CodeSnippet | null;
  stepTitle?: string;
  onClose: () => void;
}

export function CodeSnippetOverlay({ snippet, stepTitle, onClose }: Props) {
  const [copied, setCopied] = useState(false);

  // Esc closes; body scroll locks while open.
  useEffect(() => {
    if (!snippet) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [snippet, onClose]);

  // Reset the "Copied!" state when a different snippet is opened.
  useEffect(() => {
    setCopied(false);
  }, [snippet]);

  return (
    <AnimatePresence>
      {snippet && (
        <motion.div
          key="overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          onClick={onClose}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/75 backdrop-blur-md"
        >
          <motion.div
            key="panel"
            initial={{ opacity: 0, scale: 0.97, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: 12 }}
            transition={{ duration: 0.22, ease: "easeOut" }}
            onClick={(e) => e.stopPropagation()}
            className="relative w-full max-w-3xl max-h-[88vh] flex flex-col rounded-2xl border border-integrity/30 bg-[#0a0a0a]/95 backdrop-blur-xl shadow-[0_30px_80px_-20px_rgba(0,255,136,0.25)]"
          >
            <header className="flex items-start justify-between gap-4 px-5 sm:px-6 pt-5 pb-4 border-b border-white/8">
              <div className="min-w-0">
                <div className="text-[10px] uppercase tracking-[0.3em] text-integrity">
                  Technical Deep-Dive
                </div>
                <div className="mt-1 text-base sm:text-lg font-medium text-white truncate">
                  {stepTitle ?? "Backend logic"}
                </div>
                <div className="mt-1 text-[11px] font-mono text-white/40 truncate">
                  {snippet.source}
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className="px-2 py-0.5 rounded-md text-[10px] font-mono uppercase tracking-wider bg-white/[0.04] border border-white/10 text-white/60">
                  {snippet.language}
                </span>
                <button
                  onClick={() => {
                    navigator.clipboard?.writeText(snippet.code).then(
                      () => {
                        setCopied(true);
                        setTimeout(() => setCopied(false), 1400);
                      },
                      () => {},
                    );
                  }}
                  className="px-2.5 py-1 rounded-md text-[11px] bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 text-white/70 hover:text-white transition-colors"
                >
                  {copied ? "Copied" : "Copy"}
                </button>
                <button
                  onClick={onClose}
                  aria-label="Close"
                  className="w-7 h-7 rounded-md flex items-center justify-center text-white/40 hover:text-white hover:bg-white/5 transition-colors"
                >
                  ×
                </button>
              </div>
            </header>

            <div className="px-5 sm:px-6 py-4 text-[13px] leading-relaxed text-white/65 text-pretty border-b border-white/5">
              {snippet.caption}
            </div>

            <div className="flex-1 overflow-auto px-2 sm:px-3 py-4 bg-[#06070a]">
              <HighlightedCode source={snippet.code} language={snippet.language} />
            </div>

            <footer className="px-5 sm:px-6 py-3 text-[10px] font-mono text-white/30 border-t border-white/5 flex items-center justify-between">
              <span>Esc to close</span>
              <span className="hidden sm:inline">{snippet.code.split("\n").length} lines</span>
            </footer>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
