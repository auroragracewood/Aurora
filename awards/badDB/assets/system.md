<!--
FF Meta is not on Google Fonts. It's distributed via Adobe Fonts / Monotype.
For local preview to render the actual typeface, the font must be installed
locally OR served via an Adobe Fonts kit. Without it, the samples below fall
back to the system sans-serif — the layout and weights are still accurate;
only the typeface itself appears as a fallback until FF Meta is loaded.
-->
<style>
/* If FF Meta is locally available it will be used. Otherwise the fallback
   chain below approximates the visual character (humanist, slightly wide). */
</style>

# Aurora Gracewood — Brand System

The colors and font Aurora uses across her sites. This is the input baseline for badge artwork design — when you choose hexes for the Starter (or any future badge), pull from this palette unless there's a deliberate reason to invent new ones.

> **Status**: hex values are PLACEHOLDERS pending Aurora's finalization (per `great-creations-color-system.md` memory). Source-of-truth: `D:\Great_Creations\Aurora-Gracewood\site\styles.css`. When the hexes are finalized, update there first, then re-pull here.
>
> **Font in current use across all Aurora surfaces**: FF Meta (Adobe Fonts / Monotype) with system fallbacks. No secondary or display font is declared yet — typographic hierarchy is achieved through FF Meta weight changes. Common weights: Light 300, Book 400, Medium 500, Bold 700, Black 900. (FF Meta does not natively have a 600 / Semi-Bold weight; browsers will synthesize one if requested.)

---

## Tier 1 — Aurora Primary (the lead palette)

These three are the brand's *voice* in color. Use them most.

<table style="width:100%;border-collapse:collapse">
<tr>
  <td style="background:#f4cfd9;width:120px;height:80px;border:1px solid #ddd"></td>
  <td style="padding:0 16px;font-family:'FF Meta','Meta Pro','Meta',sans-serif;font-weight:600">Aurora Light Pink<br><span style="font-family:ui-monospace,monospace;font-weight:400;color:#666">#f4cfd9</span></td>
  <td style="font-family:'FF Meta','Meta Pro','Meta',sans-serif;color:#444">Soft, romantic, warm. The brand's signature blush — used for accents, eyebrows, gentle highlights.</td>
</tr>
<tr>
  <td style="background:#4a5fc1;width:120px;height:80px;border:1px solid #ddd"></td>
  <td style="padding:0 16px;font-family:'FF Meta','Meta Pro','Meta',sans-serif;font-weight:600">Aurora Blueberry<br><span style="font-family:ui-monospace,monospace;font-weight:400;color:#666">#4a5fc1</span></td>
  <td style="font-family:'FF Meta','Meta Pro','Meta',sans-serif;color:#444">Deep berry blue. Confident and grounding — used for primary buttons, CTAs, brand mark accents.</td>
</tr>
<tr>
  <td style="background:#738c5e;width:120px;height:80px;border:1px solid #ddd"></td>
  <td style="padding:0 16px;font-family:'FF Meta','Meta Pro','Meta',sans-serif;font-weight:600">Aurora Moss<br><span style="font-family:ui-monospace,monospace;font-weight:400;color:#666">#738c5e</span></td>
  <td style="font-family:'FF Meta','Meta Pro','Meta',sans-serif;color:#444">Earthy green-grey. The grounding base — quiet, organic. Used sparingly to balance the pink and blue.</td>
</tr>
</table>

---

## Tier 2 — Great Creations Family Signal (aurora curtain colors)

These three are the *family signal* — they identify Aurora as a Great Creations property. Used in small doses (footer-link hovers, accent moments, the GC wordmark animation).

<table style="width:100%;border-collapse:collapse">
<tr>
  <td style="background:#45d9ff;width:120px;height:80px;border:1px solid #ddd"></td>
  <td style="padding:0 16px;font-family:'FF Meta','Meta Pro','Meta',sans-serif;font-weight:600">GC Cyan<br><span style="font-family:ui-monospace,monospace;font-weight:400;color:#666">#45d9ff</span></td>
  <td style="font-family:'FF Meta','Meta Pro','Meta',sans-serif;color:#444">Bright signal cyan. The "Creations" word in the GC wordmark hover.</td>
</tr>
<tr>
  <td style="background:#ff8fd8;width:120px;height:80px;border:1px solid #ddd"></td>
  <td style="padding:0 16px;font-family:'FF Meta','Meta Pro','Meta',sans-serif;font-weight:600">GC Pink<br><span style="font-family:ui-monospace,monospace;font-weight:400;color:#666">#ff8fd8</span></td>
  <td style="font-family:'FF Meta','Meta Pro','Meta',sans-serif;color:#444">Bright pop pink. The "a" and "property" words + underline in the GC footer wordmark hover.</td>
</tr>
<tr>
  <td style="background:#ffb469;width:120px;height:80px;border:1px solid #ddd"></td>
  <td style="padding:0 16px;font-family:'FF Meta','Meta Pro','Meta',sans-serif;font-weight:600">GC Orange<br><span style="font-family:ui-monospace,monospace;font-weight:400;color:#666">#ffb469</span></td>
  <td style="font-family:'FF Meta','Meta Pro','Meta',sans-serif;color:#444">Light orange. The "Great" word in the GC wordmark hover.</td>
</tr>
</table>

---

## Tier 3 — Universal (foundation, dark, neutral)

The structural colors. Backgrounds, text, borders, copper accents.

<table style="width:100%;border-collapse:collapse">
<tr>
  <td style="background:#6f4ea3;width:120px;height:80px;border:1px solid #ddd"></td>
  <td style="padding:0 16px;font-family:'FF Meta','Meta Pro','Meta',sans-serif;font-weight:600">Grape<br><span style="font-family:ui-monospace,monospace;font-weight:400;color:#666">#6f4ea3</span></td>
  <td style="font-family:'FF Meta','Meta Pro','Meta',sans-serif;color:#444">Royal purple. Used in tier-honoree gradient and decorative accents.</td>
</tr>
<tr>
  <td style="background:#2c5e3f;width:120px;height:80px;border:1px solid #ddd"></td>
  <td style="padding:0 16px;font-family:'FF Meta','Meta Pro','Meta',sans-serif;font-weight:600">Forest<br><span style="font-family:ui-monospace,monospace;font-weight:400;color:#666">#2c5e3f</span></td>
  <td style="font-family:'FF Meta','Meta Pro','Meta',sans-serif;color:#444">Deep forest green. Anchored, mature.</td>
</tr>
<tr>
  <td style="background:#050816;width:120px;height:80px;border:1px solid #ddd"></td>
  <td style="padding:0 16px;color:#fff;font-family:'FF Meta','Meta Pro','Meta',sans-serif;font-weight:600">Midnight<br><span style="font-family:ui-monospace,monospace;font-weight:400;color:#aaa">#050816</span></td>
  <td style="font-family:'FF Meta','Meta Pro','Meta',sans-serif;color:#444">Deep navy-black. Site background base.</td>
</tr>
<tr>
  <td style="background:#1c1f2a;width:120px;height:80px;border:1px solid #ddd"></td>
  <td style="padding:0 16px;color:#fff;font-family:'FF Meta','Meta Pro','Meta',sans-serif;font-weight:600">Charcoal<br><span style="font-family:ui-monospace,monospace;font-weight:400;color:#aaa">#1c1f2a</span></td>
  <td style="font-family:'FF Meta','Meta Pro','Meta',sans-serif;color:#444">Soft black. Text on light surfaces, panels on dark.</td>
</tr>
<tr>
  <td style="background:#f6f7fb;width:120px;height:80px;border:1px solid #ddd"></td>
  <td style="padding:0 16px;font-family:'FF Meta','Meta Pro','Meta',sans-serif;font-weight:600">Off-White<br><span style="font-family:ui-monospace,monospace;font-weight:400;color:#666">#f6f7fb</span></td>
  <td style="font-family:'FF Meta','Meta Pro','Meta',sans-serif;color:#444">Cool paper white. Text on dark surfaces, light-mode card backgrounds.</td>
</tr>
<tr>
  <td style="background:#c47a4a;width:120px;height:80px;border:1px solid #ddd"></td>
  <td style="padding:0 16px;font-family:'FF Meta','Meta Pro','Meta',sans-serif;font-weight:600">Copper<br><span style="font-family:ui-monospace,monospace;font-weight:400;color:#666">#c47a4a</span></td>
  <td style="font-family:'FF Meta','Meta Pro','Meta',sans-serif;color:#444">Warm metallic copper. The Winner-tier eyebrow gradient anchor; used for prestige moments.</td>
</tr>
<tr>
  <td style="background:#a3e3c1;width:120px;height:80px;border:1px solid #ddd"></td>
  <td style="padding:0 16px;font-family:'FF Meta','Meta Pro','Meta',sans-serif;font-weight:600">Ocean Forest Mint<br><span style="font-family:ui-monospace,monospace;font-weight:400;color:#666">#a3e3c1</span></td>
  <td style="font-family:'FF Meta','Meta Pro','Meta',sans-serif;color:#444">A soft, slightly creamy mint with warmth carried by its red component (R163) — distinct from the icy cool-mint candy family. The "ocean" and "forest" naming evokes calm depth and growth; the "mint" gives it the freshness without going saccharine. <strong>LOCKED 2026-05-06</strong> — signature/scarce use only, like a brand pearl, not a wash.</td>
</tr>
</table>

---

## Typography — FF Meta

The single font in use across all Aurora surfaces. Hierarchy comes from weight and size, not from a second typeface. FF Meta (Erik Spiekermann, FontFont) is a humanist sans-serif with strong personality at display sizes and excellent legibility at small sizes — well-suited to badge artwork.

<div style="font-family:'FF Meta','Meta Pro','Meta','ui-sans-serif','system-ui',sans-serif;line-height:1.5">

<div style="margin:24px 0;padding:24px;background:#f6f7fb;border:1px solid #e6e8ee">
  <div style="font-size:48px;font-weight:900;letter-spacing:-0.02em;color:#1c1f2a;line-height:1">Aurora Gracewood</div>
  <div style="font-family:ui-monospace,monospace;font-size:11px;color:#7d8a99;margin-top:6px">FF Meta Black (900) · 48px · letter-spacing -0.02em — used for hero h1</div>
</div>

<div style="margin:16px 0;padding:18px;background:#f6f7fb;border:1px solid #e6e8ee">
  <div style="font-size:32px;font-weight:800;letter-spacing:-0.01em;color:#1c1f2a">Aurora Gracewood</div>
  <div style="font-family:ui-monospace,monospace;font-size:11px;color:#7d8a99;margin-top:6px">FF Meta Extra Bold (800) · 32px — primary headers, badge name candidate</div>
</div>

<div style="margin:16px 0;padding:18px;background:#f6f7fb;border:1px solid #e6e8ee">
  <div style="font-size:24px;font-weight:700;color:#1c1f2a">Aurora Gracewood</div>
  <div style="font-family:ui-monospace,monospace;font-size:11px;color:#7d8a99;margin-top:6px">FF Meta Bold (700) · 24px — secondary headers</div>
</div>

<div style="margin:16px 0;padding:18px;background:#f6f7fb;border:1px solid #e6e8ee">
  <div style="font-size:18px;font-weight:600;color:#1c1f2a">Aurora Gracewood</div>
  <div style="font-family:ui-monospace,monospace;font-size:11px;color:#7d8a99;margin-top:6px">600 / Semi-Bold · 18px — browser-synthesized; FF Meta has no native 600 weight (use Medium 500 or Bold 700 instead)</div>
</div>

<div style="margin:16px 0;padding:18px;background:#f6f7fb;border:1px solid #e6e8ee">
  <div style="font-size:16px;font-weight:500;color:#1c1f2a">Aurora Gracewood — recognition for work that endures</div>
  <div style="font-family:ui-monospace,monospace;font-size:11px;color:#7d8a99;margin-top:6px">FF Meta Medium (500) · 16px — body copy with mild emphasis</div>
</div>

<div style="margin:16px 0;padding:18px;background:#f6f7fb;border:1px solid #e6e8ee">
  <div style="font-size:16px;font-weight:400;color:#1c1f2a">Aurora Gracewood — recognition for work that endures</div>
  <div style="font-family:ui-monospace,monospace;font-size:11px;color:#7d8a99;margin-top:6px">FF Meta Book (400) · 16px — body copy</div>
</div>

<div style="margin:16px 0;padding:18px;background:#f6f7fb;border:1px solid #e6e8ee">
  <div style="font-size:11px;font-weight:800;letter-spacing:0.18em;text-transform:uppercase;color:#7d8a99">RECOGNITION · STARTER · 2026</div>
  <div style="font-family:ui-monospace,monospace;font-size:11px;color:#7d8a99;margin-top:6px">FF Meta Extra Bold (800) · 11px · letter-spacing 0.18em · uppercase — section eyebrows, year stamp candidate</div>
</div>

</div>

---

## Practical badge-design notes

- **For the Starter badge specifically**: the Aurora Light Pink (`#f4cfd9`) is the brand's signature soft accent and is consistent with "Influence" category from the awards config. Pair it with Aurora Blueberry (`#4a5fc1`) for primary marks, or use the Charcoal (`#1c1f2a`) for high-contrast typography on light surfaces.
- **For Tier 1 (Real Award Badges) — Winner / Finalist / Honoree**: each has a locked gradient identity in `index.html`'s recognition section:
  - Winner: Copper → GC Orange (`#c47a4a` → `#ffb469`)
  - Finalist: GC Cyan → GC Pink (`#45d9ff` → `#ff8fd8`)
  - Honoree: Grape → GC Pink (`#6f4ea3` → `#ff8fd8`)
- **Fonts**: FF Meta at weights 300 (Light) / 400 (Book) / 500 (Medium) / 700 (Bold) / 800 (Extra Bold) / 900 (Black) covers all hierarchy needs. FF Meta has no native 600 weight — substitute Medium 500 or Bold 700 rather than relying on browser synthesis. If a secondary/display font is added later (for badge name display), document it in `awards/CLAUDE.md` and reflect here.
- **Year stamp font candidate**: FF Meta Extra Bold (800) at small size with wide letter-spacing (0.18em+) and uppercase reads as a credential mark. Sample above.

---

## How to update this file

1. Update `D:\Great_Creations\Aurora-Gracewood\site\styles.css` first (source-of-truth).
2. Update `awards/CLAUDE.md` "Trail of changes" with what changed.
3. Re-pull values into this `system.md` so the design reference stays in sync.

When values are placeholders (like the current hexes), **never lock them into badge artwork** without confirming with Aurora. Hexes are placeholders until she finalizes — once she does, this file updates and badges reflect the locked palette.
