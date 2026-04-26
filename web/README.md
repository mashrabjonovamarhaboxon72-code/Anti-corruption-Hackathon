# Integrity Shield · Web Dashboard

Next.js 15 + Tailwind v3 frontend for the Integrity Shield FastAPI backend.

## What it shows

A Bento-grid dashboard with three primary tiles:

- **Civic ROI Counter** (`/public/stats`) — large animated number for "Public Funds Protected" in UZS, with a four-tier breakdown beneath. Auto-refreshes every 30 s.
- **High-Impact Feed** (`/admin/media-feed`) — frosted-glass cards listing Verified Tier-3+ reports with trust score above 0.9.
- **Quick Report Portal** (`/upload/evidence`) — drag-and-drop image uploader that POSTs to the sanitizer; on success, displays the evidence_id, byte-delta from sanitization, and the SHA-256 integrity anchor.

## Setup

```bash
cd web
npm install
cp .env.example .env.local
npm run dev
```

The dashboard expects the FastAPI backend on `http://localhost:8000` (override via `NEXT_PUBLIC_API_URL`). The backend must have CORS enabled for `http://localhost:3000` (default in `app/config.py`).

## Backend prerequisites

```bash
cd ..   # back to repo root
PT_SALT=$(openssl rand -hex 32) \
PROTECTION_ORDER_SIGNING_KEY=$(openssl rand -hex 32) \
RECOVERY_SALT=$(openssl rand -hex 32) \
DEMO_MODE=1 \
.venv/bin/uvicorn app.main:app --reload
```

Then in another terminal seed the demo data:

```bash
curl -X POST http://localhost:8000/admin/demo-setup
```

Refresh the dashboard — the counter, feed, and uploader will all light up.

## Layout

```
web/
  app/
    layout.tsx               Root layout, font, dark color scheme
    page.tsx                 Dashboard page — Bento grid composition
    globals.css              Tailwind directives + dark background
  components/
    Header.tsx               Brand mark + API URL pill
    GlassCard.tsx            Frosted-glass primitive (used by every tile)
    CivicRoiCounter.tsx      Large animated number + tier breakdown
    MediaFeed.tsx            Scrollable list of high-impact report cards
    QuickReportPortal.tsx    react-dropzone target → /upload/evidence
  hooks/
    usePublicStats.ts        SWR wrapper for /public/stats
    useMediaFeed.ts          SWR wrapper for /admin/media-feed
    useAnimatedNumber.ts     rAF-based ease-out cubic interpolator
  lib/
    api.ts                   fetch wrapper, ApiError, base URL
    format.ts                UZS, count, time-ago helpers
```

## Design notes

- **Frosted glass** — `backdrop-blur-xl` over a translucent `bg-white/[0.03]` on a dark gradient body. Visible only against the dark background; if you flip to light mode, swap the white tints for black.
- **Counter animation** — pure rAF, no framer-motion dependency. Ease-out cubic over 1.8 s. Re-targets smoothly when the SWR refresh changes the value (no snap-back to zero).
- **Bento grid** — single column on mobile, 12-col grid at `lg`. ROI takes 8 cols × 2 rows, Feed takes 4 cols × 3 rows (tall sidebar), Quick Report takes 8 cols × 1 row beneath ROI.
- **No client state library** — SWR handles caching/revalidation; component state is local `useState`. If the surface grows, lift to Zustand or React Query.
