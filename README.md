# Aurora Gracewood

Brand persona under Great Creations. Houses Aurora Awards (paid review awards
body) and future Aurora products (Showcase, Directory, Editorial).

## Repo layout

```
Aurora-Gracewood/
├── index.html              # Splash page (auroragracewood.com/)
├── splash.css
├── site/                   # AG home (/site/)
├── awards/                 # Aurora Awards (/awards/)
├── account/                # Account/auth UI (/account/)
├── backend/                # FastAPI service (Phase C+ — see backend/README.md)
├── assets/                 # Brand-level assets (logo, portrait, treeline, moon-map)
├── LAUNCH-READINESS.md     # Tracked checklist of what's needed before public launch
├── .gitignore
└── README.md               # this file
```

## Quick start (local dev)

```bash
# From the AG root, serve everything as a single domain:
cd D:\Great_Creations\Aurora-Gracewood
python -m http.server 9333 --bind 127.0.0.1

# Then visit:
#   http://127.0.0.1:9333/             (splash)
#   http://127.0.0.1:9333/site/        (AG home)
#   http://127.0.0.1:9333/awards/      (Aurora Awards)
#   http://127.0.0.1:9333/account/     (account/profile)
```

The frontend currently runs on a localStorage auth stub. Backend (`backend/`)
is in Phase C scaffolding — see `backend/README.md`.

## Architecture in one breath

- **Single-page-frontend** per product surface (Splash, Site, Awards, Account).
- **Cross-product accounts** via `AGAuth` module (`account/auth.js`), shared
  across all AG products. Same identity on /awards/ as on /site/.
- **Stub-first backend strategy**: `auth.js` uses localStorage today; Phase C+
  swaps to FastAPI calls without changing the public surface.
- **Awards system**: 9 main categories + 1 influencer category + Community
  Choice bonus track (points-based, no physical trophy). Three recognition
  tiers (Winner / Finalist / Honoree) with year-stamped badges.
- **Year handling**: `<span class="year"></span>` filled by JS at load time —
  never hardcode the year anywhere.

## Canonical specs

- **Strategic decisions, pricing, trophy plan, Community Choice mechanic, badge
  system, OAuth voting plan**: `awards/CLAUDE.md`
- **Backend integration target**: `backend/README.md`
- **Launch-readiness checklist** (gating items before public launch):
  `LAUNCH-READINESS.md`

## Brand context

Aurora Gracewood is a **peer subsidiary of Great Creations**, alongside
Great Creation Studios (GCS). GCS provides design/maintenance services to
Aurora's sites in a sister-brand arrangement.

- Auth boundary: **Aurora Gracewood-wide** (one signup spans all AG products)
- Data-share boundary: **Great Creations** (data flows to GCS + future siblings)

See `awards/CLAUDE.md` for the full corporate structure and editorial-integrity
wall between review data and marketing data.

## Status

Day-1 starter complete. Phase A (config reconciliation) + Phase B (form gating)
+ Phase C kickoff (profile editor, backend skeleton, superuser elevation) are
in. See `LAUNCH-READINESS.md` for what's left before public launch.

## License

TBD — pending decision on whether the codebase is private (closed) or open
(MIT/AGPL/etc.). Currently treat as proprietary until decided.
