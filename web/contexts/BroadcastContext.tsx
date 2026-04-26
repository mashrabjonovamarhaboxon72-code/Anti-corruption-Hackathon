"use client";
import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

/*
  Broadcast Mode is a presentation-only view, designed for being filmed or
  projected at events. Three behavioral changes:

    1. Civic ROI counter goes full-screen — the only headline on the page.
    2. High-Impact Feed becomes a slow vertical marquee, paced for camera
       readability. Pauses on hover for the operator to inspect.
    3. All technical metadata (tier numbers, trust scores, timestamps,
       PT prefixes, API URLs) is hidden. Only human-readable case
       narratives remain.

  State is mirrored to the URL query string (?broadcast=1) so a
  pre-configured display can deep-link straight into broadcast mode
  without operator interaction.
*/

const URL_PARAM = "broadcast";

interface BroadcastContextValue {
  isBroadcast: boolean;
  toggle: () => void;
  enable: () => void;
  disable: () => void;
}

const BroadcastContext = createContext<BroadcastContextValue | null>(null);

export function BroadcastProvider({ children }: { children: ReactNode }) {
  const [isBroadcast, setIsBroadcast] = useState(false);

  // Read initial state from the URL on first mount.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (params.get(URL_PARAM) === "1") setIsBroadcast(true);
  }, []);

  // Mirror state to the URL whenever it changes — replaceState (not push)
  // so toggling doesn't pollute the back-button stack.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    if (isBroadcast) url.searchParams.set(URL_PARAM, "1");
    else url.searchParams.delete(URL_PARAM);
    window.history.replaceState(window.history.state, "", url.toString());
  }, [isBroadcast]);

  // Esc exits broadcast — operators expect a hardware-style escape hatch.
  useEffect(() => {
    if (!isBroadcast) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsBroadcast(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [isBroadcast]);

  const toggle = useCallback(() => setIsBroadcast((v) => !v), []);
  const enable = useCallback(() => setIsBroadcast(true), []);
  const disable = useCallback(() => setIsBroadcast(false), []);

  return (
    <BroadcastContext.Provider value={{ isBroadcast, toggle, enable, disable }}>
      {children}
    </BroadcastContext.Provider>
  );
}

export function useBroadcast(): BroadcastContextValue {
  const ctx = useContext(BroadcastContext);
  if (!ctx) {
    throw new Error("useBroadcast must be used within a <BroadcastProvider>");
  }
  return ctx;
}
