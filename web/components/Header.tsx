import { API_URL } from "@/lib/api";

export function Header() {
  return (
    <header className="flex items-center justify-between mb-8">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-md border border-accent-400/40 bg-accent-500/10 flex items-center justify-center">
          <span className="text-accent-400 text-sm font-bold">▲</span>
        </div>
        <div>
          <div className="text-sm font-semibold tracking-tight">Integrity Shield</div>
          <div className="text-[11px] font-mono text-white/40">transparency dashboard</div>
        </div>
      </div>
      <div className="text-[11px] font-mono text-white/30 hidden sm:block">
        {API_URL}
      </div>
    </header>
  );
}
