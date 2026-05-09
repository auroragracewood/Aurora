# Aurora Gracewood — Backend

FastAPI service backing the Aurora Gracewood account, profile, awards
submission, and Community Choice systems.

## Status

**Phase C scaffolding** (2026-05-06). Routes are registered with correct
request/response schemas, but most handlers return `501 Not Implemented`
or stub data. The frontend remains on its localStorage stub for now.

The next sub-phases of Phase C will, one at a time:

1. Add SQLAlchemy + SQLite database with User / Submission / CommunityChoicePoint tables.
2. Real password hashing (passlib bcrypt) + JWT issuance (python-jose).
3. Wire `/api/auth/signup` to actually persist + issue tokens.
4. Wire `/api/profile` GET/PATCH to read/write the DB.
5. Migrate `account/auth.js` from localStorage to fetch() against this API.
6. Wire `/api/submissions` POST to persist submissions + enqueue review.
7. Add admin endpoints for Regular Admin / Superuser tiers.
8. Add Community Choice voting endpoints (read-only OAuth integrations come in Phase 5).

## Run locally

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# OR
source .venv/bin/activate       # macOS/Linux

pip install -r requirements.txt
cp .env.example .env             # then fill SESSION_SECRET, JWT_SECRET, etc.

uvicorn app.main:app --reload --port 8000
```

Then visit `http://127.0.0.1:8000/docs` for the auto-generated OpenAPI UI.

## Frontend integration target

Frontends call this API at `API_BASE_URL` (default `http://127.0.0.1:8000`).
CORS is open to the dev frontend (`http://127.0.0.1:9333`) and the production
domain (`https://auroragracewood.com`).

When `auth.js` is migrated, its public surface (`AGAuth.isLoggedIn()`,
`AGAuth.getUser()`, `AGAuth.updateProfile(patch)`, etc.) stays the same —
only the internal storage layer swaps from localStorage to API calls.

## Folder structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app + route definitions
│   ├── models.py          # Pydantic request/response models
│   ├── routes/            # (future) route modules split out by domain
│   ├── security/          # (future) auth, password hashing, JWT
│   └── services/          # (future) email, badge signing, payment
├── tests/                 # pytest tests
├── data/                  # SQLite + uploads (gitignored)
├── requirements.txt
├── .env.example           # template — copy to .env and fill
└── README.md              # this file
```

## Pydantic schemas mirror the frontend

The frontend stores a profile object in localStorage with these keys:

```
name, email, public_slug, public_bio, avatar_url, role,
marketing_share, created_at, updated_at
```

`app/models.py` defines `ProfileBase`, `ProfileCreate`, `ProfileUpdate`,
and `ProfileOut` matching exactly. When the frontend swaps localStorage
for `fetch('/api/profile')`, the JSON shape stays identical.

## Authentication strategy

- **Day-1 stub**: localStorage-only, no real auth (current state).
- **Phase C+ target**: bearer JWT issued by `/api/auth/signup` and `/api/auth/signin`.
  Frontend stores the JWT in localStorage and includes it in `Authorization:
  Bearer <token>` headers on every request.
- **Phase C++ target**: magic-link email auth replaces password forms entirely
  (per Phase 2 plan in awards/CLAUDE.md). Email provider TBD (Resend/Postmark/Mailgun).

## Why this skeleton ships before the implementations

By laying down the route shapes + schemas first, every Phase C+ implementation
slots into a defined contract. The frontend can be migrated endpoint-by-endpoint
without re-architecting. Backend work proceeds in parallel with frontend
polish without either side blocking the other.
