import * as cheerio from "cheerio";
import type { Organization, Person } from "./matcher";

const BASE = process.env.OPENINFO_BASE_URL || "https://openinfo.uz";
const LIST_PATH = process.env.OPENINFO_LIST_PATH || "/ru?tab=stock&page=1&type=stocks";
const UA = process.env.SCRAPE_USER_AGENT || "Mozilla/5.0 (compatible; ConflictDetectorBot/0.1)";
const DELAY = Number(process.env.SCRAPE_DELAY_MS || 800);
const MAX_PAGES = Number(process.env.SCRAPE_MAX_PAGES || 5);

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function fetchHtml(url: string): Promise<string> {
  const res = await fetch(url, {
    headers: { "User-Agent": UA, Accept: "text/html,application/xhtml+xml" },
  });
  if (!res.ok) throw new Error(`GET ${url} -> ${res.status}`);
  return res.text();
}

// openinfo.uz uses dynamic content for some sections. The selectors below are
// best-effort against the public Russian-language pages and may need
// adjustment when the site layout changes — see scripts/scrape.ts for the
// quick smoke-test that prints what was found.
function extractCompanyLinks($: cheerio.CheerioAPI): { name: string; href: string }[] {
  const seen = new Set<string>();
  const out: { name: string; href: string }[] = [];
  $('a[href*="/issuer/"], a[href*="/emitent/"], a[href*="/company/"]').each((_, el) => {
    const href = ($(el).attr("href") || "").trim();
    const name = $(el).text().trim();
    if (!href || !name) return;
    const full = href.startsWith("http") ? href : new URL(href, BASE).toString();
    if (seen.has(full)) return;
    seen.add(full);
    out.push({ name, href: full });
  });
  return out;
}

function extractPeopleFromCompany($: cheerio.CheerioAPI): { fullName: string; role: string }[] {
  // Look for sections labelled with management / supervisory board headings,
  // then collect the rows beneath them.
  const labels = [
    "руководство",
    "наблюдательный совет",
    "правление",
    "менеджмент",
    "rahbariyat",
    "kuzatuv",
    "boshqaruv",
  ];

  const people: { fullName: string; role: string }[] = [];
  $("h1, h2, h3, h4, .section-title, .block-title").each((_, el) => {
    const heading = $(el).text().toLowerCase().trim();
    if (!labels.some((l) => heading.includes(l))) return;
    const block = $(el).nextUntil("h1, h2, h3, h4, .section-title, .block-title");
    block.find("tr, li, .person, .row").each((_, row) => {
      const cells = $(row).find("td, .cell, .value, span").map((_, c) => $(c).text().trim()).get().filter(Boolean);
      if (cells.length === 0) return;
      // Heuristic: a name has 2-4 words, all letters, possibly with apostrophes.
      const nameCandidate = cells.find((t) => /^[A-Za-zА-Яа-яЁё'`’\- ]{6,80}$/.test(t) && t.split(" ").length >= 2);
      if (!nameCandidate) return;
      const role = cells.find((t) => t !== nameCandidate && t.length < 120) || "";
      people.push({ fullName: nameCandidate, role });
    });
  });
  return people;
}

export async function scrapeCompanyList(): Promise<{ name: string; href: string }[]> {
  const all: { name: string; href: string }[] = [];
  for (let page = 1; page <= MAX_PAGES; page++) {
    const url = page === 1
      ? `${BASE}${LIST_PATH}`
      : `${BASE}${LIST_PATH.replace(/page=\d+/, `page=${page}`)}`;
    const html = await fetchHtml(url);
    const $ = cheerio.load(html);
    const links = extractCompanyLinks($);
    if (links.length === 0) break;
    all.push(...links);
    await sleep(DELAY);
  }
  // De-duplicate by URL.
  const seen = new Set<string>();
  return all.filter((l) => (seen.has(l.href) ? false : (seen.add(l.href), true)));
}

export async function scrapeCompanyPage(url: string): Promise<{
  name: string;
  people: { fullName: string; role: string }[];
}> {
  const html = await fetchHtml(url);
  const $ = cheerio.load(html);
  const name = $("h1").first().text().trim() || $("title").text().trim();
  const people = extractPeopleFromCompany($);
  return { name, people };
}

export async function scrapeAll(opts: { limit?: number } = {}): Promise<{
  organizations: Organization[];
  people: Person[];
}> {
  const list = await scrapeCompanyList();
  const limit = opts.limit ?? list.length;
  const organizations: Organization[] = [];
  const people: Person[] = [];

  for (let i = 0; i < Math.min(limit, list.length); i++) {
    const link = list[i];
    try {
      const { name, people: members } = await scrapeCompanyPage(link.href);
      const orgId = `org_${i + 1}`;
      organizations.push({ id: orgId, name: name || link.name, url: link.href });
      members.forEach((m, j) => {
        people.push({
          id: `${orgId}_p${j + 1}`,
          fullName: m.fullName,
          role: m.role,
          organizationId: orgId,
        });
      });
      await sleep(DELAY);
    } catch (e) {
      console.error(`scrape failed for ${link.href}:`, (e as Error).message);
    }
  }

  return { organizations, people };
}
