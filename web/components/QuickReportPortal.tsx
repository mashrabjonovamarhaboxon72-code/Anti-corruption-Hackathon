"use client";
import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
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

interface UploadState {
  status: "idle" | "uploading" | "done" | "error";
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

export function QuickReportPortal() {
  const [state, setState] = useState<UploadState>({ status: "idle" });

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
      setState({
        status: "done",
        result,
        fileName: file.name,
        originalSize: file.size,
      });
    } catch (e) {
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
  }, []);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: ACCEPT,
    multiple: false,
    maxSize: 10 * 1024 * 1024,
  });

  const reset = () => setState({ status: "idle" });

  return (
    <GlassCard className="p-6 lg:p-7 h-full flex flex-col">
      <div>
        <div className="text-xs uppercase tracking-[0.18em] text-white/50">
          Quick Report · Evidence Sanitizer
        </div>
        <div className="mt-1 text-sm text-white/60">
          Drop an image. EXIF, GPS, and embedded metadata are stripped before storage,
          then a SHA-256 integrity anchor is recorded.
        </div>
      </div>

      <div
        {...getRootProps()}
        className={[
          "mt-5 flex-1 min-h-[180px] rounded-xl border-2 border-dashed",
          "flex flex-col items-center justify-center text-center px-6 py-8",
          "transition-colors cursor-pointer select-none",
          isDragReject
            ? "border-rose-400/60 bg-rose-500/5"
            : isDragActive
              ? "border-accent-400/70 bg-accent-500/5"
              : "border-white/15 bg-white/[0.02] hover:border-white/30 hover:bg-white/[0.04]",
        ].join(" ")}
      >
        <input {...getInputProps()} />

        {state.status === "idle" && (
          <>
            <div className="text-3xl mb-3 opacity-70">⇧</div>
            <div className="text-sm text-white/80">
              {isDragActive ? "Release to sanitize" : "Drop a JPEG / PNG / WebP here"}
            </div>
            <div className="mt-1 text-xs text-white/40">
              or click to choose · max 10 MB
            </div>
          </>
        )}

        {state.status === "uploading" && (
          <>
            <div className="text-sm text-white/80">Sanitizing {state.fileName}…</div>
            <div className="mt-2 text-xs text-white/40">
              Stripping metadata · hashing payload · persisting Evidence row
            </div>
          </>
        )}

        {state.status === "done" && state.result && (
          <div className="w-full text-left">
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

            <div className="mt-4 rounded-md border border-white/5 bg-black/20 p-3 text-[11px] text-white/50">
              Next: submit a report referencing
              <code className="mx-1 text-white/70">evidence_path</code>
              and the priority engine will re-verify this hash before granting
              the +0.10 trust component.
            </div>
          </div>
        )}

        {state.status === "error" && (
          <div className="text-center">
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
          </div>
        )}
      </div>

      <div className="mt-3 text-[10px] font-mono text-white/30 text-center">
        POST {API_URL}/upload/evidence
      </div>
    </GlassCard>
  );
}
