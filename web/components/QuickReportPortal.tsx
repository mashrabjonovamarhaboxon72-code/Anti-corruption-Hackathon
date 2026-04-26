"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useDropzone } from "react-dropzone";
import { AnimatePresence, motion } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { api, ApiError, API_URL } from "@/lib/api";

interface UploadResult {
  message: string;
  evidence_id: number;
  stored_path: string;
  integrity_hash: string;
  size_bytes: number;
  metadata_stripped: boolean;
}

type Status = "idle" | "uploading" | "done" | "error";

interface UploadState {
  status: Status;
  result?: UploadResult;
  error?: string;
  originalSize?: number;
  fileName?: string;
}

const ACCEPT = {
  "image/jpeg": [".jpg", ".jpeg"],
  "image/png": [".png"],
  "image/webp": [".webp"],
};

/**
 * Synthetic stage timeline. The actual /upload/evidence call is one round-trip,
 * so there's no real progress signal mid-flight — we narrate what the server is
 * doing in named stages with realistic timing. If the request resolves before
 * the timeline completes, we snap to "done"; if it errors, we freeze the bar
 * at its current width and tint it red.
 */
const STAGES = [
  { key: "upload", label: "Uploading bytes", target: 32, durationMs: 380 },
  { key: "strip", label: "Stripping EXIF / GPS / XMP", target: 68, durationMs: 520 },
  { key: "hash", label: "Hashing payload (SHA-256)", target: 90, durationMs: 280 },
  { key: "persist", label: "Persisting Evidence row", target: 99, durationMs: 220 },
] as const;

function useSanitizationProgress(active: boolean) {
  const [progress, setProgress] = useState(0);
  const [stageLabel, setStageLabel] = useState<string>(STAGES[0].label);
  const completeRef = useRef<() => void>(() => {});
  const failRef = useRef<() => void>(() => {});

  useEffect(() => {
    if (!active) {
      setProgress(0);
      setStageLabel(STAGES[0].label);
      return;
    }

    let cancelled = false;
    let stageIdx = 0;
    const tick = () => {
      if (cancelled || stageIdx >= STAGES.length) return;
      const stage = STAGES[stageIdx];
      setStageLabel(stage.label);
      setProgress(stage.target);
      setTimeout(() => {
        stageIdx += 1;
        tick();
      }, stage.durationMs);
    };
    tick();

    completeRef.current = () => {
      cancelled = true;
      setProgress(100);
      setStageLabel("Cleansed");
    };
    failRef.current = () => {
      cancelled = true;
      // freeze whatever progress we had
    };

    return () => {
      cancelled = true;
    };
  }, [active]);

  return {
    progress,
    stageLabel,
    finishSuccess: () => completeRef.current(),
    finishFailure: () => failRef.current(),
  };
}

export function QuickReportPortal() {
  const [state, setState] = useState<UploadState>({ status: "idle" });
  const { progress, stageLabel, finishSuccess, finishFailure } = useSanitizationProgress(
    state.status === "uploading",
  );

  const onDrop = useCallback(async (files: File[]) => {
    const file = files[0];
    if (!file) return;
    setState({ status: "uploading", fileName: file.name, originalSize: file.size });

    const form = new FormData();
    form.append("file", file);

    try {
      const result = await api<UploadResult>("/upload/evidence", {
        method: "POST",
        body: form,
      });
      finishSuccess();
      // Tiny delay so the bar visibly hits 100% before the result panel renders
      setTimeout(() => {
        setState({
          status: "done",
          result,
          fileName: file.name,
          originalSize: file.size,
        });
      }, 250);
    } catch (e) {
      finishFailure();
      const msg =
        e instanceof ApiError
          ? typeof e.body === "object" && e.body !== null && "detail" in e.body
            ? String((e.body as { detail: unknown }).detail)
            : `HTTP ${e.status}`
          : e instanceof Error
            ? e.message
            : "Upload failed.";
      setState({ status: "error", error: msg, fileName: file.name });
    }
  }, [finishSuccess, finishFailure]);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: ACCEPT,
    multiple: false,
    maxSize: 10 * 1024 * 1024,
    disabled: state.status === "uploading",
  });

  const reset = () => setState({ status: "idle" });

  return (
    <GlassCard className="p-6 lg:p-7 h-full flex flex-col">
      <div>
        <div className="text-xs uppercase tracking-[0.18em] text-white/50">
          Evidence Dropzone · Sanitizer Pipeline
        </div>
        <div className="mt-1 text-sm text-white/60">
          Drop an image. EXIF, GPS, and embedded metadata are stripped before
          storage; a SHA-256 anchors the cleansed bytes against future tampering.
        </div>
      </div>

      <div
        {...getRootProps()}
        className={[
          "mt-5 flex-1 min-h-[180px] rounded-xl border-2 border-dashed",
          "flex flex-col items-center justify-center text-center px-6 py-8",
          "transition-colors select-none",
          state.status === "uploading"
            ? "border-accent-400/60 bg-accent-500/5 cursor-wait"
            : isDragReject
              ? "border-rose-400/60 bg-rose-500/5 cursor-not-allowed"
              : isDragActive
                ? "border-accent-400/70 bg-accent-500/5 cursor-copy"
                : "border-white/15 bg-white/[0.02] hover:border-white/30 hover:bg-white/[0.04] cursor-pointer",
        ].join(" ")}
      >
        <input {...getInputProps()} />

        <AnimatePresence mode="wait">
          {state.status === "idle" && (
            <motion.div
              key="idle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center"
            >
              <div className="text-3xl mb-3 opacity-70">⇧</div>
              <div className="text-sm text-white/80">
                {isDragActive ? "Release to sanitize" : "Drop a JPEG / PNG / WebP here"}
              </div>
              <div className="mt-1 text-xs text-white/40">
                or click to choose · max 10 MB
              </div>
            </motion.div>
          )}

          {state.status === "uploading" && (
            <motion.div
              key="uploading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="w-full max-w-md mx-auto"
            >
              <div className="text-sm text-white/85 truncate">
                Sanitizing {state.fileName}
              </div>

              <div className="mt-4 h-2 rounded-full bg-white/10 overflow-hidden">
                <motion.div
                  className="h-full rounded-full bg-gradient-to-r from-accent-500 to-accent-400"
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.45, ease: "easeOut" }}
                />
              </div>

              <div className="mt-3 flex items-center justify-between text-[11px] font-mono text-white/60">
                <span>{stageLabel}…</span>
                <span className="tabular-nums">{progress.toString().padStart(2, "0")}%</span>
              </div>

              <div className="mt-3 grid grid-cols-4 gap-1 text-[10px] uppercase tracking-wider">
                {STAGES.map((s) => (
                  <div
                    key={s.key}
                    className={[
                      "text-center px-1 py-1 rounded border",
                      progress >= s.target
                        ? "border-accent-400/40 text-accent-400/90 bg-accent-500/5"
                        : progress > 0
                          ? "border-white/10 text-white/40"
                          : "border-white/5 text-white/30",
                    ].join(" ")}
                  >
                    {s.key}
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {state.status === "done" && state.result && (
            <motion.div
              key="done"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="w-full text-left"
            >
              <div className="flex items-center justify-between">
                <div className="text-sm text-accent-400 font-medium">
                  ✓ Evidence cleansed and stored
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    reset();
                  }}
                  className="text-xs text-white/50 hover:text-white/80 underline-offset-2 hover:underline"
                >
                  Upload another
                </button>
              </div>

              <dl className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-2 text-xs font-mono">
                <div>
                  <dt className="text-white/40">file</dt>
                  <dd className="text-white/85 truncate">{state.fileName}</dd>
                </div>
                <div>
                  <dt className="text-white/40">evidence_id</dt>
                  <dd className="text-white/85">#{state.result.evidence_id}</dd>
                </div>
                <div>
                  <dt className="text-white/40">original</dt>
                  <dd className="text-white/85">
                    {state.originalSize?.toLocaleString()} B
                  </dd>
                </div>
                <div>
                  <dt className="text-white/40">cleansed</dt>
                  <dd className="text-white/85">
                    {state.result.size_bytes.toLocaleString()} B
                    {state.originalSize && state.originalSize > state.result.size_bytes && (
                      <span className="ml-1 text-accent-400/80">
                        (−{(state.originalSize - state.result.size_bytes).toLocaleString()} B stripped)
                      </span>
                    )}
                  </dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="text-white/40">integrity_hash (SHA-256)</dt>
                  <dd className="text-white/70 break-all">
                    {state.result.integrity_hash}
                  </dd>
                </div>
              </dl>
            </motion.div>
          )}

          {state.status === "error" && (
            <motion.div
              key="error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-center"
            >
              <div className="text-sm text-rose-300">Upload failed</div>
              <div className="mt-1 text-xs text-white/60 max-w-sm">{state.error}</div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  reset();
                }}
                className="mt-3 text-xs text-white/60 hover:text-white underline"
              >
                Try again
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="mt-3 text-[10px] font-mono text-white/30 text-center">
        POST {API_URL}/upload/evidence
      </div>
    </GlassCard>
  );
}
