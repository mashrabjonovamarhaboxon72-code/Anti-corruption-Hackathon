import { NextResponse } from "next/server";
import { readStore } from "@/lib/storage";

export const dynamic = "force-dynamic";

export async function GET() {
  const store = readStore();
  return NextResponse.json({
    organizations: store.organizations,
    people: store.people,
    scrapedAt: store.scrapedAt,
  });
}
