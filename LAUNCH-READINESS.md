# Aurora Gracewood — Launch Readiness Checklist

> **Single source of truth for "what's left before we can ship publicly."**
> Maintained by Claude as a living document. Every relevant change updates
> this file. You should be able to glance here and see status without
> asking for an inventory.

**Last updated**: 2026-05-06
**Target launch URL**: `https://auroragracewood.com/awards/` (and other AG paths)

---

## Status legend

- ✅ **Done** — shipped, tested, working
- 🟡 **In progress** — partially done; specifics in notes
- 🔲 **Pending** — planned, not started
- ❓ **User decision** — needs Andrew's input before Claude can proceed
- ⚠️ **Risk** — known concern, may bite later if not handled

---

## A. Frontend product surfaces

| Item | Status | Notes |
|---|---|---|
| Splash page (`/`) | ✅ Done | Aurora-themed, moon + curtains + trees, logo, lineage link |
| Site home (`/site/`) | ✅ Done | Hero, 4 product cards, About, Aurora's portrait, footer |
| Awards page (`/awards/`) | 🟡 In progress | Day-1 build + new pricing + recognition tiers + form gating shipped. Needs CC bundled-points slider at checkout (Phase 5). |
| Account direct (`/account/`) | ✅ Done | Profile editor with name/email/slug/bio/avatar/marketing-share fields |
| Showcase (`/showcase/`) | 🔲 Pending | Phase E — separate product page, distinct design lane |
| Directory (`/directory/`) | 🔲 Pending | Phase E |
| Editorial (`/editorial/`) | 🔲 Pending | Phase E |
| Public partial profile (`/awards/clients/<slug>`) | 🔲 Pending | Needs backend persistence; can't render other users' profiles in stub mode |

## B. Auth & accounts

| Item | Status | Notes |
|---|---|---|
| Auth stub (localStorage) | ✅ Done | Cross-product, modal-based, no redirects |
| Auth chip in nav | ✅ Done | On `/site/` and `/awards/` |
| Form gating (logged-in/logged-out) | ✅ Done | Pattern A on awards forms |
| Profile editor | ✅ Done | Name, slug, bio, avatar, marketing share |
| Superuser elevation | ✅ Done | `INITIAL_SUPERUSER_EMAIL = aandrew7.am@gmail.com` auto-elevates on signup |
| Real backend auth | 🔲 Pending | FastAPI skeleton in place; persistence + JWT + password hashing not yet implemented |
| Magic-link email auth | 🔲 Pending | Replaces password forms in Phase C++. Needs email provider (TBD). |
| OAuth provider read-only sign-in (X / LinkedIn / Instagram / TikTok / Facebook) | 🔲 Pending | Phase 5 — for Community Choice voting |
| Account deletion (real) | 🟡 Stub only | Stub clears localStorage. Real cascade (submissions, badges, votes) needed. |
| GDPR data export | 🔲 Pending | Required for EU users; needs backend persistence first |

## C. Admin system

| Item | Status | Notes |
|---|---|---|
| Role schema (Client / Agent / Regular Admin / Superuser) | ✅ Done | In Pydantic + auth.js + documented in CLAUDE.md |
| Admin dashboard UI | 🔲 Pending | At `/account/admin/`; needs role-gated route |
| Audit log | 🔲 Pending | Per Phase 2 plan in CLAUDE.md |
| Admin can view submissions | 🔲 Pending | Needs backend submission persistence |
| Admin can manage agents | 🔲 Pending | Per role architecture in CLAUDE.md |
| Notification system (in-app + email) | 🔲 Pending | Phase 2 |

## D. Awards system

| Item | Status | Notes |
|---|---|---|
| Award categories config (10 total: 9 main + 1 influencer) | ✅ Done | In `awards/config.js` with `track` field |
| Recognition tiers (Winner/Finalist/Honoree) UI | ✅ Done | On `/awards/` with year stamps |
| Pricing structure | ✅ Done | Main $199/$299/$399, Influencer $99/$149/$199 |
| Submission forms (6 paths) | ✅ Done | All forms render, gate correctly |
| Year-handling convention (`.year` class) | ✅ Done | Universal across pages |
| Submission persistence | 🟡 Stub | Saves to localStorage; needs backend |
| Stripe payment integration | 🔲 Pending | Phase 4 |
| Physical trophy design | ❓ User decision | Crystal commitment locked; specific shape/dimensions/finish needs designer pass |
| Trophy manufacturing partner | ❓ User decision | Industry options researched; no partner selected |
| Badge embed system (HMAC-signed iframes) | 🔲 Pending | Phase 5 |
| Badge artwork (per tier per category) | ❓ User decision | Designer needs to produce |

## E. Community Choice

| Item | Status | Notes |
|---|---|---|
| Mechanic v6 documented | ✅ Done | Bundled / direct / social-vote pricing locked |
| CC submission panel on `/awards/` | ✅ Done | Stub form collects basic info |
| Bundled CC slider at cat checkout | 🔲 Pending | Phase 5 — UX in awards form needs add-on slider |
| Direct CC submission flow | 🔲 Pending | Phase 5 |
| Read-only OAuth sign-in (5 platforms) | 🔲 Pending | Phase 5 — read-only is free across all platforms |
| Vote backend + leaderboard | 🔲 Pending | Phase 5 |
| Aurora-side automated honoree posting | 🔲 Pending | Phase 5 |
| Anti-fraud monitoring | 🔲 Pending | Phase 5 |

## F. Backend infrastructure

| Item | Status | Notes |
|---|---|---|
| FastAPI skeleton | ✅ Done | Routes scaffolded; handlers stubbed at 501 |
| Pydantic schemas matching frontend | ✅ Done | `app/models.py` |
| `requirements.txt` + `.env.example` + `.gitignore` | ✅ Done | All in `backend/` |
| SQLAlchemy + database (SQLite → Postgres) | 🔲 Pending | Phase C — next sub-chunk |
| Alembic migrations | 🔲 Pending | After SQLAlchemy is in |
| Real signup persistence | 🔲 Pending | After DB is in |
| Real signin (password verify + JWT issue) | 🔲 Pending | After signup persistence |
| `/api/profile` GET/PATCH wired to DB | 🔲 Pending | After signup |
| `/api/submissions` POST wired to DB | 🔲 Pending | After auth is real |
| Frontend migration from localStorage to fetch() | 🔲 Pending | One endpoint at a time |
| Rate limiting | 🔲 Pending | Backend hardening before public launch |
| Backup/restore strategy | 🔲 Pending | Once DB has real data |

## G. Legal & compliance ⚠️

| Item | Status | Notes |
|---|---|---|
| Privacy policy | 🔲 Pending ⚠️ | **LAUNCH BLOCKER**. Must list Great Creations + named subs (Aurora Gracewood, GCS, future siblings) as data-sharing scope. GDPR + CCPA disclosure required. |
| Terms of service | 🔲 Pending ⚠️ | **LAUNCH BLOCKER**. Must include: payment buys review (no guaranteed award), badge usage rules, content ownership, refund policy. |
| Refund policy | 🔲 Pending | Often part of Terms; needs explicit position on review-already-done refunds |
| Cookie / consent banner | 🔲 Pending | Required for EU traffic if any analytics/marketing cookies are used |
| Editorial-integrity disclosure | 🟡 Partial | Footer mentions Great Creations; full disclosure of GCS-relationship needs detailed text |
| Legal entity / business structure | ❓ User decision | LLC? Sole prop? Filed under what name? Needed for Stripe + tax + privacy policy entity reference |
| Footer "replace with legal details" placeholder | ⚠️ | Currently says "Replace with legal entity details before launch." Tracking. |

## H. Domain & infrastructure

| Item | Status | Notes |
|---|---|---|
| Domain: `auroragracewood.com` | ❓ User decision | User mentioned this is live — confirm ownership + DNS access |
| Domain: `aurora-gracewood.com` | ❓ User decision | Sister site — confirm ownership |
| Domain: `greatcreations.{tld}` (parent brand) | ❓ User decision | For umbrella site + auth federation; recommend grabbing now if not owned |
| DNS configuration plan | 🔲 Pending | How does `/awards/`, `/site/`, etc. get routed? Static-hosted or Python-served? |
| Hosting decision | ❓ User decision | GitHub Pages + Cloudflare? Netlify? Vercel? Self-hosted with Tailscale? Per Phase 0 plan in CLAUDE.md, me-think + Tailscale Funnel was the early choice for backend. |
| SSL/TLS certificate | 🔲 Pending | Auto via Let's Encrypt; needs hosting decision first |
| CDN / asset caching | 🔲 Pending | Especially for moon-map.jpg (1MB), aurora-portrait.png (7.5MB), treeline.png (580KB) |
| Email sending domain (for magic-link) | 🔲 Pending | Needs DKIM/SPF/DMARC records on chosen sending domain |

## I. SEO & discoverability

| Item | Status | Notes |
|---|---|---|
| Page titles + meta descriptions | 🟡 Partial | Some pages have them, some don't (account, awards) |
| Open Graph / Twitter Card tags | 🔲 Pending | Required for social sharing previews |
| Schema.org JSON-LD (Organization, Award, CreativeWork, Person) | 🔲 Pending | Per Phase 7 plan |
| `sitemap.xml` | 🔲 Pending | Auto-generated post-deploy |
| `robots.txt` | 🔲 Pending | Decide what to allow/disallow |
| Pre-rendered pages for winners / categories / judges | 🔲 Pending | Phase 7 |
| Google Search Console + Bing Webmaster | 🔲 Pending | Register at launch |
| Analytics (privacy-respecting choice — Plausible / Fathom / GA4) | ❓ User decision | |

## J. Performance & polish

| Item | Status | Notes |
|---|---|---|
| Image optimization | ⚠️ | `aurora-portrait.png` is 7.5MB — too big for production. Resize to 1500px wide + JPEG q85 → ~300KB. Same audit needed for all assets. |
| Lazy loading | 🟡 Partial | Some `<img>` tags use `loading="lazy"`; not audited site-wide |
| WebGL fallback for low-end devices / no-WebGL contexts | 🟡 Partial | Aurora canvas has try-catch + reduced-motion support |
| Mobile responsiveness | 🟡 Partial | Splash + site + awards work on mobile per testing; account page not yet mobile-tuned |
| Accessibility (WCAG audit) | 🔲 Pending | Color contrast, keyboard navigation, screen reader, focus states |
| Loading state for slow connections | 🔲 Pending | Especially for images/textures on splash |

## K. Developer / deployment infrastructure

| Item | Status | Notes |
|---|---|---|
| `.gitignore` (AG-root) | ✅ Done | This file's edit |
| `README.md` (AG-root) | ✅ Done | Quick-start + architecture overview |
| `LAUNCH-READINESS.md` | ✅ Done | This file |
| License decision | ❓ User decision | Currently TBD — proprietary by default. Decide before pushing to public GitHub. |
| GitHub Actions / CI pipeline | 🔲 Pending | Lint, test, deploy on push |
| Test infrastructure | 🟡 Partial | `backend/tests/` folder exists; no tests yet |
| Pre-commit hooks | 🔲 Pending | Lint, format, secret-scan |
| Secrets management | ⚠️ | `.env.example` documents what's needed; real secrets must NOT be committed |
| Deployment runbook | 🔲 Pending | Step-by-step deploy instructions |
| Monitoring (uptime, errors) | 🔲 Pending | Sentry / UptimeRobot / etc. |

## L. Content & assets

| Item | Status | Notes |
|---|---|---|
| Logo (canonical, alt, awards variants) | ✅ Done | `/assets/logo.png`, `/assets/altlogo.png`, `/assets/awardlogo.png` |
| Aurora portrait | ✅ Done | `/assets/aurora-portrait.png` (needs optimization for production — see Section J) |
| Brand voice doc (Aurora's voice) | ✅ Done | In Claude memory |
| Color system | ✅ Done | Aurora primary + GC family signal + universal palette in memory |
| Award badge artwork | ❓ User decision | Designer needs to produce per tier per category |
| Trophy artwork / 3D model | ❓ User decision | Material + form decision pending designer |
| Email templates (magic-link, finalist notification, winner notification) | 🔲 Pending | When email auth ships |
| Press kit / brand guidelines | 🔲 Pending | For media inquiries |

---

## L2. Interactive checklist page (NEW 2026-05-06)

A self-contained checklist UI lives at:

```
C:\Users\aandr\OneDrive\Documentos\Projects\checklists\aurora-gracewood\index.html
```

**This is internal tooling, NOT part of `auroragracewood.com`.** It's not deployed, not gated by any auth (the account/superuser system isn't built yet — it's on this very to-do list), and lives outside the AG project folder entirely. Open it directly in a browser via `file://` — no server required. Self-contained: inline CSS, inline JS, inline favicon.

**Discipline going forward** (load-bearing — Claude must follow this):

- **When an item finishes**: Claude REMOVES the `<li class="todo-item">` from the checklist's `index.html` (hard-coded edit). The item disappears entirely.
- **When a new item appears**: Claude ADDS a `<li class="todo-item">` with a unique `data-id`. Stable IDs only — never reuse a deleted ID.
- **When user has checked items**: Claude treats them as effectively done — won't re-prompt or re-litigate. Purge button clears user state but hard-coded items remain.
- **Aggressive cadence**: every conversation turn that completes an item should result in the corresponding `<li>` removal in the same turn. No "I'll update it later." Claude does it now.

## M. What CLAUDE will track proactively going forward

This file is updated automatically when:
- A new strategic decision lands (added to relevant section with status)
- A planned item ships (status flips to ✅)
- A new launch-blocker is identified (added with ⚠️)
- A user-decision item gets resolved (status flips to ✅ with answer noted)

**You should NOT need to ask "what's pending" — this file is the answer.**

If something isn't in this file, raise it; I'll add it. If a status seems
stale, flag it; I'll re-audit.

---

## N. Known launch blockers (must be resolved before public launch)

1. **Privacy policy** drafted + published
2. **Terms of service** drafted + published
3. **Legal entity** decided + named in footer + Stripe account
4. **Real backend persistence** (DB + auth + submissions)
5. **Real payment flow** (Stripe Checkout integration)
6. **Domain DNS configuration** (auroragracewood.com routing)
7. **Hosting decision + deployment** (where does this run?)
8. **Image optimization** (especially portrait + textures)

Everything else can iterate after launch. The 8 items above cannot.

---

## P. Security & hardening ⚠️

This section was missing from the initial pass. Tracking now. **Items marked
🔒 LAUNCH BLOCKER must be addressed before public launch handles real money
or real user data.**

### Authentication & sessions

| Item | Status | Notes |
|---|---|---|
| Password hashing (bcrypt via passlib) | 🔲 Pending 🔒 | `passlib[bcrypt]` already in `requirements.txt`. Implement when DB lands. |
| JWT signing secret in env (rotated, never committed) | 🟡 Stub | `JWT_SECRET` in `.env.example` — needs real value pre-launch + rotation strategy |
| JWT expiration + refresh token strategy | 🔲 Pending 🔒 | Currently `JWT_TTL_HOURS=24` in env template; refresh flow not designed |
| Email verification on signup | 🔲 Pending 🔒 | Required to prevent fake-account spam + needed for magic-link auth |
| Account lockout after N failed sign-ins | 🔲 Pending | Brute-force defense |
| Password reset via email | 🔲 Pending | Standard flow needed |
| 2FA option (TOTP) for admins | 🔲 Pending | Especially Superuser/Regular Admin tiers |
| Account enumeration prevention | 🔲 Pending | Sign-in errors should be generic ("invalid credentials"), not "no such email" |
| Session/cookie flags (Secure, HttpOnly, SameSite=Strict) | 🔲 Pending 🔒 | When real session cookies replace localStorage |
| Bootstrap superuser via `INITIAL_SUPERUSER_EMAIL` | ✅ Done | Only the named email gets superuser; everyone else is client |

### Web app security

| Item | Status | Notes |
|---|---|---|
| HTTPS-only enforcement (HTTP → HTTPS redirect) | 🔲 Pending 🔒 | Standard via hosting platform |
| HSTS header (`Strict-Transport-Security`) | 🔲 Pending 🔒 | Forces HTTPS in browsers; long max-age + includeSubDomains + preload |
| Content Security Policy (CSP) | 🔲 Pending 🔒 | Restricts script/style/image sources to trusted origins |
| X-Frame-Options / frame-ancestors | 🔲 Pending | Prevents clickjacking |
| X-Content-Type-Options: nosniff | 🔲 Pending | MIME-type sniffing prevention |
| Referrer-Policy | 🔲 Pending | Limits info leaked to outbound links |
| CSRF tokens on state-changing requests | 🔲 Pending 🔒 | Or use SameSite=Strict cookies + bearer tokens |
| Subresource Integrity (SRI) for CDN scripts | 🔲 Pending | Currently using Three.js from cdnjs without SRI hash — fix |
| CORS allowlist (not wildcard) | ✅ Done | Backend `.env.example` enumerates origins explicitly |

### Application input/output

| Item | Status | Notes |
|---|---|---|
| SQL injection prevention | 🟡 Auto via SQLAlchemy | Parameterized queries when ORM is in; no raw SQL string concatenation |
| XSS — output escaping in templates | 🟡 Partial | `auth.js` has `esc()` helper for chip rendering; site-wide audit pending |
| Form input validation (server-side) | 🟡 Stub | Pydantic models validate on backend; frontend validation is courtesy only |
| File upload validation (avatars, badges) | 🔲 Pending | Size limits, MIME-type whitelist, virus scanning at scale |
| Rate limiting (auth endpoints, signup, voting) | 🔲 Pending 🔒 | Per-IP + per-account; Redis or in-memory bucket |
| CAPTCHA on public forms (signup, submission) | 🔲 Pending 🔒 | hCaptcha (privacy-respecting) preferred over reCAPTCHA |
| Anti-fraud on Community Choice voting | 🟡 Designed | Account-quality threshold + unique constraint per vote — needs implementation when voting ships |

### Data & privacy

| Item | Status | Notes |
|---|---|---|
| Secrets in env vars only, never committed | ✅ Done | `.gitignore` excludes `.env`; `.env.example` has placeholders only |
| Logging hygiene (no PII in logs) | 🔲 Pending | Audit logging strategy when backend ships |
| Database backup strategy | 🔲 Pending 🔒 | Daily SQLite snapshot → off-site (Backblaze B2 or similar); 30-day rotation |
| Backup encryption | 🔲 Pending | Backups should be encrypted at rest |
| Data minimization | 🟡 Partial | Profile collects only essentials; needs review when more fields added |
| GDPR — right to access (data export) | 🔲 Pending 🔒 | EU users entitled to export their data |
| GDPR — right to erasure (real account deletion) | 🟡 Stub only | localStorage clear works; needs DB cascade when persistence lands |
| Cookie consent banner (EU traffic) | 🔲 Pending 🔒 | Required IF analytics/marketing cookies are used |
| Privacy policy lists data shared with Great Creations subs | 🔲 Pending 🔒 | Per the locked editorial-integrity wall + cross-brand sharing scope |

### Operational security

| Item | Status | Notes |
|---|---|---|
| DDoS protection (Cloudflare proxy) | 🔲 Pending | Free tier sufficient for launch |
| WAF (Web Application Firewall) | 🔲 Pending | Cloudflare or similar |
| Dependency vulnerability scanning | 🔲 Pending | `pip-audit` for Python, Dependabot for GitHub |
| Pen-test before public launch | 🔲 Pending | Manual or via service (HackerOne/etc.) |
| Bug bounty / responsible disclosure email | 🔲 Pending | `security@auroragracewood.com` mailbox |
| Audit log for admin actions | 🔲 Pending 🔒 | Per Phase 2 plan in CLAUDE.md — every admin action is logged immutably |
| Monitoring + alerting (uptime, error rates) | 🔲 Pending | Sentry / UptimeRobot / etc. |
| Incident response plan | 🔲 Pending | Runbook for breach response |

---

## Q. Open questions for Andrew

These need your input before Claude can act. **Listed proactively here so you
don't have to remember to ask.** Reply at any time, in any order — I'll update
this section as decisions come in.

### Q1. Legal entity & business

- **Q1.1** What's the legal entity name running Aurora Gracewood? (LLC? Sole prop? Registered name to put in footer + Stripe + privacy policy?)
- **Q1.2** What state/jurisdiction is the entity registered in? Affects tax + dispute resolution.
- **Q1.3** Tax ID / EIN to use for Stripe + invoicing?
- **Q1.4** Will Great Creations also be a registered legal entity (umbrella), or is it just a brand persona right now?
- **Q1.5** Who drafts the privacy policy + terms of service? (You write? Lawyer? Generator like Termly/iubenda? Claude drafts and you review?)
- **Q1.6** Refund policy stance: no refunds once review begins? Refundable until queued? Specific window?
- **Q1.7** Currencies — USD only at launch?
- **Q1.8** Are there jurisdictions you want to BLOCK (countries you won't accept submissions from)? Often relevant for sanctioned countries.

### Q2. Domains & DNS

- **Q2.1** Do you own `auroragracewood.com`? `aurora-gracewood.com`? Both?
- **Q2.2** Do you own `greatcreations.com` (or any TLD variant)? If not, recommend grabbing now before squatters do — the parent brand needs a home for legal/disclosure pages.
- **Q2.3** DNS provider — Cloudflare? Other? (Cloudflare gives free DDoS + caching as side benefit.)
- **Q2.4** Subdomain strategy: `auth.auroragracewood.com` vs `auroragracewood.com/account/`? (Currently planning the path-based version.)

### Q3. Hosting

- **Q3.1** Where do you want to host the static frontend? (GitHub Pages? Netlify? Vercel? Cloudflare Pages? Self-hosted via Tailscale Funnel on me-think per the original Phase 0 plan?)
- **Q3.2** Where do you want to host the FastAPI backend? Same place, or separate? (Render / Fly.io / DigitalOcean / your me-think + Tailscale?)
- **Q3.3** Database hosting decision: SQLite is fine for launch (single small file). When do we plan to migrate to Postgres? (Probably when you exceed ~10K users or want concurrent writes.)

### Q4. Payment

- **Q4.1** Stripe — do you have a Stripe account? Personal or business?
- **Q4.2** Bank account for payouts — personal or business?
- **Q4.3** State-level sales tax requirements — does your state require sales tax on digital services? (Some do, many don't — affects pricing display.)
- **Q4.4** Alternative payment methods at launch — Apple Pay / Google Pay (free via Stripe), PayPal (separate integration), crypto (probably not at launch)?

### Q5. Email infrastructure

- **Q5.1** Email sending domain — `auroragracewood.com`? Or use Resend's `resend.dev` temporarily and migrate?
- **Q5.2** Email provider — Resend (developer-friendly, cheap) / Postmark (great deliverability, slightly pricier) / Mailgun (legacy, OK) / Amazon SES (cheapest, most setup)?
- **Q5.3** Transactional vs. marketing emails — separate sending domains? (Best practice; protects deliverability.)
- **Q5.4** Magic-link auth or password auth at launch? (Magic-link is more secure + better UX, but requires email infrastructure ready.)

### Q6. Trophy production

- **Q6.1** Have you contacted any custom trophy manufacturers? Industry options: Crown Awards, EDCO, smaller boutique studios.
- **Q6.2** Year-1 setup budget approval — ~$5K one-time setup + ~$2K/year ongoing for the locked spec?
- **Q6.3** When is the year-end ceremony / announcement? Trophies typically need 6-8 weeks lead time. Affects when trophies must be ordered.
- **Q6.4** Designer for the trophy artwork — you? Commissioned? Aurora Gracewood persona's hand?

### Q7. Brand assets

- **Q7.1** ✅ Aurora portrait — replaced 2026-05-06 with new asset (896×1152, 1.49MB). Final production direction confirmed. Future pre-launch optimization pass to drop file to ~250-300KB JPEG.
- **Q7.2** Logo SVG — do you have vector versions of `logo.png` / `altlogo.png` / `awardlogo.png`? (Vector scales infinitely, smaller file size, cleaner at any zoom.)
- **Q7.3** Color palette hex values — currently using placeholders in CSS. Do you want me to lock specific brand-tested values, or wait?
- **Q7.4** Aurora's brand voice — keep the first-person editorial voice ("I notice work," "my practice")?
- **Q7.5** Award badge artwork — when does design start? Each tier × each category needs a distinct visual.

### Q8. Editorial & operations

- **Q8.1** Who reviews submissions? (You alone? You + 1-2 judges? AI-assisted via Aurora's agents per role architecture?)
- **Q8.2** Are judges paid? How much per cycle?
- **Q8.3** Rubric document — exists yet, or needs drafting? (We need clear scoring criteria per category.)
- **Q8.4** Editorial Coverage tier — who writes the feature articles? You? Freelancers? AI-drafted + human-edited?
- **Q8.5** Directory tier — vetting criteria? Who reviews listing applications?
- **Q8.6** Sponsor inquiry — who handles sponsor relationships? You? Sales contractor?

### Q9. User accounts & data

- **Q9.1** Marketing-share consent — currently opt-in default OFF. Confirm this is the right default? (Most legally-conservative; can change later.)
- **Q9.2** Email verification on signup — required immediately (block use until verified) or grace period (let them in, push verification)?
- **Q9.3** Password complexity — currently 8-char minimum. Bump to 12? Require complexity (upper + lower + digit + symbol)?
- **Q9.4** Magic-link auth as primary, OR password as primary with magic-link as backup?
- **Q9.5** Session length — currently planning 24 hours. Longer for "remember me"?

### Q10. Tech decisions

- **Q10.1** GitHub repo — public (open source) or private? Affects license decision.
- **Q10.2** License — if going public: MIT? AGPL? Apache 2.0? Or proprietary with explicit notice?
- **Q10.3** CI/CD — GitHub Actions? Other?
- **Q10.4** Image optimization pipeline — manual (resize before commit) or automated (Cloudinary / ImageKit / build-time)?
- **Q10.5** Search functionality at launch — needed for browsing winners / providers / categories? Or skip until v2?
- **Q10.6** Aurora Awards name — finalize "Aurora Awards" or leave open in case it changes? (Internal slugs already use generic `awards` to support rename.)

### Q11. Showcase / Directory / Editorial (future products)

- **Q11.1** Showcase model — submissions reviewed and accepted? Curator's pick from existing winners? Open submission?
- **Q11.2** Directory model — paid listings only ($99 fee already locked)? Free with paid premium tier?
- **Q11.3** Editorial model — pitch-driven (applicants pay for coverage consideration)? Curator-driven (Aurora picks topics)?
- **Q11.4** Launch order — which of these three ships first after Aurora Awards is live? My recommendation: Showcase (lowest stakes, leverages winner data).

### Q12. Community Choice (Phase 5)

- **Q12.1** Phase 1 platform priority for OAuth voting — confirm X / LinkedIn / Instagram / TikTok / Facebook? Or different mix?
- **Q12.2** Aurora's social media accounts — created on each platform, or use existing personal accounts during launch?
- **Q12.3** Anti-fraud thresholds — minimum follower count + minimum account age for a vote to count? My proposal: 5 followers, 30 days. Confirm?

### Q13. Operational & support

- **Q13.1** Customer support — email-only (`support@auroragracewood.com`)? Live chat? Self-serve docs?
- **Q13.2** Office hours / response SLA — what do applicants get told? "We respond within 2 business days"?
- **Q13.3** Launch publicity — soft launch (friends & first applicants) vs. press launch (PR firm, announcement, etc.)?
- **Q13.4** Beta period — do you want a private beta with selected early applicants before opening to public?

---

## O. Sequence I recommend (subject to your direction)

1. **Phase C — backend persistence** (DB + signup/signin/profile): unblocks 5 things above
2. **Phase 4 — Stripe + payment**: unblocks paid submissions
3. **Legal docs drafting** (privacy + terms + refund): unblocks public launch
4. **Hosting decision + first deploy**: unblocks public access
5. **Phase 5 — badge embed system + OAuth voting**: unblocks Community Choice + winner badges
6. **Phase E — Showcase / Directory / Editorial pages**: rounds out the AG product family
7. **SEO + analytics + monitoring**: post-launch polish

This order handles launch blockers first, then adds product depth, then adds
post-launch infrastructure.
