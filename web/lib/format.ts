export function formatUZS(n: number): string {
  // Group thousands with non-breaking spaces (matches Uzbek convention).
  return new Intl.NumberFormat("en-US").format(n).replace(/,/g, " ");
}

export function formatCount(n: number): string {
  return new Intl.NumberFormat("en-US").format(n);
}

// Broadcast-friendly human labels for corruption tiers. The numeric tier
// is an internal taxonomy; on camera we show the case severity in plain
// language so a viewer doesn't have to know what "T3" means.
export const TIER_HUMAN_LABEL: Record<number, string> = {
  1: "Minor Misconduct",
  2: "Significant Violation",
  3: "Major Corruption Case",
  4: "Critical Corruption Case",
};

export function tierLabel(tier: number): string {
  return TIER_HUMAN_LABEL[tier] ?? `Tier ${tier}`;
}

export function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  const seconds = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}
