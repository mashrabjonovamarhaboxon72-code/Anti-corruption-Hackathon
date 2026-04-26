# Conflict-of-Interest Detector — openinfo.uz

A Next.js full-stack app that detects potential conflicts of interest between Uzbek
joint-stock companies by comparing the management and supervisory-board members
listed on [openinfo.uz](https://openinfo.uz/ru?tab=stock&page=1&type=stocks).

## What it flags

For every pair of people sitting on different organizations' boards:

- **HIGH — same person on both boards** — exact full-name match.
- **HIGH — parent/child** — one person's first name is another's patronymic root,
  with a matching surname (e.g. `Karimov Akmal` ↔ `Karimova Madina Akmalovna`).
- **MEDIUM — likely siblings** — same surname *and* same patronymic root.
- **LOW — shared surname only**.

Uzbek/Slavic patronymic suffixes recognised: `-ovich`, `-evich`, `-ovna`, `-evna`,
`-o'g'li` / `-ogli`, `-ugli`, `-qizi` / `-kizi`.

## Stack

- Next.js 15 (App Router) — frontend + API routes (backend in the same project)
- Cheerio for HTML scraping of openinfo.uz
- TailwindCSS for styling
- Plain JSON file (`data/store.json`) for storage — no DB server needed

## Run it

```bash
npm install
npm run seed     # populate with realistic sample data
npm run dev      # http://localhost:3000
```

Then optionally `npm run scrape` to pull real data from openinfo.uz.

## Files

- `lib/name-parser.ts` — Uzbek/Slavic name parsing.
- `lib/matcher.ts` — pair-wise classification and severity ranking.
- `lib/scraper.ts` — Cheerio-based scraper. **Selectors in `extractCompanyLinks`
  and `extractPeopleFromCompany` are best-effort and may need tweaking for the
  current openinfo.uz layout.**
- `app/page.tsx` — bulk dashboard.
- `app/api/scrape/route.ts` — POST endpoint that triggers a scrape.
- `scripts/seed.ts` — populates `data/store.json` with sample data showing every
  conflict kind.
