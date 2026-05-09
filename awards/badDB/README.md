# BadDB — Aurora Gracewood badge templates

Templates layer for every Aurora Gracewood badge. Issuance records (which user got which badge, when) live in the database, NOT here.

## Two-tier architecture (LOCKED 2026-05-08)

The badge system has TWO distinct tiers — they share the brand but have different design, security, and install models. **Don't conflate them.**

### Tier A — Real Award Badges (Finalists + Winners)
- **Audience**: ceremony-grade. The recognition artifact for paid award entries that reach Finalist or Winner.
- **Form factor**: ONE exclusive portrait form factor. Never appears as banner/sticker/email/etc. The form factor IS the trademark — fakes in the wrong form factor self-identify as fake.
- **Security**: HIGH. Smart `<script>` embed signed against client domain, runtime URL construction, sandboxed iframe / Shadow DOM, server-side referer + nonce validation.
- **Install**: manual ceremony. Aurora installs per-recipient, per-domain. Recipient cannot resize, cannot relocate, cannot fork.
- **Status**: NOT designed yet. Pending separate design pass after Tier B (Starter) ships.
- **Folder**: TBD (will be created when Tier A design begins).

### Tier B — Representation Badges (Starter, on-signup, member-class, applicant, etc.)
- **Audience**: brand presence, aspiration, recognition of joining/participating. NOT Finalists/Winners.
- **Form factors**: 9 — see `form-factors/` (hero, compact, inline, banner, vertical-card, square-sticker, circle-pin, mini-chip, email-strip).
- **Security**: LOWER. HMAC-signed iframe + static SVG + static PNG/APNG. Verifier URL + recipient @slug stamped in artwork. Recipient can resize/customize via snippet code.
- **Install**: self-serve. Recipient copies snippet from their dashboard.
- **Status**: form-factor scaffolding complete. First badge ("Starter: Journey Begins", category Influence) pending artwork from user.

## What's here

- **`README.md`** — this file.
- **`template.json`** — the universal Tier B badge template. Every representation badge follows this shape. Fields marked `// TBD` are filled in conversation, one badge at a time.
- **`form-factors/`** — 9 SVG placeholder templates for Tier B. Dimension stubs only; real artwork ships per badge.
- **`example.html`** — embed snippet sandbox. Open in a browser to preview form factors and snippet patterns.

## Conventions (locked)

- **K.I.S.S.**: every Tier B badge ships in every Tier B form factor uniformly. We prune later if needed.
- **Year is always recorded** on every issuance (database row), regardless of badge type. Display logic for the year is a separate concern.
- **No design content yet**: form-factor SVGs are blank dimension placeholders. Real artwork ships when we design each badge, one at a time.
- **No security details locked yet**: HMAC signatures, verifier URLs, anti-counterfeit watermarks all live as `TBD` in `template.json`. Discussed one at a time.
- **Tier A and Tier B are independent**: they don't share form factors, don't share template structure, don't share install pipeline. Tier A is a future, separate design pass.

## Build progression (locked 2026-05-08)

1. User customizes the **Starter (Tier B)** artwork — concept, palette, mark, typography.
2. Together we shape that artwork to fit all 9 Tier B form factors.
3. Wire backend auto-grant on signup + render in profile's Badges section.
4. Later, separate pass — design the **Real Award (Tier A)** form factor + smart-embed install pipeline.

## Source-of-truth pointer

Anything ambiguous → `D:\Great_Creations\Aurora-Gracewood\awards\CLAUDE.md`. The "Trail of changes" at the bottom is the event log; the "TWO-TIER BADGE ARCHITECTURE" section captures this lock.
