import { NextResponse } from "next/server";
import { readStore } from "@/lib/storage";
import { detectConflicts, summarize } from "@/lib/matcher";

export const dynamic = "force-dynamic";

export async function GET() {
  const store = readStore();
  const conflicts = detectConflicts(store.organizations, store.people);
  return NextResponse.json({
    counts: summarize(conflicts),
    total: conflicts.length,
    conflicts,
    scrapedAt: store.scrapedAt,
  });
}
