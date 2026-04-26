import { scrapeAll } from "../lib/scraper";
import { writeStore } from "../lib/storage";

const limit = Number(process.env.SCRAPE_LIMIT || 25);

scrapeAll({ limit })
  .then(({ organizations, people }) => {
    writeStore({ organizations, people, scrapedAt: new Date().toISOString() });
    console.log(`Scraped ${organizations.length} orgs, ${people.length} people.`);
    if (organizations.length === 0) {
      console.warn(
        "No organizations were extracted. The selectors in lib/scraper.ts may need to be adjusted to the current openinfo.uz layout.",
      );
    }
  })
  .catch((e) => {
    console.error("Scrape failed:", e);
    process.exit(1);
  });
