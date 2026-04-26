import { NextResponse } from "next/server";
import { scrapeAll } from "@/lib/scraper";
import { readStore, writeStore } from "@/lib/storage";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

export async function POST() {
  try {
    const limit = Number(process.env.SCRAPE_LIMIT || 25);
    const { organizations, people } = await scrapeAll({ limit });
    if (organizations.length === 0) {
      // Don't wipe an existing seed if the scrape returns nothing —
      // openinfo.uz selectors may need adjusting.
      const existing = readStore();
      return NextResponse.json(
        {
          error:
            "Scrape returned 0 companies. The openinfo.uz layout may have changed and the selectors in lib/scraper.ts need updating. Existing data preserved.",
          organizations: existing.organizations.length,
          people: existing.people.length,
        },
        { status: 502 },
      );
    }
    writeStore({ organizations, people, scrapedAt: new Date().toISOString() });
    return NextResponse.json({
      organizations: organizations.length,
      people: people.length,
    });
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 500 });
  }
}
