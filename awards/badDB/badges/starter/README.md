# Starter: Journey Begins

The first badge a recipient receives. Granted automatically on signup. Tier B (Representation Badges).

## Identity

| Field | Value |
|---|---|
| Slug | `starter` |
| Display name | Starter: Journey Begins |
| Category | Influence |
| Tier | B (Representation) |
| Design year | 2026 |
| Auto-grant trigger | email signup |
| Revocable | no — granted by existence |

## Folder layout (K.I.S.S. — one asset, layout-as-data)

```
awards/badDB/badges/starter/
├── README.md       ← this file
├── template.json   ← Starter-specific badge identity (extends ../../template.json master)
├── layouts.json    ← per-form-factor placement of the mark; the data the render function consumes
└── starter_template.html  ← live preview sandbox (uses ONE mark + inline SVG wrappers per form factor)
```

**No per-form-factor SVG files exist.** SVG is vector — there's no need to ship 9 nearly-identical files. Production rendering generates each form factor on-demand from the same single mark + the layout data:

```
ONE source asset:  ../../assets/mark.svg
+ layout data:     layouts.json (per form factor: viewBox dimensions + mark placement)
+ render function: composes the SVG at request time per form factor
= rendered output: SVG (per form factor, per request)
```

## What's intentionally NOT in the visual artwork (per locked design rules 2026-05-08)

- No URLs or slug text in the rendered visual (those live in the click target)
- No verifier URL stamped in artwork (lives in click target)
- No recipient @slug in artwork

## Production serving

The render function reads `layouts.json` + the mark file + the requested form factor → emits the SVG. An endpoint serves it with HMAC + Referer validation. Endpoint design discussion is in conversation / `awards/CLAUDE.md`. Likely shape:

```
GET /awards/badge/starter/{recipient-id}/{form-factor}.{ext}
  → validate recipient_id has Starter badge issued + not revoked
  → validate HMAC + Referer per Tier B security model
  → call render_badge('starter', form_factor, recipient_data) → SVG string
  → return with cache headers + content-type
```

For PNG variant: convert SVG → PNG on-demand (cairosvg / rsvg-convert) and cache.

## Next design pass

In order: split-year `[20 [mark] 26]` typography placement (added to `layouts.json`), badge name "STARTER" placement, tagline "Journey Begins" placement, tints/gradients/treatments, palette finalization. All edits go in `layouts.json` — no SVG files are touched.
