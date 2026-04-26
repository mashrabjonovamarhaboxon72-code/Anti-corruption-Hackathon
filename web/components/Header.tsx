"use client";
import { useState } from "react";
import { API_URL } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { useBroadcast } from "@/contexts/BroadcastContext";
import { AuthModal } from "./AuthModal";

function PtChip({ pt }: { pt: string }) {
  return (
    <span className="font-mono text-[11px] text-white/70 px-2 py-1 rounded-md bg-white/[0.04] border border-white/10">
      ◆ {pt.slice(0, 8)}…{pt.slice(-4)}
    </span>
  );
}

function BroadcastToggle() {
  const { isBroadcast, toggle } = useBroadcast();
  return (
    <button
      onClick={toggle}
      title={isBroadcast ? "Exit Broadcast Mode (Esc)" : "Enter Broadcast Mode"}
      className={[
        "inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md transition-colors",
        isBroadcast
          ? "bg-accent-500/20 text-accent-400 ring-1 ring-accent-400/40 hover:bg-accent-500/25"
          : "bg-white/[0.04] text-white/70 hover:bg-white/[0.08] hover:text-white border border-white/10",
      ].join(" ")}
    >
      <span
        aria-hidden
        className={[
          "inline-block w-2 h-2 rounded-full",
          isBroadcast ? "bg-accent-400 animate-pulse" : "bg-white/30",
        ].join(" ")}
      />
      <span className="hidden sm:inline">
        {isBroadcast ? "Broadcasting" : "Broadcast Mode"}
      </span>
      <span className="sm:hidden">{isBroadcast ? "ON AIR" : "BCST"}</span>
    </button>
  );
}

export function Header() {
  const { isAuthenticated, hasCachedIdentity, pt, logout, expiresAt } = useAuth();
  const [open, setOpen] = useState(false);

  return (
    <>
      <header className="flex items-center justify-between mb-8 gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-md border border-accent-400/40 bg-accent-500/10 flex items-center justify-center">
            <span className="text-accent-400 text-sm font-bold">▲</span>
          </div>
          <div>
            <div className="text-sm font-semibold tracking-tight">
              Integrity Shield
            </div>
            <div className="text-[11px] font-mono text-white/40">
              transparency dashboard
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-[11px] font-mono text-white/30 hidden sm:inline">
            {API_URL}
          </span>

          <BroadcastToggle />

          {isAuthenticated && pt ? (
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-accent-400 px-2 py-1 rounded-full bg-accent-500/10 border border-accent-400/30">
                <span className="w-1.5 h-1.5 rounded-full bg-accent-400 animate-pulse" />
                live session
              </span>
              <PtChip pt={pt} />
              <button
                onClick={logout}
                className="text-[11px] text-white/60 hover:text-white px-2 py-1 rounded-md hover:bg-white/5 transition-colors"
                title={expiresAt ? `Expires ${new Date(expiresAt).toLocaleString()}` : undefined}
              >
                Sign out
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              {hasCachedIdentity && pt && (
                <span className="hidden sm:inline-flex items-center gap-1.5 text-[10px] text-white/50">
                  last seen
                  <PtChip pt={pt} />
                </span>
              )}
              <button
                onClick={() => setOpen(true)}
                className="text-xs px-3 py-1.5 rounded-md bg-accent-500 hover:bg-accent-400 text-ink-950 font-medium transition-colors"
              >
                {hasCachedIdentity ? "Resume session" : "Sign in"}
              </button>
            </div>
          )}
        </div>
      </header>

      <AuthModal open={open} onClose={() => setOpen(false)} />
    </>
  );
}
