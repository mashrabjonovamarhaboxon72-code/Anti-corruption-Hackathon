"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

export default function ScrapeButton() {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  async function onScrape() {
    setErr(null);
    setMsg(null);
    try {
      const res = await fetch("/api/scrape", { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || `HTTP ${res.status}`);
      setMsg(`Imported ${data.organizations} orgs, ${data.people} people.`);
      startTransition(() => router.refresh());
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        onClick={onScrape}
        disabled={pending}
        className="rounded bg-[var(--accent)] text-black font-medium px-4 py-2 hover:opacity-90 disabled:opacity-50"
      >
        {pending ? "Refreshing…" : "Scrape openinfo.uz"}
      </button>
      {msg && <span className="text-xs text-emerald-400">{msg}</span>}
      {err && <span className="text-xs text-red-400 max-w-xs text-right">{err}</span>}
    </div>
  );
}
