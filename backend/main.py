from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
import sqlite3, hashlib, hmac, os, secrets, time, json, base64, html as html_mod, re
import urllib.request, urllib.error
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "aurora.db"
LOG_PATH = ROOT / "verification-links.log"
SITE_DIR = ROOT / "site"
REALMS_DIR = ROOT / "account"
SUPERUSER_EMAIL = os.environ.get("SUPERUSER_EMAIL", "").lower()

BIO_MAX = 160  # X/Twitter style
CLIENT_ID_START = 9100  # clients use IDs >= 9100; admin/special use < 9100
LINKS_MAX = 6  # max custom links on a public profile

app = FastAPI(title="Aurora Gracewood")

# ============== THEMES ==============
# Closed enum on free tier. Curated values; user stores enum key only.
# (Hex values reuse Great Creations placeholder palette; refine when finalized.)

THEMES = {
    "aurora-light": {
        "name": "Aurora Light",
        "bg": "#f6f7fb", "fg": "#1c1f2a",
        "accent": "#f4cfd9", "accent2": "#4a5fc1",
        "muted": "#7d8a99", "card": "#ffffff",
        "border": "#e6e8ee",
        "font": "'Inter', system-ui, -apple-system, sans-serif",
    },
    "duskpink": {
        "name": "Duskpink",
        "bg": "#1c1f2a", "fg": "#f6f7fb",
        "accent": "#f4cfd9", "accent2": "#a3e3c1",
        "muted": "#8089a4", "card": "#252a3a",
        "border": "#3a3f55",
        "font": "'Inter', system-ui, -apple-system, sans-serif",
    },
    "forestlow": {
        "name": "Forestlow",
        "bg": "#a3e3c1", "fg": "#2c5e3f",
        "accent": "#738c5e", "accent2": "#2c5e3f",
        "muted": "#5a8064", "card": "#c5ecd1",
        "border": "#85bc9b",
        "font": "'Inter', system-ui, -apple-system, sans-serif",
    },
    "monochrome": {
        "name": "Monochrome",
        "bg": "#fafafa", "fg": "#000000",
        "accent": "#e8e8e8", "accent2": "#000000",
        "muted": "#666666", "card": "#fafafa",
        "border": "#bbbbbb",
        "font": "'IBM Plex Mono', ui-monospace, monospace",
    },
    "honoree-gold": {
        "name": "Honoree Gold",
        "bg": "#1c1f2a", "fg": "#f6f7fb",
        "accent": "#c47a4a", "accent2": "#e0a868",
        "muted": "#9b8b75", "card": "#252a3a",
        "border": "#403428",
        "font": "'Inter', system-ui, -apple-system, sans-serif",
    },
}
DEFAULT_THEME = "aurora-light"

# Themes that require a specific role_name in user_roles to be selectable.
THEME_REQUIRES_ROLE = {
    "honoree-gold": "Honoree",
}

def themes_available_to(user_id):
    """Return the list of theme keys this user is allowed to choose."""
    if not user_id:
        return [k for k in THEMES if k not in THEME_REQUIRES_ROLE]
    with db() as c:
        owned = set(r["role_name"] for r in c.execute(
            "SELECT role_name FROM user_roles WHERE user_id = ?", (user_id,)
        ).fetchall())
    return [k for k in THEMES if k not in THEME_REQUIRES_ROLE or THEME_REQUIRES_ROLE[k] in owned]

# Reserved at the / level (single-letter /u/ prefix isolates from these,
# but we still forbid them as custom slugs for hygiene).
SLUG_RESERVED = {"u","work","api","admin","client","g-1vl00d","account","site","verify","static","signin","signup","login","logout","about","privacy","terms","contact","search","help","support","www","aurora-gracewood","greatcreations","null","undefined"}

SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?$|^[a-z0-9]$")

def validate_slug(slug):
    """Validate a custom slug. Raises HTTPException if invalid. Returns lowercased slug on success."""
    if slug is None or not isinstance(slug, str):
        raise HTTPException(400, "Slug must be a string")
    s = slug.strip().lower()
    if len(s) < 1 or len(s) > 32:
        raise HTTPException(400, "Slug must be 1-32 characters")
    if s.isdigit():
        raise HTTPException(400, "Numeric-only slugs are reserved for user IDs")
    if not SLUG_RE.match(s):
        raise HTTPException(400, "Slug: lowercase letters, digits, hyphens; cannot start or end with a hyphen")
    if s in SLUG_RESERVED:
        raise HTTPException(400, f"'{s}' is reserved")
    return s

# ============== DB ==============

def db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            username TEXT UNIQUE,
            display_name TEXT,
            password_hash TEXT,
            role TEXT NOT NULL DEFAULT 'client',
            status TEXT NOT NULL DEFAULT 'pending',
            bio TEXT,
            avatar_url TEXT,
            slug TEXT UNIQUE,
            public_profile INTEGER DEFAULT 0,
            verify_token TEXT,
            verify_expires INTEGER,
            created_at INTEGER NOT NULL,
            verified_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS user_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role_name TEXT NOT NULL,
            year INTEGER,
            emoji TEXT,
            granted_by INTEGER,
            granted_at INTEGER NOT NULL,
            UNIQUE (user_id, role_name, year)
        );
        CREATE TABLE IF NOT EXISTS settings (
            scope TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            updated_at INTEGER NOT NULL,
            PRIMARY KEY (scope, key)
        );
        CREATE TABLE IF NOT EXISTS notification_prefs (
            user_id INTEGER NOT NULL,
            channel TEXT NOT NULL,
            via_email INTEGER DEFAULT 0,
            via_sms INTEGER DEFAULT 0,
            via_inapp INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, channel)
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            user_agent TEXT,
            ip TEXT,
            created_at INTEGER NOT NULL,
            last_seen_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            actor_role TEXT,
            action TEXT NOT NULL,
            detail TEXT,
            ip TEXT,
            created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user INTEGER NOT NULL,
            to_user INTEGER NOT NULL,
            subject TEXT,
            body TEXT NOT NULL,
            read_at INTEGER,
            created_at INTEGER NOT NULL
        );
        """)
        existing = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if existing == 0:
            now = int(time.time())
            # Clients seed with slug=str(id); admin/superuser keep readable text slugs.
            seeds = [
                # uid, email, username, display, role, status, bio, public, slug
                (1,    "superuser@aurora.local", "aurora",  "Aurora",       "superuser", "active", "I notice work that endures.", 1, "aurora"),
                (2,    "admin@aurora.local",     "admin1",  "Admin Test",   "admin",     "active", "Editorial admin for testing.", 1, "admin1"),
                (9100, "client@aurora.local",    "client1", "Client Test",  "client",    "active", "Test client account.",        0, "9100"),
            ]
            for uid, email, username, display, role, status, bio, public, slug in seeds:
                c.execute("""INSERT INTO users (id, email, username, display_name, role, status, bio, slug, public_profile, created_at, verified_at)
                             VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                          (uid, email, username, display, role, status, bio, slug, public, now, now))
            for uid in (1, 2, 9100):
                for ch in ("submissions", "refunds", "weekly_digest", "system_alerts"):
                    c.execute("INSERT INTO notification_prefs (user_id, channel, via_email, via_inapp) VALUES (?,?,1,1)", (uid, ch))
            for k, v in (("site_name","Aurora Gracewood"),("tagline","Awards, recognition, editorial."),("currency","CAD"),("submission_window_open","false")):
                c.execute("INSERT INTO settings (scope, key, value, updated_at) VALUES (?,?,?,?)", ("site", k, v, now))
        c.commit()
init_db()

STARTER_BADGE_SLUG = "starter"
STARTER_DESIGN_YEAR = 2026

def migrate_db():
    with db() as c:
        cols = [r["name"] for r in c.execute("PRAGMA table_info(users)").fetchall()]
        if "profile_lock" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN profile_lock INTEGER DEFAULT 0")
        if "admin_changed_at" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN admin_changed_at INTEGER")
        if "theme" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN theme TEXT")
        if "links_json" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN links_json TEXT")
        # Collapse auto-generated client slugs (slug == username) AND backfill any NULL slugs to numeric ID form.
        c.execute("UPDATE users SET slug = CAST(id AS TEXT) WHERE slug IS NULL OR (role = 'client' AND slug = username)")
        # Demo: ensure superuser /u/aurora is publicly viewable (no-op once true).
        c.execute("UPDATE users SET public_profile = 1 WHERE role = 'superuser' AND slug = 'aurora' AND public_profile = 0")
        # issued_badges -- per-user issuance records (which user got which badge, when, status)
        # FROZEN-AT-ISSUANCE FIELDS (per architectural decision 2026-05-08):
        #   awardee_text — the recipient's display_name as of grant moment, uppercased,
        #     stamped on the badge artwork forever. Never updates if user later changes name.
        #   destination_url — where clicking the badge goes, set at grant from BADGE_REGISTRY's
        #     default_destination template (e.g. "/u/{slug}" → resolved to "/u/9100" at grant).
        #   These two + design_year are the per-issuance variables. Everything else
        #     (artwork, title, subtitle, category, form factors) is per-badge-type in BADGE_REGISTRY.
        c.execute("""
            CREATE TABLE IF NOT EXISTS issued_badges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                badge_slug TEXT NOT NULL,
                design_year INTEGER NOT NULL,
                granted_at INTEGER NOT NULL,
                granted_by INTEGER,
                granted_reason TEXT,
                revoked_at INTEGER,
                revoked_by INTEGER,
                revoked_reason TEXT,
                hidden_on_profile INTEGER DEFAULT 0,
                awardee_text TEXT,
                destination_url TEXT,
                UNIQUE(user_id, badge_slug)
            )
        """)
        # Forward-add columns for any DB created on the older schema
        existing_cols = {row[1] for row in c.execute("PRAGMA table_info(issued_badges)").fetchall()}
        if "awardee_text" not in existing_cols:
            c.execute("ALTER TABLE issued_badges ADD COLUMN awardee_text TEXT")
        if "destination_url" not in existing_cols:
            c.execute("ALTER TABLE issued_badges ADD COLUMN destination_url TEXT")

        # Auth additions: superuser-style locked username + password reset flow
        existing_user_cols = {row[1] for row in c.execute("PRAGMA table_info(users)").fetchall()}
        if "username_locked" not in existing_user_cols:
            c.execute("ALTER TABLE users ADD COLUMN username_locked INTEGER DEFAULT 0")
        if "password_reset_token" not in existing_user_cols:
            c.execute("ALTER TABLE users ADD COLUMN password_reset_token TEXT")
        if "password_reset_expires" not in existing_user_cols:
            c.execute("ALTER TABLE users ADD COLUMN password_reset_expires INTEGER")

        # Migrate the seeded superuser to the production email + locked username, IDEMPOTENT —
        # only fires if still on the seed values (id=1 + email=superuser@aurora.local).
        c.execute("""UPDATE users
                     SET email = 'superuser@aurora-gracewood.com',
                         username = 'superuser',
                         username_locked = 1,
                         status = 'pending'
                     WHERE id = 1 AND email = 'superuser@aurora.local'""")

        # Retroactive grant: every existing user gets the Starter badge with frozen fields.
        # design_year still STARTER_DESIGN_YEAR; awardee_text and destination_url computed per user.
        # Starter badge funnels clicks to /awards/?from={slug} (decided 2026-05-08): when a
        # recipient embeds the badge on their site, reader clicks land on the awards platform.
        now = int(time.time())
        for u in c.execute("SELECT id, slug, username, display_name FROM users").fetchall():
            uid, slug, username, display_name = u[0], u[1], u[2], u[3]
            awardee_text = ((display_name or username or "").strip().upper())
            slug_for_url = slug or str(uid)
            destination_url = f"/awards/?from={slug_for_url}"
            c.execute("""
                INSERT OR IGNORE INTO issued_badges
                    (user_id, badge_slug, design_year, granted_at, granted_reason, hidden_on_profile,
                     awardee_text, destination_url)
                VALUES (?, ?, ?, ?, 'signup_retroactive', 0, ?, ?)
            """, (uid, STARTER_BADGE_SLUG, STARTER_DESIGN_YEAR, now, awardee_text, destination_url))
        # Backfill frozen fields on rows created BEFORE the columns existed (pre-2026-05-08 deploys).
        # Each row gets its awardee_text and destination_url derived from the user's CURRENT state
        # — this is the freeze moment for any pre-existing test data.
        c.execute("""
            UPDATE issued_badges
            SET awardee_text = (
                    SELECT UPPER(COALESCE(NULLIF(TRIM(u.display_name), ''), u.username, ''))
                    FROM users u WHERE u.id = issued_badges.user_id
                )
            WHERE awardee_text IS NULL OR awardee_text = ''
        """)
        c.execute("""
            UPDATE issued_badges
            SET destination_url = '/awards/?from=' || COALESCE(
                (SELECT slug FROM users WHERE id = issued_badges.user_id),
                CAST(user_id AS TEXT)
            )
            WHERE destination_url IS NULL OR destination_url = ''
        """)
        c.commit()
migrate_db()

def _resolve_destination_template(template, recipient):
    """Resolve a destination_url template by substituting {slug} and {id} with the recipient's
    actual values at grant time. Frozen after substitution — destination_url is set forever."""
    slug = recipient.get("slug") or str(recipient.get("id"))
    return (template or "")\
        .replace("{slug}", slug)\
        .replace("{id}", str(recipient.get("id")))

def grant_starter_badge(user_id, granted_by=None, reason="signup"):
    """Auto-grant the Starter badge to a user. Idempotent — won't duplicate if already issued.
    Captures awardee_text + destination_url at grant moment so they're frozen forever.
    After the DB row is committed, renders all 9 form factor SVGs and commits each to
    auroragracewood/badges via GitHub API. The static files are then served by GitHub Pages
    forever; Python is out of the embed-view loop."""
    with db() as c:
        u = c.execute("SELECT id, slug, username, display_name FROM users WHERE id = ?", (user_id,)).fetchone()
        if not u:
            return
        recipient = {"id": u[0], "slug": u[1], "username": u[2], "display_name": u[3]}
        awardee_text = ((recipient["display_name"] or recipient["username"] or "").strip().upper())
        badge_def = BADGE_REGISTRY.get(STARTER_BADGE_SLUG, {})
        destination_url = _resolve_destination_template(
            badge_def.get("default_destination", "/u/{slug}"), recipient
        )
        # Idempotent insert. If row already exists, this is a no-op (row stays as-is).
        existed_before = c.execute(
            "SELECT 1 FROM issued_badges WHERE user_id = ? AND badge_slug = ?",
            (user_id, STARTER_BADGE_SLUG)
        ).fetchone() is not None
        c.execute("""
            INSERT OR IGNORE INTO issued_badges
                (user_id, badge_slug, design_year, granted_at, granted_by, granted_reason,
                 hidden_on_profile, awardee_text, destination_url)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
        """, (user_id, STARTER_BADGE_SLUG, STARTER_DESIGN_YEAR, int(time.time()), granted_by, reason,
              awardee_text, destination_url))
        c.commit()

    # After DB grant: render + commit static SVGs to the badges repo. Synchronous in the request
    # so the recipient's badge artwork is live the moment the grant returns. Failure to commit
    # doesn't unwind the DB grant — admins can re-trigger render via a separate endpoint later.
    if not existed_before:
        try:
            render_and_commit_badge(STARTER_BADGE_SLUG, recipient, STARTER_DESIGN_YEAR, awardee_text)
        except Exception:
            # Don't fail signup if GitHub commit hiccups. Future: log to activity table for retry.
            pass

PERMISSIONS = {
    "superuser": ["Manage all users","Promote / demote admins","Create / close award cycles","Review and score all submissions","Publish editorial content","Configure site settings","Override votes (Community Choice)","Issue refunds via Stripe","Modify award rubrics","Manage trophies pipeline","Access all subsidiary data","Export full database","Audit log access","Run database migrations"],
    "admin":     ["Manage clients (read + suspend)","Review submissions","Score submissions","Draft editorial content","View notifications","View own activity","Send messages to clients","Send messages to superuser"],
    "client":    ["Edit own profile","Submit work to award cycles","View own submissions","View own notifications","Send messages to admin/superuser","View public award winners"],
}

ROLE_EMOJI = {"Honoree":"🎗","Finalist":"🥈","Winner":"🏆","Partner":"🤝","Provider":"🤝","Sponsor":"🤝","Supporter":"❤","Voter":"❤","Fan":"❤","Actor":"🥽"}

def resolve_slug(slug):
    """Look up a user by either custom slug or numeric ID. Returns user dict or None."""
    with db() as c:
        r = c.execute("SELECT * FROM users WHERE slug = ?", (slug,)).fetchone()
        if r: return dict(r)
        if slug.isdigit():
            r = c.execute("SELECT * FROM users WHERE id = ?", (int(slug),)).fetchone()
            if r: return dict(r)
    return None

_USER_COLS = "id, email, username, display_name, role, status, bio, avatar_url, slug, public_profile, profile_lock, admin_changed_at, theme, links_json"

def get_actor(request):
    """Returns the acting user dict, or None if no auth.

    Two paths:
      1. Real session cookie `ag_session` → looked up in `sessions` table → user
      2. Dev override `?as=N` query param → impersonate user N (kept for now;
         should be removed before public launch)
    Cookie path takes precedence if both are present.
    """
    sid = request.cookies.get("ag_session")
    if sid:
        with db() as c:
            r = c.execute(
                f"SELECT {_USER_COLS} FROM users WHERE id = (SELECT user_id FROM sessions WHERE id = ?)",
                (sid,)
            ).fetchone()
            if r:
                c.execute("UPDATE sessions SET last_seen_at = ? WHERE id = ?", (int(time.time()), sid))
                c.commit()
                return dict(r)
    as_id = request.query_params.get("as")
    if not as_id: return None
    try: uid = int(as_id)
    except: return None
    with db() as c:
        r = c.execute(f"SELECT {_USER_COLS} FROM users WHERE id = ?", (uid,)).fetchone()
        return dict(r) if r else None

def log_activity(user_id, action, detail=None):
    with db() as c:
        role = None
        if user_id:
            r = c.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
            role = r["role"] if r else None
        c.execute("INSERT INTO activity (user_id, actor_role, action, detail, created_at) VALUES (?,?,?,?,?)",
                  (user_id, role, action, detail, int(time.time())))
        c.commit()

def next_user_id(role):
    with db() as c:
        if role == "client":
            r = c.execute("SELECT MAX(id) FROM users WHERE id >= ?", (CLIENT_ID_START,)).fetchone()
            return (r[0] or (CLIENT_ID_START - 1)) + 1
        r = c.execute("SELECT MAX(id) FROM users WHERE id < ?", (CLIENT_ID_START,)).fetchone()
        return (r[0] or 0) + 1

# =====================================================================
# AUTH — password hashing, sessions, email sending, signup/verify/signin
# =====================================================================

PUBLIC_BASE_URL = "https://aurora-gracewood.com"
EMAIL_FROM = "Aurora Gracewood <hello@aurora-gracewood.com>"
RESEND_KEY_FILE = ROOT / ".resend_key"
SESSION_COOKIE = "ag_session"
SESSION_TTL_SECS = 60 * 60 * 24 * 30  # 30 days

def hash_password(password):
    """scrypt with random salt, 32-byte output. Format: scrypt$N$r$p$salt_b64$hash_b64."""
    salt = secrets.token_bytes(16)
    n, r, p, dklen = 16384, 8, 1, 32
    h = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=dklen, maxmem=64*1024*1024)
    return f"scrypt${n}${r}${p}${base64.b64encode(salt).decode()}${base64.b64encode(h).decode()}"

def verify_password(password, stored):
    if not stored or not stored.startswith("scrypt$"):
        return False
    try:
        parts = stored.split("$")
        if len(parts) != 6: return False
        n, r, p = int(parts[1]), int(parts[2]), int(parts[3])
        salt = base64.b64decode(parts[4])
        expected = base64.b64decode(parts[5])
        h = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=len(expected), maxmem=64*1024*1024)
        return hmac.compare_digest(h, expected)
    except Exception:
        return False

def generate_token():
    return secrets.token_urlsafe(32)

def _read_resend_key():
    if not RESEND_KEY_FILE.exists():
        return None
    return RESEND_KEY_FILE.read_text(encoding="utf-8").strip()

def send_email(to_addr, subject, html, text=None):
    """Send via Resend API. Returns (ok, msg). API key from .resend_key file (deployed
    separately to me-think; not in source). Stdlib-only."""
    api_key = _read_resend_key()
    if not api_key:
        return False, "no resend api key"
    payload = {"from": EMAIL_FROM, "to": [to_addr], "subject": subject, "html": html}
    if text:
        payload["text"] = text
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # Cloudflare in front of api.resend.com blocks default Python-urllib UA with
            # error 1010. Set a real-ish UA to pass the bot-signature check.
            "User-Agent": "Aurora-Gracewood-Backend/1.0 (FastAPI)",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
            return True, data.get("id", "ok")
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}"
    except Exception as e:
        return False, f"err: {str(e)[:300]}"

def create_session(user_id, request):
    sid = secrets.token_urlsafe(32)
    user_agent = (request.headers.get("user-agent") or "")[:255]
    ip = (request.client.host if request.client else "") or ""
    now = int(time.time())
    with db() as c:
        c.execute("INSERT INTO sessions (id, user_id, user_agent, ip, created_at, last_seen_at) VALUES (?,?,?,?,?,?)",
                  (sid, user_id, user_agent, ip, now, now))
        c.commit()
    return sid

def _attach_session(response, sid):
    response.set_cookie(SESSION_COOKIE, sid,
                        httponly=True, secure=True, samesite="lax",
                        max_age=SESSION_TTL_SECS, path="/")
    return response

def _post_signin_redirect(role):
    return {"superuser": "/g-1vl00d/superuser",
            "admin":     "/admin/admin",
            "client":    "/client/client"}.get(role, "/")

def _simple_page(title, message):
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{title} · Aurora Gracewood</title>
<style>body{{margin:0;background:linear-gradient(135deg,#1c1f2a,#0a0a0e);color:#f6f7fb;font-family:Inter,sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}}.card{{background:rgba(28,31,42,.96);border:1px solid rgba(255,255,255,.1);border-radius:18px;padding:32px;max-width:440px}}h1{{color:#a3e3c1;margin:0 0 8px}}p{{color:rgba(246,247,251,.78);line-height:1.55}}a{{color:#4a5fc1}}</style></head>
<body><div class="card"><h1>{title}</h1><p>{message}</p><p><a href="/awards/">Aurora Awards →</a></p></div></body></html>"""

def _auth_form_html(token, email, kind, locked_username=None):
    """kind = 'verify' or 'reset'. For 'verify', shows username field (locked or free).
    For 'reset', just password field."""
    safe = html_mod.escape
    if kind == "verify":
        title = "Set up your account"
        sub = f"Welcome to Aurora Gracewood. Set a username and password — you'll use these to sign in."
        action = f"/api/verify/{safe(token)}"
        btn_label = "Set up my account →"
        if locked_username:
            username_field = (
                f'<div class="ag-field"><label>Username (locked for your role)</label>'
                f'<input type="text" value="{safe(locked_username)}" disabled style="opacity:0.55"></div>'
            )
        else:
            username_field = (
                '<div class="ag-field"><label>Choose a username</label>'
                '<input type="text" name="username" required minlength="3" maxlength="40" '
                'pattern="[a-zA-Z0-9_-]+" '
                'placeholder="3-40 chars, letters/numbers/_- only" autocomplete="username"></div>'
            )
    else:
        title = "Reset your password"
        sub = f"Choose a new password for {safe(email)}."
        action = f"/api/reset/{safe(token)}"
        btn_label = "Update password →"
        username_field = ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{title} · Aurora Gracewood</title>
<link rel="icon" type="image/png" href="/assets/logo.png">
<style>
body{{margin:0;background:linear-gradient(135deg,#1c1f2a,#0a0a0e);color:#f6f7fb;font-family:Inter,system-ui,sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}}
.card{{background:rgba(28,31,42,.96);border:1px solid rgba(255,255,255,.1);border-radius:18px;padding:32px;max-width:440px;width:100%;box-shadow:0 20px 60px rgba(0,0,0,.4)}}
h1{{color:#a3e3c1;margin:0 0 8px;font-size:1.4rem;letter-spacing:-.01em}}
.sub{{color:rgba(246,247,251,.7);margin:0 0 24px;font-size:.95rem;line-height:1.5}}
.ag-field{{display:flex;flex-direction:column;gap:6px;margin:0 0 16px}}
.ag-field label{{font-size:.82rem;color:rgba(246,247,251,.84);font-weight:700}}
.ag-field input{{background:rgba(0,0,0,.35);color:#f6f7fb;border:1px solid rgba(255,255,255,.12);border-radius:10px;padding:11px 14px;font:inherit;font-size:.95rem}}
.ag-field input:focus{{outline:2px solid #4a5fc1;outline-offset:1px}}
button{{width:100%;padding:13px;background:linear-gradient(135deg,#4a5fc1,#f4cfd9);color:#0a0a0e;border:0;border-radius:12px;font:inherit;font-weight:800;cursor:pointer;font-size:.98rem}}
button:hover{{filter:brightness(1.07)}}
button:disabled{{opacity:.5;cursor:not-allowed}}
.err{{color:#ff8fd8;font-size:.85rem;margin-top:8px;min-height:1em}}
.meta{{color:rgba(246,247,251,.5);font-size:.75rem;margin-top:16px;line-height:1.5}}
</style></head>
<body><div class="card">
<h1>{title}</h1><p class="sub">{sub}</p>
<form id="f" autocomplete="on">
  <div class="ag-field"><label>Email</label><input type="email" value="{safe(email)}" disabled style="opacity:0.55"></div>
  {username_field}
  <div class="ag-field"><label>Password</label>
    <input type="password" name="password" id="pw" required minlength="8" maxlength="200" autocomplete="new-password" placeholder="At least 8 characters"></div>
  <button id="btn" type="submit">{btn_label}</button>
  <div class="err" id="err"></div>
</form>
<div class="meta">By continuing you agree to Aurora Gracewood's terms.</div>
</div>
<script>
document.getElementById('f').addEventListener('submit', async (e) => {{
  e.preventDefault();
  const btn = document.getElementById('btn'); const err = document.getElementById('err');
  btn.disabled = true; const orig = btn.textContent; btn.textContent = 'Working…'; err.textContent = '';
  const body = {{ password: document.getElementById('pw').value }};
  const u = document.querySelector('input[name=username]');
  if (u) body.username = u.value;
  try {{
    const r = await fetch('{action}', {{
      method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify(body), credentials: 'include',
    }});
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || 'Failed');
    window.location = d.redirect || '/awards/';
  }} catch (e) {{
    err.textContent = e.message; btn.disabled = false; btn.textContent = orig;
  }}
}});
</script></body></html>"""


# ============== ROUTES ==============

# ---------- AUTH ROUTES ----------

@app.post("/api/signup")
async def api_signup(request: Request):
    """Email-only request that creates a pending user and emails a verification link.
    Re-running for an unverified email refreshes the token. For an already-verified
    email, returns success without leaking that fact (use forgot-password instead)."""
    data = await request.json()
    email = (data.get("email") or "").strip().lower()
    role = (data.get("role") or "client").strip()
    if not email or "@" not in email or "." not in email:
        raise HTTPException(400, "Valid email required")
    if role not in ("client", "admin", "superuser"):
        role = "client"

    now = int(time.time())
    token = generate_token()
    expires = now + 24 * 3600

    with db() as c:
        existing = c.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,)).fetchone()
        if existing and existing["password_hash"]:
            # Already verified — say nothing useful (don't leak account existence)
            return {"ok": True, "message": "If you have an account, check your email for next steps."}
        if existing:
            uid = existing["id"]
            c.execute("UPDATE users SET verify_token = ?, verify_expires = ? WHERE id = ?",
                      (token, expires, uid))
        else:
            uid = next_user_id(role)
            c.execute("""INSERT INTO users (id, email, role, status, created_at, verify_token, verify_expires, slug)
                         VALUES (?, ?, ?, 'pending', ?, ?, ?, ?)""",
                      (uid, email, role, now, token, expires, str(uid)))
        c.commit()

    verify_url = f"{PUBLIC_BASE_URL}/verify/{token}"
    html = (
        '<!DOCTYPE html><html><body style="font-family:Inter,Helvetica,sans-serif;color:#1c1f2a;background:#f6f7fb;line-height:1.6;margin:0;padding:32px 16px">'
        '<div style="max-width:560px;margin:0 auto;background:#fff;border-radius:14px;padding:32px;border:1px solid #e6e8ee">'
        '<h2 style="color:#4a5fc1;margin:0 0 8px;letter-spacing:-.01em">Welcome to Aurora Gracewood</h2>'
        '<p>Click the button below to set up your account. The link expires in 24 hours.</p>'
        f'<p style="margin:24px 0"><a href="{verify_url}" style="background:#4a5fc1;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:700;display:inline-block">Set up my account →</a></p>'
        f'<p style="font-size:13px;color:#7d8a99;word-break:break-all">Or paste this link: {verify_url}</p>'
        '<p style="font-size:12px;color:#7d8a99;margin-top:32px;border-top:1px solid #e6e8ee;padding-top:16px">If you didn\'t request this, ignore this email — no account will be created without you completing setup.</p>'
        '</div></body></html>'
    )
    sent, msg = send_email(email, "Set up your Aurora Gracewood account", html,
                           text=f"Welcome to Aurora Gracewood. Set up your account: {verify_url}\n\nThis link expires in 24 hours.")
    log_activity(None, "signup", f"email={email} role={role} sent={sent} msg={msg[:120]}")
    return {"ok": True, "message": "Check your email for a verification link."}

@app.get("/verify/{token}", response_class=HTMLResponse)
def verify_page(token: str):
    with db() as c:
        r = c.execute("SELECT id, email, username, username_locked, verify_expires FROM users WHERE verify_token = ?",
                      (token,)).fetchone()
    if not r:
        return HTMLResponse(_simple_page("Link not valid",
            "This link doesn't exist or has been used. If you've already set up your account, go sign in. Otherwise request a new link."), status_code=404)
    if r["verify_expires"] and int(time.time()) > r["verify_expires"]:
        return HTMLResponse(_simple_page("Link expired",
            "This setup link has expired. Sign up again to get a fresh one."), status_code=410)
    locked = bool(r["username_locked"])
    return HTMLResponse(_auth_form_html(token, r["email"], "verify",
                                        locked_username=r["username"] if locked else None))

@app.post("/api/verify/{token}")
async def api_verify(token: str, request: Request):
    data = await request.json()
    submitted_username = (data.get("username") or "").strip()
    password = (data.get("password") or "")
    if len(password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    with db() as c:
        r = c.execute("""SELECT id, email, username, role, username_locked, verify_expires
                         FROM users WHERE verify_token = ?""", (token,)).fetchone()
    if not r:
        raise HTTPException(404, "Token not found")
    if r["verify_expires"] and int(time.time()) > r["verify_expires"]:
        raise HTTPException(410, "Token expired")

    locked = bool(r["username_locked"])
    if locked:
        final_username = r["username"]
    else:
        if not submitted_username or len(submitted_username) < 3 or len(submitted_username) > 40:
            raise HTTPException(400, "Username must be 3-40 characters")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", submitted_username):
            raise HTTPException(400, "Username can only contain letters, numbers, underscores, and hyphens")
        with db() as c:
            existing = c.execute("SELECT id FROM users WHERE username = ? AND id != ?",
                                 (submitted_username, r["id"])).fetchone()
            if existing:
                raise HTTPException(409, "Username already taken")
        final_username = submitted_username

    pw_hash = hash_password(password)
    now = int(time.time())
    with db() as c:
        c.execute("""UPDATE users SET username = ?, password_hash = ?, status = 'active',
                     verify_token = NULL, verify_expires = NULL, verified_at = ?
                     WHERE id = ?""", (final_username, pw_hash, now, r["id"]))
        c.execute("""UPDATE users SET display_name = ?
                     WHERE id = ? AND (display_name IS NULL OR display_name = '')""",
                  (final_username, r["id"]))
        c.commit()

    if r["role"] == "client":
        try: grant_starter_badge(r["id"], reason="signup")
        except Exception: pass

    log_activity(r["id"], "verify_complete", f"username={final_username}")
    sid = create_session(r["id"], request)
    response = JSONResponse({"ok": True, "user_id": r["id"],
                             "redirect": _post_signin_redirect(r["role"])})
    return _attach_session(response, sid)

@app.post("/api/signin")
async def api_signin(request: Request):
    data = await request.json()
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "")
    if not email or not password:
        raise HTTPException(400, "Email and password required")
    with db() as c:
        r = c.execute("SELECT id, password_hash, status, role FROM users WHERE email = ?",
                      (email,)).fetchone()
    if not r or not r["password_hash"]:
        raise HTTPException(401, "Email or password incorrect")
    if r["status"] != "active":
        raise HTTPException(403, "Account not active. Verify your email or contact support.")
    if not verify_password(password, r["password_hash"]):
        log_activity(r["id"], "signin_failed")
        raise HTTPException(401, "Email or password incorrect")
    sid = create_session(r["id"], request)
    log_activity(r["id"], "signin")
    response = JSONResponse({"ok": True, "user_id": r["id"],
                             "redirect": _post_signin_redirect(r["role"])})
    return _attach_session(response, sid)

@app.post("/api/signout")
async def api_signout(request: Request):
    sid = request.cookies.get(SESSION_COOKIE)
    if sid:
        with db() as c:
            c.execute("DELETE FROM sessions WHERE id = ?", (sid,))
            c.commit()
    response = JSONResponse({"ok": True})
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response

@app.post("/api/forgot-password")
async def api_forgot_password(request: Request):
    """Always returns 'ok' regardless of whether the email exists — don't leak account
    existence to attackers. Only sends the email if a real active account is found."""
    data = await request.json()
    email = (data.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(400, "Email required")
    with db() as c:
        r = c.execute("SELECT id, status FROM users WHERE email = ?", (email,)).fetchone()
    if r and r["status"] == "active":
        token = generate_token()
        expires = int(time.time()) + 60 * 60  # 1 hour
        with db() as c:
            c.execute("UPDATE users SET password_reset_token = ?, password_reset_expires = ? WHERE id = ?",
                      (token, expires, r["id"]))
            c.commit()
        reset_url = f"{PUBLIC_BASE_URL}/reset/{token}"
        html = (
            '<!DOCTYPE html><html><body style="font-family:Inter,Helvetica,sans-serif;color:#1c1f2a;background:#f6f7fb;line-height:1.6;margin:0;padding:32px 16px">'
            '<div style="max-width:560px;margin:0 auto;background:#fff;border-radius:14px;padding:32px;border:1px solid #e6e8ee">'
            '<h2 style="color:#4a5fc1;margin:0 0 8px">Reset your password</h2>'
            '<p>Click the button below to choose a new password. The link expires in 1 hour.</p>'
            f'<p style="margin:24px 0"><a href="{reset_url}" style="background:#4a5fc1;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:700;display:inline-block">Reset my password →</a></p>'
            f'<p style="font-size:13px;color:#7d8a99;word-break:break-all">Or paste this link: {reset_url}</p>'
            '<p style="font-size:12px;color:#7d8a99;margin-top:32px;border-top:1px solid #e6e8ee;padding-top:16px">If you didn\'t request this, ignore this email — your password won\'t change.</p>'
            '</div></body></html>'
        )
        send_email(email, "Reset your Aurora Gracewood password", html,
                   text=f"Reset your password: {reset_url}\n\nThis link expires in 1 hour.")
        log_activity(r["id"], "forgot_password_sent")
    return {"ok": True, "message": "If an account exists for that email, we've sent a reset link."}

@app.get("/reset/{token}", response_class=HTMLResponse)
def reset_page(token: str):
    with db() as c:
        r = c.execute("SELECT id, email, password_reset_expires FROM users WHERE password_reset_token = ?",
                      (token,)).fetchone()
    if not r or (r["password_reset_expires"] and int(time.time()) > r["password_reset_expires"]):
        return HTMLResponse(_simple_page("Link not valid or expired",
            "Request a new password reset link from the sign-in page."), status_code=410)
    return HTMLResponse(_auth_form_html(token, r["email"], "reset"))

@app.post("/api/reset/{token}")
async def api_reset(token: str, request: Request):
    data = await request.json()
    password = (data.get("password") or "")
    if len(password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    with db() as c:
        r = c.execute("""SELECT id, role, password_reset_expires
                         FROM users WHERE password_reset_token = ?""", (token,)).fetchone()
    if not r:
        raise HTTPException(404, "Token not found")
    if r["password_reset_expires"] and int(time.time()) > r["password_reset_expires"]:
        raise HTTPException(410, "Token expired")
    with db() as c:
        c.execute("""UPDATE users SET password_hash = ?, password_reset_token = NULL,
                     password_reset_expires = NULL WHERE id = ?""", (hash_password(password), r["id"]))
        # Invalidate ALL existing sessions for this user — security best practice on reset
        c.execute("DELETE FROM sessions WHERE user_id = ?", (r["id"],))
        c.commit()
    log_activity(r["id"], "password_reset_complete")
    sid = create_session(r["id"], request)
    response = JSONResponse({"ok": True, "redirect": _post_signin_redirect(r["role"])})
    return _attach_session(response, sid)

@app.post("/api/forgot-username")
async def api_forgot_username(request: Request):
    data = await request.json()
    email = (data.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(400, "Email required")
    with db() as c:
        r = c.execute("SELECT id, username FROM users WHERE email = ? AND status = 'active'",
                      (email,)).fetchone()
    if r and r["username"]:
        html = (
            '<!DOCTYPE html><html><body style="font-family:Inter,Helvetica,sans-serif;color:#1c1f2a;background:#f6f7fb;line-height:1.6;margin:0;padding:32px 16px">'
            '<div style="max-width:560px;margin:0 auto;background:#fff;border-radius:14px;padding:32px;border:1px solid #e6e8ee">'
            '<h2 style="color:#4a5fc1;margin:0 0 8px">Your Aurora Gracewood username</h2>'
            f'<p>Your username is: <strong style="font-family:ui-monospace,monospace;font-size:1.05rem">{html_mod.escape(r["username"])}</strong></p>'
            f'<p style="margin-top:20px"><a href="{PUBLIC_BASE_URL}/" style="background:#4a5fc1;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:700;display:inline-block">Sign in →</a></p>'
            '</div></body></html>'
        )
        send_email(email, "Your Aurora Gracewood username", html,
                   text=f"Your username: {r['username']}")
        log_activity(r["id"], "forgot_username_sent")
    return {"ok": True, "message": "If an account exists for that email, we've sent your username."}

# ---------- END AUTH ROUTES ----------

@app.get("/")
def home():
    """Apex of aurora-gracewood.com: redirect to the awards landing.
    The old `site/index.html` signup-card splash is gone (was leaking sign-in UI onto a
    public page via GitHub Pages mirror at aurora-gracewood.com/site/). Auth flow is now
    initiated via /awards/ (or directly via the AGAuth modal on any page that has it)."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/awards/", status_code=302)

@app.get("/g-1vl00d/{page}", response_class=HTMLResponse)
def superuser_realm(page: str):
    f = REALMS_DIR / "g-1vl00d" / (page + ".html")
    if not f.exists(): raise HTTPException(404)
    return f.read_text(encoding="utf-8")

@app.get("/admin/{page}", response_class=HTMLResponse)
def admin_realm(page: str):
    f = REALMS_DIR / "admin" / (page + ".html")
    if not f.exists(): raise HTTPException(404)
    return f.read_text(encoding="utf-8")

@app.get("/client/{page}", response_class=HTMLResponse)
def client_realm(page: str):
    f = REALMS_DIR / "client" / (page + ".html")
    if not f.exists(): raise HTTPException(404)
    return f.read_text(encoding="utf-8")

@app.get("/account/realm.css")
def realm_css(): return Response((REALMS_DIR / "realm.css").read_text(encoding="utf-8"), media_type="text/css")

@app.get("/account/realm.js")
def realm_js(): return Response((REALMS_DIR / "realm.js").read_text(encoding="utf-8"), media_type="application/javascript")

# ============== PUBLIC PROFILE ==============

_NOCACHE = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}

@app.get("/u/{slug}", response_class=HTMLResponse)
def public_profile(slug: str):
    u = resolve_slug(slug)
    if not u or not u.get("public_profile") or u.get("profile_lock"):
        return HTMLResponse(render_404(), status_code=404, headers=_NOCACHE)
    with db() as c:
        roles = [dict(r) for r in c.execute(
            "SELECT role_name, year, emoji FROM user_roles WHERE user_id = ? ORDER BY year DESC, id ASC",
            (u["id"],)
        ).fetchall()]
    links = []
    if u.get("links_json"):
        try: links = json.loads(u["links_json"])
        except Exception: links = []
    theme = THEMES.get(u.get("theme") or DEFAULT_THEME, THEMES[DEFAULT_THEME])
    return HTMLResponse(render_profile(u, roles, links, theme), headers=_NOCACHE)

# ============== API ==============

@app.get("/api/me")
def api_me(request: Request):
    u = get_actor(request)
    if not u: raise HTTPException(401, "Pass ?as=<user_id> in dev mode")
    if u.get("links_json"):
        try: u["links"] = json.loads(u["links_json"])
        except Exception: u["links"] = []
    else:
        u["links"] = []
    with db() as c:
        roles = c.execute("SELECT id, role_name, year, emoji FROM user_roles WHERE user_id = ? ORDER BY year DESC, id ASC", (u["id"],)).fetchall()
        u["additional_roles"] = [dict(r) for r in roles]
        unread = c.execute("SELECT COUNT(*) FROM messages WHERE to_user = ? AND read_at IS NULL", (u["id"],)).fetchone()[0]
        u["unread_messages"] = unread
        badges = c.execute("""SELECT id, badge_slug, design_year, granted_at, hidden_on_profile, revoked_at
                              FROM issued_badges WHERE user_id = ? ORDER BY granted_at ASC""", (u["id"],)).fetchall()
        u["badges"] = [dict(r) for r in badges]
    return u

@app.get("/api/me/badges")
def get_my_badges(request: Request):
    u = get_actor(request)
    if not u: raise HTTPException(401)
    with db() as c:
        rows = c.execute("""SELECT id, badge_slug, design_year, granted_at, hidden_on_profile, revoked_at,
                                   awardee_text, destination_url
                            FROM issued_badges WHERE user_id = ? ORDER BY granted_at ASC""", (u["id"],)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        badge_def = BADGE_REGISTRY.get(d["badge_slug"]) or {}
        d["title"] = badge_def.get("title", d["badge_slug"])
        d["subtitle"] = badge_def.get("subtitle", "")
        # image_base_url points at the GitHub-Pages-served folder for this issuance.
        # Client appends `/{form_factor}.svg` to compose any specific form factor URL.
        # E.g., `${image_base_url}/circle-pin.svg`, `${image_base_url}/hero.svg`, etc.
        d["image_base_url"] = f"{SNIPPET_HOST}/badge/{d['badge_slug']}/{u['id']}"
        out.append(d)
    return out

@app.get("/api/me/badge-modal/{badge_slug}/{design_year}", response_class=HTMLResponse)
def get_my_badge_modal(badge_slug: str, design_year: int, request: Request):
    """Returns the embed-picker modal body HTML for a (badge × current user × year). Lazy-loaded
    by profile-edit.html when the user clicks a badge title — avoids shipping ~20KB of modal
    markup for every badge they own up-front. Only their own badges; no admin-of-other-user mode."""
    u = get_actor(request)
    if not u: raise HTTPException(401)
    with db() as c:
        owns = c.execute("SELECT 1 FROM issued_badges WHERE user_id = ? AND badge_slug = ? AND design_year = ?",
                         (u["id"], badge_slug, design_year)).fetchone()
    if not owns: raise HTTPException(404)
    recipient_ctx = {
        "id": u["id"],
        "slug": u.get("slug"),
        "username": u.get("username"),
        "display_name": u.get("display_name"),
    }
    # Reuse render_badge_modal_template, strip the wrapping <template> tags so the response is
    # ready to inject directly into a modal-content div.
    full = render_badge_modal_template(recipient_ctx, badge_slug, design_year)
    if full.startswith("<template") and full.endswith("</template>"):
        inner_start = full.index(">") + 1
        inner_end = full.rfind("</template>")
        full = full[inner_start:inner_end]
    return HTMLResponse(full, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.put("/api/me/badges/{badge_slug}/visibility")
async def set_my_badge_visibility(badge_slug: str, request: Request):
    u = get_actor(request)
    if not u: raise HTTPException(401)
    data = await request.json()
    hidden = 1 if data.get("hidden") else 0
    with db() as c:
        c.execute("UPDATE issued_badges SET hidden_on_profile = ? WHERE user_id = ? AND badge_slug = ?",
                  (hidden, u["id"], badge_slug))
        c.commit()
    log_activity(u["id"], "badge_visibility_set", f"{badge_slug}={'hidden' if hidden else 'visible'}")
    return {"ok": True}

@app.get("/api/users/{uid}/badges")
def admin_get_user_badges(uid: int, request: Request):
    actor = get_actor(request)
    if not actor or actor["role"] not in ("admin", "superuser"): raise HTTPException(403)
    with db() as c:
        rows = c.execute("""SELECT id, badge_slug, design_year, granted_at, hidden_on_profile, revoked_at
                            FROM issued_badges WHERE user_id = ? ORDER BY granted_at ASC""", (uid,)).fetchall()
        return [dict(r) for r in rows]

@app.put("/api/users/{uid}/badges/{badge_slug}/visibility")
async def admin_set_user_badge_visibility(uid: int, badge_slug: str, request: Request):
    actor = get_actor(request)
    if not actor or actor["role"] not in ("admin", "superuser"): raise HTTPException(403)
    data = await request.json()
    hidden = 1 if data.get("hidden") else 0
    with db() as c:
        c.execute("UPDATE issued_badges SET hidden_on_profile = ? WHERE user_id = ? AND badge_slug = ?",
                  (hidden, uid, badge_slug))
        c.execute("UPDATE users SET admin_changed_at = ? WHERE id = ?", (int(time.time()), uid))
        c.commit()
    log_activity(actor["id"], "admin_badge_visibility_set",
                 f"uid={uid} {badge_slug}={'hidden' if hidden else 'visible'}")
    return {"ok": True}

# Serve badge artwork assets (mark.svg etc.) so inline SVGs in profiles can reference them
BADDB_ASSETS_DIR = ROOT / "awards" / "badDB" / "assets"
BADDB_BADGES_DIR = ROOT / "awards" / "badDB" / "badges"

@app.get("/awards/asset/{filename}")
def serve_badge_asset(filename: str):
    safe = filename.replace("..", "").replace("/", "").replace("\\", "")
    f = BADDB_ASSETS_DIR / safe
    if not f.exists(): raise HTTPException(404)
    media = "image/svg+xml" if safe.endswith(".svg") else ("image/png" if safe.endswith(".png") else "application/octet-stream")
    return Response(f.read_bytes(), media_type=media, headers={"Cache-Control": "public, max-age=86400"})

@app.get("/awards/badge-asset/{badge_slug}/{filename}")
def serve_badge_specific_asset(badge_slug: str, filename: str):
    safe_b = badge_slug.replace("..", "").replace("/", "").replace("\\", "")
    safe_f = filename.replace("..", "").replace("/", "").replace("\\", "")
    f = BADDB_BADGES_DIR / safe_b / safe_f
    if not f.exists(): raise HTTPException(404)
    media = "image/svg+xml" if safe_f.endswith(".svg") else ("image/png" if safe_f.endswith(".png") else "application/octet-stream")
    return Response(f.read_bytes(), media_type=media, headers={"Cache-Control": "public, max-age=86400"})

# ============== AWARDS LANDING PAGE ==============
# Starter badges click through to /awards/?from={slug}. The landing page exists at
# awards/index.html ("Aurora Awards — Submissions"). These routes serve it and its sibling
# assets. Route ordering: more-specific paths above (/awards/asset/, /awards/badge-asset/)
# already resolve, so /awards/{filename} only catches single-segment requests like
# /awards/styles.css and won't shadow them.
AWARDS_DIR = ROOT / "awards"
ASSETS_DIR = ROOT / "assets"

_MEDIA_BY_EXT = {
    "css": "text/css", "js": "application/javascript", "html": "text/html",
    "png": "image/png", "svg": "image/svg+xml", "jpg": "image/jpeg",
    "jpeg": "image/jpeg", "webp": "image/webp", "ico": "image/x-icon",
    "json": "application/json", "txt": "text/plain",
}

def _media_for(name: str) -> str:
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return _MEDIA_BY_EXT.get(ext, "application/octet-stream")

@app.get("/awards", response_class=HTMLResponse)
@app.get("/awards/", response_class=HTMLResponse)
def awards_landing(request: Request):
    # ?from={slug} attribution param is read by app.js if/when analytics ships;
    # backend just serves the page either way.
    return HTMLResponse((AWARDS_DIR / "index.html").read_text(encoding="utf-8"))

@app.get("/awards/{filename}")
def serve_awards_sibling(filename: str):
    safe = filename.replace("..", "").replace("\\", "")
    f = AWARDS_DIR / safe
    if "/" in safe or not f.exists() or not f.is_file(): raise HTTPException(404)
    return Response(f.read_bytes(), media_type=_media_for(safe), headers={"Cache-Control": "public, max-age=3600"})

@app.get("/account/auth.css")
def auth_css():
    f = REALMS_DIR / "auth.css"
    if not f.exists(): raise HTTPException(404)
    return Response(f.read_text(encoding="utf-8"), media_type="text/css")

@app.get("/account/auth.js")
def auth_js():
    # auth.js is referenced by awards/index.html but not yet implemented locally.
    # Returning an empty stub keeps the page from 404-ing on the script tag and
    # allows the auth-chip slot to remain empty (app.js handles a missing chip gracefully).
    f = REALMS_DIR / "auth.js"
    if f.exists():
        return Response(f.read_text(encoding="utf-8"), media_type="application/javascript")
    return Response("/* auth.js: stub — auth chip not yet implemented */",
                    media_type="application/javascript")

@app.get("/assets/{filename}")
def serve_root_asset(filename: str):
    safe = filename.replace("..", "").replace("/", "").replace("\\", "")
    f = ASSETS_DIR / safe
    if not f.exists(): raise HTTPException(404)
    return Response(f.read_bytes(), media_type=_media_for(safe), headers={"Cache-Control": "public, max-age=86400"})

@app.get("/api/themes")
def list_themes(request: Request):
    """Return themes available to the actor based on their roles. Locked themes are filtered out."""
    actor = get_actor(request)
    allowed = set(themes_available_to(actor["id"]) if actor else themes_available_to(None))
    return [
        {"id": k, "name": v["name"], "swatch": [v["bg"], v["accent"], v["accent2"]]}
        for k, v in THEMES.items() if k in allowed
    ]

def _validate_links(value):
    if not isinstance(value, list):
        raise HTTPException(400, "links must be a list")
    if len(value) > LINKS_MAX:
        raise HTTPException(400, f"At most {LINKS_MAX} links")
    cleaned = []
    for entry in value:
        if not isinstance(entry, dict):
            raise HTTPException(400, "each link must be an object {url, label}")
        url = (entry.get("url") or "").strip()
        label = (entry.get("label") or "").strip()
        if not url:
            continue
        if not url.startswith(("http://", "https://")):
            raise HTTPException(400, "link urls must start with http:// or https://")
        if len(url) > 500: raise HTTPException(400, "link url too long")
        if len(label) > 80: raise HTTPException(400, "link label too long")
        cleaned.append({"url": url, "label": label})
    return cleaned

@app.put("/api/profile/me")
async def update_profile(request: Request):
    u = get_actor(request)
    if not u: raise HTTPException(401)
    data = await request.json()
    if "bio" in data and data["bio"] and len(data["bio"]) > BIO_MAX:
        raise HTTPException(400, f"Bio capped at {BIO_MAX} characters")
    if u["role"] == "client":
        for f in ("username", "slug"):
            data.pop(f, None)
    if u.get("profile_lock") and "public_profile" in data:
        del data["public_profile"]
    if "theme" in data:
        if data["theme"] not in THEMES:
            raise HTTPException(400, "Unknown theme")
        if data["theme"] not in themes_available_to(u["id"]):
            raise HTTPException(403, f"Theme '{data['theme']}' requires a role you don't have")
    if "slug" in data:
        if data["slug"] is None or (isinstance(data["slug"], str) and data["slug"].strip() == ""):
            data["slug"] = str(u["id"])  # cleared -> revert to numeric ID
        else:
            data["slug"] = validate_slug(data["slug"])
    if "links" in data:
        data["links_json"] = json.dumps(_validate_links(data["links"]))
        del data["links"]
    fields = {k: data[k] for k in ("display_name","username","bio","avatar_url","slug","public_profile","theme","links_json") if k in data}
    if not fields: return {"ok": True}
    sets = ", ".join(k + "=?" for k in fields)
    with db() as c:
        try:
            c.execute("UPDATE users SET " + sets + " WHERE id = ?", list(fields.values()) + [u["id"]])
            c.commit()
        except sqlite3.IntegrityError as e:
            raise HTTPException(409, f"Conflict: {str(e)}")
    log_activity(u["id"], "profile_updated", json.dumps(list(fields.keys())))
    return {"ok": True}

@app.get("/api/permissions")
def api_perms(request: Request):
    u = get_actor(request)
    if not u: raise HTTPException(401)
    return {"role": u["role"], "permissions": PERMISSIONS.get(u["role"], [])}

@app.get("/api/settings")
def get_settings(request: Request):
    u = get_actor(request)
    if not u: raise HTTPException(401)
    with db() as c:
        return {r["key"]: r["value"] for r in c.execute("SELECT key, value FROM settings WHERE scope='site'").fetchall()}

@app.put("/api/settings")
async def put_settings(request: Request):
    u = get_actor(request)
    if not u or u["role"] != "superuser": raise HTTPException(403)
    data = await request.json()
    now = int(time.time())
    with db() as c:
        for k, v in data.items():
            c.execute("INSERT INTO settings (scope, key, value, updated_at) VALUES ('site',?,?,?) ON CONFLICT(scope, key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (k, str(v), now))
        c.commit()
    log_activity(u["id"], "settings_updated", json.dumps(list(data.keys())))
    return {"ok": True}

@app.get("/api/notifications/preferences")
def get_notif_prefs(request: Request):
    u = get_actor(request)
    if not u: raise HTTPException(401)
    with db() as c:
        return [dict(r) for r in c.execute("SELECT channel, via_email, via_sms, via_inapp FROM notification_prefs WHERE user_id = ?", (u["id"],)).fetchall()]

@app.put("/api/notifications/preferences")
async def put_notif_prefs(request: Request):
    u = get_actor(request)
    if not u: raise HTTPException(401)
    data = await request.json()
    with db() as c:
        for p in data:
            c.execute("INSERT INTO notification_prefs (user_id, channel, via_email, via_sms, via_inapp) VALUES (?,?,?,?,?) ON CONFLICT(user_id, channel) DO UPDATE SET via_email=excluded.via_email, via_sms=excluded.via_sms, via_inapp=excluded.via_inapp",
                      (u["id"], p["channel"], int(p.get("via_email",0)), int(p.get("via_sms",0)), int(p.get("via_inapp",0))))
        c.commit()
    log_activity(u["id"], "notif_prefs_updated")
    return {"ok": True}

@app.get("/api/sessions")
def get_sessions(request: Request):
    u = get_actor(request)
    if not u: raise HTTPException(401)
    with db() as c:
        return [dict(r) for r in c.execute("SELECT id, user_agent, ip, created_at, last_seen_at FROM sessions WHERE user_id = ? ORDER BY last_seen_at DESC", (u["id"],)).fetchall()]

@app.delete("/api/sessions/{sid}")
def del_session(sid: str, request: Request):
    u = get_actor(request)
    if not u: raise HTTPException(401)
    with db() as c:
        c.execute("DELETE FROM sessions WHERE id = ? AND user_id = ?", (sid, u["id"]))
        c.commit()
    log_activity(u["id"], "session_revoked", sid)
    return {"ok": True}

@app.delete("/api/sessions")
def del_all_sessions(request: Request):
    u = get_actor(request)
    if not u: raise HTTPException(401)
    with db() as c:
        c.execute("DELETE FROM sessions WHERE user_id = ?", (u["id"],))
        c.commit()
    log_activity(u["id"], "all_sessions_revoked")
    return {"ok": True}

@app.get("/api/activity")
def get_activity(request: Request, limit: int = 50):
    u = get_actor(request)
    if not u: raise HTTPException(401)
    with db() as c:
        if u["role"] == "superuser":
            rows = c.execute("SELECT id, user_id, actor_role, action, detail, created_at FROM activity ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        else:
            rows = c.execute("SELECT id, user_id, actor_role, action, detail, created_at FROM activity WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (u["id"], limit)).fetchall()
        return [dict(r) for r in rows]

@app.get("/api/messages")
def get_messages(request: Request):
    u = get_actor(request)
    if not u: raise HTTPException(401)
    with db() as c:
        rows = c.execute("""SELECT m.id, m.from_user, m.to_user, m.subject, m.body, m.read_at, m.created_at,
                                   uf.display_name as from_name, uf.role as from_role,
                                   ut.display_name as to_name, ut.role as to_role
                            FROM messages m
                            LEFT JOIN users uf ON uf.id = m.from_user
                            LEFT JOIN users ut ON ut.id = m.to_user
                            WHERE m.from_user = ? OR m.to_user = ?
                            ORDER BY m.created_at DESC""", (u["id"], u["id"])).fetchall()
        return [dict(r) for r in rows]

@app.post("/api/messages")
async def send_message(request: Request):
    u = get_actor(request)
    if not u: raise HTTPException(401)
    data = await request.json()
    to_user = data.get("to_user")
    if not to_user or not data.get("body"): raise HTTPException(400, "to_user and body required")
    with db() as c:
        c.execute("INSERT INTO messages (from_user, to_user, subject, body, created_at) VALUES (?,?,?,?,?)",
                  (u["id"], int(to_user), data.get("subject",""), data["body"], int(time.time())))
        c.commit()
    log_activity(u["id"], "message_sent", "to_user="+str(to_user))
    return {"ok": True}

@app.put("/api/messages/{mid}/read")
def mark_read(mid: int, request: Request):
    u = get_actor(request)
    if not u: raise HTTPException(401)
    with db() as c:
        c.execute("UPDATE messages SET read_at = ? WHERE id = ? AND to_user = ?", (int(time.time()), mid, u["id"]))
        c.commit()
    return {"ok": True}

@app.get("/api/users")
def list_users(request: Request):
    u = get_actor(request)
    if not u: raise HTTPException(401)
    with db() as c:
        rows = c.execute("SELECT id, email, username, display_name, role, status, avatar_url, slug, public_profile, theme, created_at FROM users ORDER BY id ASC").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            roles = c.execute("SELECT role_name, year, emoji FROM user_roles WHERE user_id = ? ORDER BY year DESC", (d["id"],)).fetchall()
            d["additional_roles"] = [dict(x) for x in roles]
            out.append(d)
        return out

@app.put("/api/users/{uid}")
async def edit_user(uid: int, request: Request):
    actor = get_actor(request)
    if not actor or actor["role"] not in ("admin","superuser"): raise HTTPException(403)
    data = await request.json()
    if "bio" in data and data["bio"] and len(data["bio"]) > BIO_MAX:
        raise HTTPException(400, f"Bio capped at {BIO_MAX} characters")
    if "theme" in data:
        if data["theme"] not in THEMES:
            raise HTTPException(400, "Unknown theme")
        if data["theme"] not in themes_available_to(uid):
            raise HTTPException(403, f"Theme '{data['theme']}' requires a role the target user doesn't have")
    if "slug" in data:
        if data["slug"] is None or (isinstance(data["slug"], str) and data["slug"].strip() == ""):
            data["slug"] = str(uid)  # cleared -> revert to numeric ID
        else:
            data["slug"] = validate_slug(data["slug"])
    if "links" in data:
        data["links_json"] = json.dumps(_validate_links(data["links"]))
        del data["links"]
    allowed = {"display_name","role","status","bio","username","slug","avatar_url","public_profile","profile_lock","theme","links_json"}
    if actor["role"] != "superuser":
        allowed.discard("role")
    fields = {k: data[k] for k in data if k in allowed}
    if fields.get("profile_lock"):
        fields["public_profile"] = 0
    if not fields: return {"ok": True}
    if actor["id"] != uid:
        fields["admin_changed_at"] = int(time.time())
    sets = ", ".join(k + "=?" for k in fields)
    with db() as c:
        try:
            c.execute("UPDATE users SET " + sets + " WHERE id = ?", list(fields.values()) + [uid])
            c.commit()
        except sqlite3.IntegrityError as e:
            raise HTTPException(409, f"Conflict: {str(e)}")
    log_activity(actor["id"], "user_edited", "uid="+str(uid)+" fields="+json.dumps(list(fields.keys())))
    return {"ok": True}

@app.get("/api/users/{uid}/roles")
def get_user_roles(uid: int, request: Request):
    actor = get_actor(request)
    if not actor: raise HTTPException(401)
    with db() as c:
        rows = c.execute("SELECT id, role_name, year, emoji, granted_by, granted_at FROM user_roles WHERE user_id = ? ORDER BY year DESC, id ASC", (uid,)).fetchall()
        return [dict(r) for r in rows]

@app.post("/api/users/{uid}/roles")
async def add_user_role(uid: int, request: Request):
    actor = get_actor(request)
    if not actor or actor["role"] not in ("admin","superuser"): raise HTTPException(403)
    data = await request.json()
    role_name = data.get("role_name","").strip()
    year = data.get("year")
    if not role_name: raise HTTPException(400, "role_name required")
    emoji = ROLE_EMOJI.get(role_name, "")
    with db() as c:
        try:
            c.execute("INSERT INTO user_roles (user_id, role_name, year, emoji, granted_by, granted_at) VALUES (?,?,?,?,?,?)",
                      (uid, role_name, year, emoji, actor["id"], int(time.time())))
            c.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Role already assigned for that year")
    log_activity(actor["id"], "role_granted", f"uid={uid} role={role_name} year={year}")
    return {"ok": True}

@app.delete("/api/users/{uid}/roles/{rid}")
def remove_user_role(uid: int, rid: int, request: Request):
    actor = get_actor(request)
    if not actor or actor["role"] not in ("admin","superuser"): raise HTTPException(403)
    PROTECTED = ("Honoree", "Finalist", "Winner")
    with db() as c:
        r = c.execute("SELECT role_name FROM user_roles WHERE id = ? AND user_id = ?", (rid, uid)).fetchone()
        if not r: raise HTTPException(404, "Role not found")
        if r["role_name"] in PROTECTED and actor["role"] != "superuser":
            raise HTTPException(403, f"Only superuser can remove {r['role_name']} role")
        c.execute("DELETE FROM user_roles WHERE id = ? AND user_id = ?", (rid, uid))
        c.commit()
    log_activity(actor["id"], "role_revoked", f"uid={uid} rid={rid}")
    return {"ok": True}

@app.get("/api/role-catalog")
def role_catalog(request: Request):
    return [{"name": k, "emoji": v} for k, v in ROLE_EMOJI.items()]


# --- per-user data endpoints (for admin/superuser viewing a target user) ---

@app.get("/api/users/{uid}/activity")
def user_activity(uid: int, request: Request, limit: int = 50):
    actor = get_actor(request)
    if not actor or actor["role"] not in ("admin", "superuser"): raise HTTPException(403)
    with db() as c:
        rows = c.execute("SELECT id, user_id, actor_role, action, detail, created_at FROM activity WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (uid, limit)).fetchall()
        return [dict(r) for r in rows]

@app.get("/api/users/{uid}/messages")
def user_messages(uid: int, request: Request):
    actor = get_actor(request)
    if not actor or actor["role"] not in ("admin", "superuser"): raise HTTPException(403)
    with db() as c:
        rows = c.execute("""SELECT m.id, m.from_user, m.to_user, m.subject, m.body, m.read_at, m.created_at,
                                   uf.display_name as from_name, uf.role as from_role,
                                   ut.display_name as to_name, ut.role as to_role
                            FROM messages m
                            LEFT JOIN users uf ON uf.id = m.from_user
                            LEFT JOIN users ut ON ut.id = m.to_user
                            WHERE m.from_user = ? OR m.to_user = ?
                            ORDER BY m.created_at DESC""", (uid, uid)).fetchall()
        return [dict(r) for r in rows]

@app.get("/api/users/{uid}/sessions")
def user_sessions_endpoint(uid: int, request: Request):
    actor = get_actor(request)
    if not actor or actor["role"] != "superuser": raise HTTPException(403, "Superuser only")
    with db() as c:
        rows = c.execute("SELECT id, user_agent, ip, created_at, last_seen_at FROM sessions WHERE user_id = ?", (uid,)).fetchall()
        return [dict(r) for r in rows]


# ============== PUBLIC PROFILE RENDERING ==============

# =====================================================================
# BADGE RENDERING — dynamic, per badge × per form factor × per recipient
# =====================================================================

# Badge registry: static data per badge. Add new badges by adding entries here.
BADGE_REGISTRY = {
    "starter": {
        "title": "Starter",
        "subtitle": "Journey Begins Badge",
        "category_label": "INFLUENCE",
        # Local FILE PATHS (not URLs) — each render embeds these as base64 data: URIs so the
        # generated SVG is fully self-contained. Required because SVG delivered via <img> can't
        # load <image href> URL references (browser security sandbox); the static-file embeds
        # in the wild MUST be self-contained or the artwork breaks.
        "background_path": ROOT / "awards" / "badDB" / "badges" / "starter" / "starter.png",
        "mark_path": ROOT / "awards" / "badDB" / "assets" / "mark.svg",
        # default_destination is the URL template baked into every Starter issuance at grant time.
        # {slug} resolves to the recipient's slug at grant; result is frozen forever in
        # issued_badges.destination_url. Per-issuance overrides are allowed (admin can pass a
        # different destination at grant) but the default is the awards funnel.
        "default_destination": "/awards/?from={slug}",
    },
    # Future badges: just add to this dict (and assets to deploy.py). Override default_destination
    # per badge type (e.g. some badges might point to /u/{slug}, a work page, an external URL, etc.).
}

_DATA_URI_CACHE = {}
def _encode_as_data_uri(path):
    """Read a local file and return a `data:<mime>;base64,...` URI. Cached per path to avoid
    re-reading + re-encoding starter.png on every badge render. Returns empty string if path
    is missing or unreadable so the caller falls through gracefully."""
    if not path:
        return ""
    key = str(path)
    if key in _DATA_URI_CACHE:
        return _DATA_URI_CACHE[key]
    p = Path(path)
    if not p.exists() or not p.is_file():
        _DATA_URI_CACHE[key] = ""
        return ""
    ext = p.suffix.lower()
    mime = {
        ".png": "image/png", ".svg": "image/svg+xml", ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg", ".webp": "image/webp",
    }.get(ext, "application/octet-stream")
    encoded = base64.b64encode(p.read_bytes()).decode("ascii")
    uri = f"data:{mime};base64,{encoded}"
    _DATA_URI_CACHE[key] = uri
    return uri

# Layout coordinates per form factor. Coords transcribed from starter_template.html so production
# matches the design sandbox. Layout-as-data: add a new form factor by adding an entry here.
# Field guide:
#   awardee/subtitle "lines": 1 = single line, 2 = split (first word vs rest, with line2_dy spacing)
#   subtitle "split_first": override default split point (e.g. "Journey Begins" splits "Journey Begins Badge")
#   "category": optional element for vertical-card (renders BADGE_REGISTRY[badge]["category_label"])
#   "use_circle_clip": True clips artwork to a circle and uses a circle frame instead of rect
#   "friendly_name" + "use_case": copy shown to recipients in the embed-picker modal (not on artwork)
FORM_FACTOR_LAYOUTS = {
    "hero": {
        "w": 200, "h": 200, "use_circle_clip": False, "frame_stroke_width": 3, "frame_inset": 6,
        "friendly_name": "Hero", "use_case": "Footer, statement piece, 'as-seen-in' anchor.",
        "awardee":  {"x": 100, "y": 46, "size": 7, "anchor": "middle", "letter_spacing": 1.5, "lines": 1},
        "year_l":   {"x": 46,  "y": 106, "size": 20, "letter_spacing": -0.5},
        "year_r":   {"x": 154, "y": 106, "size": 20, "letter_spacing": -0.5},
        "mark":     {"x": 60,  "y": 60,  "w": 80, "h": 80},
        "title":    {"x": 100, "y": 166, "size": 22, "anchor": "middle", "letter_spacing": 0.5},
        "subtitle": {"x": 100, "y": 183, "size": 11, "anchor": "middle", "lines": 1},
    },
    "compact": {
        "w": 120, "h": 120, "use_circle_clip": False, "frame_stroke_width": 2, "frame_inset": 4,
        "friendly_name": "Compact", "use_case": "Sidebar, blog about-author, multi-badge row.",
        "awardee":  {"x": 60, "y": 32, "size": 5, "anchor": "middle", "letter_spacing": 1.2, "lines": 1},
        "year_l":   {"x": 28, "y": 64, "size": 11, "letter_spacing": 0},
        "year_r":   {"x": 92, "y": 64, "size": 11, "letter_spacing": 0},
        "mark":     {"x": 40, "y": 40, "w": 40, "h": 40},
        "title":    {"x": 60, "y": 96, "size": 14, "anchor": "middle", "letter_spacing": 0.4},
        "subtitle": {"x": 60, "y": 108, "size": 7, "anchor": "middle", "lines": 1},
    },
    "inline": {
        "w": 240, "h": 60, "use_circle_clip": False, "frame_stroke_width": 2, "frame_inset": 3,
        "friendly_name": "Inline", "use_case": "Slim mid-content strip in articles.",
        "awardee":  {"x": 28, "y": 26, "size": 6, "anchor": "start", "letter_spacing": 1.2, "lines": 2, "line2_dy": 12},
        "year_l":   {"x": 92,  "y": 36, "size": 11, "letter_spacing": 0},
        "year_r":   {"x": 148, "y": 36, "size": 11, "letter_spacing": 0},
        "mark":     {"x": 104, "y": 14, "w": 32, "h": 32},
        "title":    {"x": 166, "y": 24, "size": 14, "anchor": "start", "letter_spacing": 0.4},
        "subtitle": {"x": 166, "y": 40, "size": 8, "anchor": "start", "lines": 2, "line2_dy": 12, "split_first": "Journey Begins"},
    },
    "banner": {
        "w": 480, "h": 96, "use_circle_clip": False, "frame_stroke_width": 3, "frame_inset": 4,
        "friendly_name": "Banner", "use_case": "Twitter/X header, blog top banner.",
        "awardee":  {"x": 100, "y": 42, "size": 9, "anchor": "middle", "letter_spacing": 1.6, "lines": 2, "line2_dy": 14},
        "year_l":   {"x": 180, "y": 56, "size": 20, "letter_spacing": -0.5},
        "year_r":   {"x": 276, "y": 56, "size": 20, "letter_spacing": -0.5},
        "mark":     {"x": 196, "y": 16, "w": 64, "h": 64},
        "title":    {"x": 332, "y": 50, "size": 28, "anchor": "start", "letter_spacing": 0.5},
        "subtitle": {"x": 332, "y": 72, "size": 13, "anchor": "start", "lines": 1},
    },
    "vertical-card": {
        "w": 240, "h": 360, "use_circle_clip": False, "frame_stroke_width": 3, "frame_inset": 6,
        "friendly_name": "Vertical Card", "use_case": "Side panel, awards wall, portrait spotlight.",
        "awardee":  {"x": 120, "y": 112, "size": 9, "anchor": "middle", "letter_spacing": 1.8, "lines": 1},
        "year_l":   {"x": 56,  "y": 186, "size": 26, "letter_spacing": -0.5},
        "year_r":   {"x": 184, "y": 186, "size": 26, "letter_spacing": -0.5},
        "mark":     {"x": 70,  "y": 130, "w": 100, "h": 100},
        "title":    {"x": 120, "y": 262, "size": 32, "anchor": "middle", "letter_spacing": 0.6},
        "subtitle": {"x": 120, "y": 284, "size": 14, "anchor": "middle", "lines": 1},
        "category": {"x": 120, "y": 306, "size": 8, "anchor": "middle", "letter_spacing": 2},
    },
    "square-sticker": {
        "w": 300, "h": 300, "use_circle_clip": False, "frame_stroke_width": 3, "frame_inset": 6,
        "friendly_name": "Square Sticker", "use_case": "Instagram, printable stickers.",
        "awardee":  {"x": 150, "y": 84, "size": 10, "anchor": "middle", "letter_spacing": 2, "lines": 1},
        "year_l":   {"x": 68,  "y": 158, "size": 28, "letter_spacing": -0.6},
        "year_r":   {"x": 232, "y": 158, "size": 28, "letter_spacing": -0.6},
        "mark":     {"x": 90,  "y": 100, "w": 120, "h": 120},
        "title":    {"x": 150, "y": 248, "size": 34, "anchor": "middle", "letter_spacing": 0.6},
        "subtitle": {"x": 150, "y": 272, "size": 15, "anchor": "middle", "lines": 1},
    },
    "circle-pin": {
        "w": 120, "h": 120, "use_circle_clip": True, "frame_stroke_width": 2, "frame_inset": 3,
        "friendly_name": "Circle Pin", "use_case": "Profile-photo overlay, small corner mark.",
        "awardee":  {"x": 60, "y": 32, "size": 5, "anchor": "middle", "letter_spacing": 1.2, "lines": 1},
        "year_l":   {"x": 28, "y": 62, "size": 9, "letter_spacing": 0},
        "year_r":   {"x": 92, "y": 62, "size": 9, "letter_spacing": 0},
        "mark":     {"x": 42, "y": 38, "w": 36, "h": 36},
        "title":    {"x": 60, "y": 88, "size": 13, "anchor": "middle", "letter_spacing": 0.5},
        "subtitle": {"x": 60, "y": 100, "size": 7, "anchor": "middle", "lines": 1},
    },
    "mini-chip": {
        "w": 200, "h": 32, "use_circle_clip": False, "frame_stroke_width": 2, "frame_inset": 2,
        "friendly_name": "Mini Chip", "use_case": "Footer line, inline mention.",
        "awardee":  {"x": 16, "y": 14, "size": 5, "anchor": "start", "letter_spacing": 1, "lines": 2, "line2_dy": 10},
        "year_l":   {"x": 84,  "y": 22, "size": 8, "letter_spacing": 0},
        "year_r":   {"x": 124, "y": 22, "size": 8, "letter_spacing": 0},
        "mark":     {"x": 92, "y": 4, "w": 24, "h": 24},
        "title":    {"x": 138, "y": 20, "size": 11, "anchor": "start", "letter_spacing": 0.3},
        "subtitle": {"x": 138, "y": 28, "size": 6, "anchor": "start", "lines": 1},
    },
    "email-strip": {
        "w": 400, "h": 64, "use_circle_clip": False, "frame_stroke_width": 3, "frame_inset": 3,
        "friendly_name": "Email Strip", "use_case": "Email signatures (use the PNG variant).",
        "awardee":  {"x": 44, "y": 28, "size": 8, "anchor": "start", "letter_spacing": 1.5, "lines": 2, "line2_dy": 14},
        "year_l":   {"x": 158, "y": 38, "size": 14, "letter_spacing": 0},
        "year_r":   {"x": 242, "y": 38, "size": 14, "letter_spacing": 0},
        "mark":     {"x": 176, "y": 8, "w": 48, "h": 48},
        "title":    {"x": 266, "y": 36, "size": 20, "anchor": "start", "letter_spacing": 0.5},
        "subtitle": {"x": 266, "y": 52, "size": 11, "anchor": "start", "lines": 1},
    },
}

# Form factors in user-presentation order in the embed-picker modal (large/featured first, small last).
FORM_FACTOR_ORDER = ["hero", "vertical-card", "square-sticker", "banner", "compact",
                     "circle-pin", "inline", "email-strip", "mini-chip"]

def render_badge(badge_slug, form_factor, recipient, design_year, wrap_link=True):
    """Render a badge as inline SVG, dynamically per badge × form factor × recipient.
    When wrap_link=True (default), wraps the SVG in <a href="/awards/?from={slug}"> for the
    funnel click-through. wrap_link=False returns just the SVG — used by the embed-picker
    modal where badges are previews, not navigation."""
    safe = html_mod.escape
    badge = BADGE_REGISTRY.get(badge_slug)
    if not badge:
        return f'<div class="ag-badge-item ag-badge-unknown">[{safe(badge_slug)}]</div>'
    layout = FORM_FACTOR_LAYOUTS.get(form_factor) or FORM_FACTOR_LAYOUTS["compact"]

    awardee = (recipient.get("display_name") or recipient.get("username") or "").upper()
    yl = str(design_year)[:2]
    yr = str(design_year)[2:]
    slug = recipient.get("slug") or str(recipient["id"])
    uid = f"{badge_slug}-{form_factor}-{design_year}-{recipient['id']}"

    w, h = layout["w"], layout["h"]
    aw, yl_p, yr_p = layout["awardee"], layout["year_l"], layout["year_r"]
    mk, ti, st = layout["mark"], layout["title"], layout["subtitle"]
    cx, cy, r = w // 2, h // 2, (w // 2) - 3
    fsw = layout["frame_stroke_width"]

    defs = f'''<defs>
<linearGradient id="brd-{uid}" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0%" stop-color="#45d9ff"/><stop offset="33%" stop-color="#ff8fd8"/>
  <stop offset="66%" stop-color="#4a5fc1"/><stop offset="100%" stop-color="#738c5e"/>
</linearGradient>
<linearGradient id="cop-{uid}" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0%" stop-color="#e09668"/><stop offset="50%" stop-color="#c47a4a"/>
  <stop offset="100%" stop-color="#6f4326"/>
</linearGradient>
<mask id="msk-{uid}" mask-type="alpha"><image href="{_encode_as_data_uri(badge.get('mark_path'))}" x="{mk["x"]}" y="{mk["y"]}" width="{mk["w"]}" height="{mk["h"]}"/></mask>
<filter id="ts-{uid}"><feDropShadow dx="0" dy="0" stdDeviation="1" flood-color="#1c1f2a" flood-opacity="1"/></filter>
<filter id="ds-{uid}" x="-50%" y="-50%" width="200%" height="200%">
  <feDropShadow dx="0" dy="2" stdDeviation="1" flood-color="#000000" flood-opacity="1"/>
  <feDropShadow dx="0" dy="3" stdDeviation="3" flood-color="#000000" flood-opacity="0.85"/>
  <feDropShadow dx="0" dy="0" stdDeviation="6" flood-color="#000000" flood-opacity="0.5"/>
</filter>
<filter id="tit-{uid}" x="-100%" y="-100%" width="300%" height="300%">
  <feDropShadow dx="0" dy="0" stdDeviation="2" flood-color="#f6f7fb" flood-opacity="1"/>
  <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="#f6f7fb" flood-opacity="1"/>
</filter>
<radialGradient id="gl1-{uid}" cx="0.5" cy="0.5" r="0.65" gradientUnits="objectBoundingBox">
  <stop offset="0" stop-color="#ffffff" stop-opacity="0.18"/>
  <stop offset="0.35" stop-color="#ffffff" stop-opacity="0.13"/>
  <stop offset="0.7" stop-color="#ffffff" stop-opacity="0.04"/>
  <stop offset="1" stop-color="#ffffff" stop-opacity="0"/>
  <animate attributeName="cx" attributeType="XML" values="0.8;0.71;0.5;0.29;0.2;0.29;0.5;0.71;0.8" keyTimes="0;0.125;0.25;0.375;0.5;0.625;0.75;0.875;1" dur="22s" repeatCount="indefinite"/>
  <animate attributeName="cy" attributeType="XML" values="0.5;0.64;0.7;0.64;0.5;0.36;0.3;0.36;0.5" keyTimes="0;0.125;0.25;0.375;0.5;0.625;0.75;0.875;1" dur="22s" repeatCount="indefinite"/>
</radialGradient>
<radialGradient id="gl2-{uid}" cx="0.5" cy="0.5" r="0.65" gradientUnits="objectBoundingBox">
  <stop offset="0" stop-color="#ffffff" stop-opacity="0.18"/>
  <stop offset="0.35" stop-color="#ffffff" stop-opacity="0.13"/>
  <stop offset="0.7" stop-color="#ffffff" stop-opacity="0.04"/>
  <stop offset="1" stop-color="#ffffff" stop-opacity="0"/>
  <animate attributeName="cx" attributeType="XML" values="0.2;0.29;0.5;0.71;0.8;0.71;0.5;0.29;0.2" keyTimes="0;0.125;0.25;0.375;0.5;0.625;0.75;0.875;1" dur="22s" repeatCount="indefinite"/>
  <animate attributeName="cy" attributeType="XML" values="0.5;0.64;0.7;0.64;0.5;0.36;0.3;0.36;0.5" keyTimes="0;0.125;0.25;0.375;0.5;0.625;0.75;0.875;1" dur="22s" repeatCount="indefinite"/>
</radialGradient>'''
    if layout["use_circle_clip"]:
        defs += f'<clipPath id="clip-{uid}"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>'
    defs += '</defs>'

    bg_data_uri = _encode_as_data_uri(badge.get("background_path"))
    bg = (f'<image href="{bg_data_uri}" x="0" y="0" width="{w}" height="{h}" preserveAspectRatio="xMidYMid slice"/>'
          if bg_data_uri else
          f'<rect width="{w}" height="{h}" fill="#f6f7fb"/>')

    # Awardee text — 1 or 2 lines depending on form factor (compact form factors use single line;
    # horizontal-strip form factors split first word vs rest onto two lines).
    aw_lines = aw.get("lines", 1)
    if aw_lines == 2:
        words = (awardee or "").split()
        line1 = words[0] if words else ""
        line2 = " ".join(words[1:]) if len(words) > 1 else ""
        line2_dy = aw.get("line2_dy", 12)
        text_awardee = (
            f'<text x="{aw["x"]}" y="{aw["y"]}" text-anchor="{aw["anchor"]}" font-family="\'FF Meta\',\'Meta Pro\',\'Inter\',sans-serif" font-size="{aw["size"]}" font-weight="800" letter-spacing="{aw["letter_spacing"]}" fill="#f6f7fb" filter="url(#ts-{uid})">{safe(line1)}</text>'
            + (f'<text x="{aw["x"]}" y="{aw["y"]+line2_dy}" text-anchor="{aw["anchor"]}" font-family="\'FF Meta\',\'Meta Pro\',\'Inter\',sans-serif" font-size="{aw["size"]}" font-weight="800" letter-spacing="{aw["letter_spacing"]}" fill="#f6f7fb" filter="url(#ts-{uid})">{safe(line2)}</text>' if line2 else "")
        )
    else:
        text_awardee = f'<text x="{aw["x"]}" y="{aw["y"]}" text-anchor="{aw["anchor"]}" font-family="\'FF Meta\',\'Meta Pro\',\'Inter\',sans-serif" font-size="{aw["size"]}" font-weight="800" letter-spacing="{aw["letter_spacing"]}" fill="#f6f7fb" filter="url(#ts-{uid})">{safe(awardee)}</text>'

    text_yl = f'<text x="{yl_p["x"]}" y="{yl_p["y"]}" text-anchor="middle" font-family="\'FF Meta\',\'Meta Pro\',\'Inter\',sans-serif" font-size="{yl_p["size"]}" font-weight="900" letter-spacing="{yl_p.get("letter_spacing", 0)}" fill="#c47a4a" filter="url(#ds-{uid})">{yl}</text>'
    text_yr = f'<text x="{yr_p["x"]}" y="{yr_p["y"]}" text-anchor="middle" font-family="\'FF Meta\',\'Meta Pro\',\'Inter\',sans-serif" font-size="{yr_p["size"]}" font-weight="900" letter-spacing="{yr_p.get("letter_spacing", 0)}" fill="#c47a4a" filter="url(#ds-{uid})">{yr}</text>'
    g_mark = f'<g mask="url(#msk-{uid})" filter="url(#ds-{uid})"><rect x="{mk["x"]}" y="{mk["y"]}" width="{mk["w"]}" height="{mk["h"]}" fill="url(#cop-{uid})"/></g>'
    text_title = f'<text x="{ti["x"]}" y="{ti["y"]}" text-anchor="{ti["anchor"]}" font-family="\'FF Meta\',\'Meta Pro\',\'Inter\',sans-serif" font-size="{ti["size"]}" font-weight="900" fill="#4a5fc1" letter-spacing="{ti["letter_spacing"]}" filter="url(#tit-{uid})">{safe(badge["title"])}</text>'

    # Subtitle — 1 or 2 lines. Two-line mode uses split_first to override the natural break point.
    st_lines = st.get("lines", 1)
    if st_lines == 2:
        full = badge.get("subtitle") or ""
        split_first = st.get("split_first")
        if split_first and full.startswith(split_first):
            line1 = split_first
            line2 = full[len(split_first):].strip()
        else:
            words = full.split()
            mid = max(1, len(words) // 2)
            line1 = " ".join(words[:mid])
            line2 = " ".join(words[mid:])
        line2_dy = st.get("line2_dy", 12)
        text_subtitle = (
            f'<text x="{st["x"]}" y="{st["y"]}" text-anchor="{st["anchor"]}" font-family="\'FF Meta\',\'Meta Pro\',\'Inter\',sans-serif" font-size="{st["size"]}" font-weight="500" font-style="italic" fill="#f6f7fb" filter="url(#ts-{uid})">{safe(line1)}</text>'
            + (f'<text x="{st["x"]}" y="{st["y"]+line2_dy}" text-anchor="{st["anchor"]}" font-family="\'FF Meta\',\'Meta Pro\',\'Inter\',sans-serif" font-size="{st["size"]}" font-weight="500" font-style="italic" fill="#f6f7fb" filter="url(#ts-{uid})">{safe(line2)}</text>' if line2 else "")
        )
    else:
        text_subtitle = f'<text x="{st["x"]}" y="{st["y"]}" text-anchor="{st["anchor"]}" font-family="\'FF Meta\',\'Meta Pro\',\'Inter\',sans-serif" font-size="{st["size"]}" font-weight="500" font-style="italic" fill="#f6f7fb" filter="url(#ts-{uid})">{safe(badge["subtitle"])}</text>'

    # Optional category label (vertical-card uses this — renders BADGE_REGISTRY[badge]["category_label"]).
    text_category = ""
    if layout.get("category") and badge.get("category_label"):
        cat = layout["category"]
        text_category = f'<text x="{cat["x"]}" y="{cat["y"]}" text-anchor="{cat["anchor"]}" font-family="\'FF Meta\',\'Meta Pro\',\'Inter\',sans-serif" font-size="{cat["size"]}" font-weight="800" letter-spacing="{cat["letter_spacing"]}" fill="#f6f7fb" filter="url(#ts-{uid})">{safe(badge["category_label"])}</text>'

    gleam = f'<rect width="{w}" height="{h}" fill="url(#gl1-{uid})" pointer-events="none"/><rect width="{w}" height="{h}" fill="url(#gl2-{uid})" pointer-events="none"/>'

    inner = bg + text_awardee + text_yl + g_mark + text_yr + text_title + text_subtitle + text_category + gleam

    fi = layout.get("frame_inset", 3)
    if layout["use_circle_clip"]:
        body = f'<g clip-path="url(#clip-{uid})">{inner}</g><circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#brd-{uid})" stroke-width="{fsw}"/>'
    else:
        body = inner + f'<rect x="{fi}" y="{fi}" width="{w-2*fi}" height="{h-2*fi}" fill="none" stroke="url(#brd-{uid})" stroke-width="{fsw}"/>'

    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">{defs}{body}</svg>'
    if not wrap_link:
        return svg
    # Click target = the Aurora Awards landing page. Strategic funnel decision: when a
    # recipient embeds their badge on their own site, any reader who clicks lands on the
    # awards platform itself, not the recipient's profile. Badges become a discovery surface
    # for the awards. The {slug} flows through as ?from= so attribution is recoverable later.
    href = f"/awards/?from={safe(slug)}"
    title = f'{safe(badge["title"])} · {safe(awardee)} · {design_year} — about Aurora Awards'
    return f'<a class="ag-badge-link" href="{href}" title="{title}">{svg}</a>'


# Snippet host: the static-site domain serving pre-rendered badge files. Each issuance commits
# its 9 form-factor SVGs into auroragracewood/badges via GitHub API at grant time, and GitHub
# Pages serves them under this domain. Embeds anywhere on the web hit this CDN-fronted host
# directly — Python is OUT of the embed-view loop forever after issuance.
SNIPPET_HOST = "https://badges.aurora-gracewood.com"

def render_badge_modal_template(recipient, badge_slug, design_year):
    """Render a hidden <template> containing the embed-picker modal body for one badge.
    The modal body has: header copy + 9 form-factor cards, each with a rendered preview
    and 3 expandable snippet variants (SVG/PNG/iframe) with copy-to-clipboard buttons.
    JS clones this template into the shared modal container when the user clicks the
    badge title button on the profile."""
    safe = html_mod.escape
    badge = BADGE_REGISTRY.get(badge_slug)
    if not badge:
        return ""
    slug = recipient.get("slug") or str(recipient["id"])
    awardee = (recipient.get("display_name") or recipient.get("username") or "").upper()
    template_id = f"badge-modal-{badge_slug}-{design_year}"

    user_id = recipient["id"]
    sections = []
    for ff in FORM_FACTOR_ORDER:
        layout = FORM_FACTOR_LAYOUTS.get(ff)
        if not layout:
            continue
        w, h = layout["w"], layout["h"]
        ff_friendly = layout.get("friendly_name", ff)
        ff_use_case = layout.get("use_case", "")

        # Static SVG URL — what the recipient embeds, what GitHub Pages serves, what
        # this preview <img> loads. Same URL the modal preview uses + the snippet shows.
        svg_url = f"{SNIPPET_HOST}/badge/{badge_slug}/{user_id}/{ff}.svg"
        alt = f"Aurora Gracewood {badge['title']} {design_year} — {awardee}"

        preview_html = f'<img src="{safe(svg_url)}" alt="{safe(alt)}" width="{w}" height="{h}" loading="lazy" style="display:block">'

        # Tier B (Starter): SVG-only snippet. PNG deferred until libcairo install is sorted on
        # me-think; iframe is Tier A only (winners/finalists with HMAC-bound tamper resistance).
        snippet_svg = (f'<img src="{svg_url}"\n'
                       f'  alt="{alt}"\n'
                       f'  width="{w}" height="{h}">')

        block_svg = (
            f'<div class="ag-snip-block">'
            f'<div class="ag-snip-head">'
            f'<div class="ag-snip-label"><strong>For most websites</strong> <span class="ag-snip-sub">SVG · recommended</span></div>'
            f'<button type="button" class="ag-copy-btn" data-copy-target="next">Copy</button>'
            f'</div>'
            f'<pre class="ag-snip-code"><code>{safe(snippet_svg)}</code></pre>'
            f'<p class="ag-snip-hint">Crisp at any size. Use this almost everywhere — blogs, portfolios, websites.</p>'
            f'</div>'
        )
        # Email-strip: add a note that an email-friendly PNG variant is coming.
        if ff == "email-strip":
            block_svg += (
                '<p class="ag-snip-hint" style="margin-top:8px">'
                '<strong>Heads up:</strong> a PNG variant for email signatures is coming. '
                'For now, paste the SVG — Gmail and Outlook may not render it; web mail clients like ProtonMail and FastMail will.'
                '</p>'
            )
        blocks_html = block_svg

        sections.append(
            f'<section class="ag-modal-ff" data-ff="{ff}">'
            f'<div class="ag-modal-ff-preview">{preview_html}</div>'
            f'<div class="ag-modal-ff-info">'
            f'<h3>{safe(ff_friendly)} <span class="ag-modal-ff-dim">{w}×{h}</span></h3>'
            f'<p class="ag-modal-ff-use">{safe(ff_use_case)}</p>'
            f'<details class="ag-modal-ff-snippets"><summary>Get the code</summary>{blocks_html}</details>'
            f'</div>'
            f'</section>'
        )

    header = (
        f'<header class="ag-modal-header">'
        f'<h2>Your <span class="ag-modal-title-em">{safe(badge["title"])}</span> Badge</h2>'
        f'<p>You earned this when you joined Aurora Gracewood. Show it off — pick a size below, copy the snippet, paste it into your site, blog, or email signature. Each size is the same badge in a different shape — pick whichever fits where you want it.</p>'
        f'</header>'
    )
    body = '<div class="ag-modal-ff-list">' + "".join(sections) + '</div>'

    return f'<template id="{template_id}">{header}{body}</template>'


# =====================================================================
# OFFLINE RENDER + COMMIT TO GITHUB PAGES (auroragracewood/badges)
# =====================================================================
# At issuance, we render all 9 form factor SVGs and commit each to the public badges repo
# via the GitHub Contents API. GitHub Pages serves them at https://badges.aurora-gracewood.com/
# under /badge/{slug}/{user_id}/{form_factor}.svg. After issuance, Python is out of the
# embed-view loop — every reader anywhere on the web hits the static file via CDN.
#
# PNG generation deferred for v1 — Windows libcairo install is a separate ticket. SVG-only
# is enough for almost every embed surface; PNG is mainly for email signatures (small fraction).

GITHUB_REPO_OWNER = "auroragracewood"
GITHUB_REPO_NAME = "badges"
GITHUB_PAT_FILE = ROOT / ".github_pat"  # Deployed separately to me-think; NEVER in source.

def _read_github_pat():
    """Read the GitHub Personal Access Token from .github_pat on disk. Token is fine-grained,
    scoped to Contents:read+write on auroragracewood/badges only."""
    if not GITHUB_PAT_FILE.exists():
        return None
    return GITHUB_PAT_FILE.read_text(encoding="utf-8").strip()

def commit_to_github(path, content, commit_msg):
    """PUT a file into auroragracewood/badges via the GitHub Contents API. Creates if absent;
    updates in place if present (carries the existing SHA on update). Returns (ok, message).
    Stdlib-only — no GitHub-SDK dependency."""
    pat = _read_github_pat()
    if not pat:
        return False, "no github PAT on disk (.github_pat missing)"

    api = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # 1) Check if file already exists — GitHub PUT requires the existing SHA on updates.
    sha = None
    try:
        get_req = urllib.request.Request(api, headers=headers, method="GET")
        with urllib.request.urlopen(get_req, timeout=10) as resp:
            data = json.loads(resp.read())
            sha = data.get("sha")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            return False, f"GET failed {e.code}: {e.read().decode(errors='replace')[:200]}"
    except Exception as e:
        return False, f"GET error: {str(e)[:200]}"

    # 2) PUT the new content (base64-encoded).
    if isinstance(content, str):
        content = content.encode("utf-8")
    body = {
        "message": commit_msg,
        "content": base64.b64encode(content).decode("ascii"),
    }
    if sha:
        body["sha"] = sha
    put_req = urllib.request.Request(
        api,
        data=json.dumps(body).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json"},
        method="PUT",
    )
    try:
        with urllib.request.urlopen(put_req, timeout=20) as resp:
            return True, f"PUT {resp.status}"
    except urllib.error.HTTPError as e:
        return False, f"PUT failed {e.code}: {e.read().decode(errors='replace')[:200]}"
    except Exception as e:
        return False, f"PUT error: {str(e)[:200]}"

def render_and_commit_badge(badge_slug, recipient, design_year, awardee_text):
    """Render all 9 form factor SVGs for one (badge × recipient × year) and commit each to
    auroragracewood/badges. Path scheme: /badge/{slug}/{user_id}/{form_factor}.svg

    `awardee_text` is the FROZEN-AT-ISSUANCE awardee (uppercased name as-of grant moment).
    We pass it through `recipient.display_name` so render_badge picks it up; render_badge
    then `.upper()`s it (idempotent on already-uppercased text).

    Returns: dict of {form_factor: (success, message)}.
    """
    user_id = recipient["id"]
    # Build a frozen recipient view so render_badge uses the captured awardee, not live user data.
    frozen_recipient = dict(recipient)
    frozen_recipient["display_name"] = awardee_text

    results = {}
    for ff in FORM_FACTOR_ORDER:
        if ff not in FORM_FACTOR_LAYOUTS:
            continue
        # wrap_link=False — the static SVG file is just artwork. Click-through href is applied
        # only when the badge is shown inline on a profile (using frozen destination_url from DB).
        svg = render_badge(badge_slug, ff, frozen_recipient, design_year, wrap_link=False)
        path = f"badge/{badge_slug}/{user_id}/{ff}.svg"
        commit_msg = f"render {badge_slug}/{user_id}/{ff} ({design_year}, {awardee_text})"
        results[ff] = commit_to_github(path, svg, commit_msg)
    return results


def render_profile(u, roles, links, theme):
    safe = html_mod.escape
    name = u.get("display_name") or u.get("username") or ""
    slug_or_id = u.get("slug") or str(u["id"])
    bio = u.get("bio") or ""
    avatar = u.get("avatar_url") or ""

    if avatar:
        avatar_inner = f'<div class="ag-avatar" role="img" aria-label="{safe(name)}" style="background-image:url(\'{safe(avatar)}\')"></div>'
    else:
        letter = (name[:1] or "?").upper()
        avatar_inner = f'<div class="ag-avatar ag-avatar-letter" aria-hidden="true">{safe(letter)}</div>'
    # Avatar frame is groundwork for future customization (custom borders, badges on the border).
    avatar_html = f'<div class="ag-avatar-frame">{avatar_inner}</div>'

    # Awards rendered in two views: horizontal (default) and timeline. JS toggle switches.
    horizontal_html = ""
    timeline_html = ""
    if roles:
        sorted_roles = sorted(
            [r for r in roles if r.get("year") is not None],
            key=lambda r: -(r.get("year") or 0)
        )
        # Horizontal view: chips with year inline
        if sorted_roles:
            chips = []
            for r in sorted_roles:
                emoji = r.get("emoji") or ""
                chips.append(
                    f'<span class="ag-role-chip">{safe(emoji)} {safe(r["role_name"])} <span class="ag-role-year">{safe(str(r["year"]))}</span></span>'
                )
            horizontal_html = '<div class="ag-roles-horizontal">' + "".join(chips) + '</div>'
        # Timeline view: tighter year rows
        by_year = defaultdict(list)
        for r in sorted_roles:
            by_year[r["year"]].append(r)
        for year in sorted(by_year.keys(), key=lambda y: -y):
            row = f'<div class="ag-year-row"><div class="ag-year-label">{safe(str(year))}</div><div class="ag-year-chips">'
            for r in by_year[year]:
                emoji = r.get("emoji") or ""
                row += f'<span class="ag-chip">{safe(emoji)} {safe(r["role_name"])}</span>'
            row += '</div></div>'
            timeline_html += row

    # Badges area -- structural slot present on every profile.
    # Real badge artwork comes from awards/badDB/ when the badge system ships
    # (see awards/CLAUDE.md). For now: section header always renders, empty state
    # text shows when the user has no badges yet.
    # Pull this user's visible (non-hidden, non-revoked) badges from the DB.
    # destination_url is the FROZEN click target captured at grant moment — readers clicking
    # the badge land where the badge owner was directed at issuance, even if they later get a
    # new slug or change their display name.
    with db() as c:
        visible_badges = c.execute("""
            SELECT badge_slug, design_year, destination_url, awardee_text FROM issued_badges
            WHERE user_id = ? AND hidden_on_profile = 0 AND revoked_at IS NULL
            ORDER BY granted_at ASC
        """, (u["id"],)).fetchall()
    if visible_badges:
        items = []
        for b in visible_badges:
            badge_def = BADGE_REGISTRY.get(b["badge_slug"]) or {}
            ff_layout = FORM_FACTOR_LAYOUTS.get("circle-pin") or {}
            w, h = ff_layout.get("w", 120), ff_layout.get("h", 120)
            svg_url = f"{SNIPPET_HOST}/badge/{b['badge_slug']}/{u['id']}/circle-pin.svg"
            dest = b["destination_url"] or "/awards/"
            alt = f"{badge_def.get('title', b['badge_slug'])} {b['design_year']} — {b['awardee_text'] or ''}".strip()
            items.append(
                f'<a class="ag-badge-link" href="{safe(dest)}" title="{safe(alt)}">'
                f'<img src="{safe(svg_url)}" alt="{safe(alt)}" width="{w}" height="{h}" loading="lazy" style="display:block">'
                f'</a>'
            )
        badges_inner = f'<div class="ag-badges-grid">{"".join(items)}</div>'
    else:
        badges_inner = '<p class="ag-badges-empty">No badges visible.</p>'
    badges_html = f'<section class="ag-badges-section"><h2 class="ag-section-title">Badges</h2>{badges_inner}</section>'

    # Links: original horizontal chip layout
    links_html = ""
    if links:
        items = []
        for l in links:
            url = (l.get("url") or "").strip()
            label = (l.get("label") or url).strip()
            if url.startswith(("http://","https://")):
                items.append(f'<a class="ag-link" href="{safe(url)}" rel="me noopener" target="_blank">{safe(label)}</a>')
        if items:
            links_html = '<nav class="ag-links" aria-label="Links">' + "".join(items) + '</nav>'

    # Primary role chip
    primary_chip = ""
    if u["role"] == "superuser":
        primary_chip = '<span class="ag-chip ag-chip-primary">Aurora</span>'
    elif u["role"] == "admin":
        primary_chip = '<span class="ag-chip ag-chip-primary">Editorial admin</span>'

    og_title = f"{name} · Aurora Gracewood" if name else "Aurora Gracewood"
    og_desc = bio or "Aurora Gracewood public profile"

    css = """
:root {
  /* THEME (inside the card only) */
  --ag-bg: """ + theme['bg'] + """;
  --ag-fg: """ + theme['fg'] + """;
  --ag-accent: """ + theme['accent'] + """;
  --ag-accent2: """ + theme['accent2'] + """;
  --ag-muted: """ + theme['muted'] + """;
  --ag-card: """ + theme['card'] + """;
  --ag-border: """ + theme['border'] + """;
  --ag-font: """ + theme['font'] + """;
  /* Customization slots for future themes. The card-border slot is intentionally
     left empty here; themes/premium tier can override (e.g. inner thick border,
     animated gradient, badge ring). */
  --ag-card-border: none;
  --ag-card-bg: var(--ag-card);
  --ag-avatar-border: none;
  --ag-avatar-padding: 0;
  --ag-avatar-radius: 50%;
  /* PAGE (outside the card) -- light mode default. Decoupled from theme. */
  --ag-page-bg: #ffffff;
  --ag-page-fg: #1c1f2a;
  --ag-page-muted: #7d8a99;
  /* Great Creations family-signal colors (used in the footer wordmark hover). */
  --gc-pink: #ff8fd8;
  --gc-orange: #ffb469;
  --gc-cyan: #45d9ff;
  --ag-light-pink: #f4cfd9;
}
:root.ag-dark {
  --ag-page-bg: #0a0a0e;
  --ag-page-fg: #f6f7fb;
  --ag-page-muted: #8089a4;
}
* { box-sizing: border-box; }
/* Theme-matching thin scrollbars everywhere */
* {
  scrollbar-width: thin;
  scrollbar-color: var(--ag-muted) transparent;
}
*::-webkit-scrollbar { width: 6px; height: 6px; }
*::-webkit-scrollbar-track { background: transparent; }
*::-webkit-scrollbar-thumb { background: var(--ag-muted); }
*::-webkit-scrollbar-thumb:hover { background: var(--ag-fg); }
html, body { margin: 0; padding: 0; }
body {
  /* Page bg/fg follow light/dark mode, NOT the theme. */
  background: var(--ag-page-bg);
  color: var(--ag-page-fg);
  font-family: var(--ag-font);
  -webkit-font-smoothing: antialiased;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  transition: background 200ms ease, color 200ms ease;
}

/* Content area grows to fill viewport so footer stays at the bottom on short pages. */
.ag-page {
  flex: 1 0 auto;
  width: 100%;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 48px 20px 32px;
}

/* Wider portrait card. The card asserts its theme colors explicitly so it
   doesn't inherit page (light/dark) text color when those modes flip. */
.ag-card-container {
  border: var(--ag-card-border);
  background: var(--ag-card-bg);
  color: var(--ag-fg);
  font-family: var(--ag-font);
  padding: 32px 32px;
  width: 100%;
  max-width: 640px;
  display: flex;
  flex-direction: column;
}

/* Original side-by-side header: avatar left, identity right. */
.ag-header { display: flex; gap: 24px; align-items: flex-start; }

/* Avatar frame -- groundwork for future customization (animated borders, badges on the border). */
.ag-avatar-frame {
  border: var(--ag-avatar-border);
  border-radius: var(--ag-avatar-radius);
  padding: var(--ag-avatar-padding);
  position: relative;
  display: inline-block;
  flex-shrink: 0;
  line-height: 0;
}
.ag-avatar {
  width: 144px; height: 144px;
  background-color: var(--ag-card);
  background-position: center; background-size: cover;
  display: flex; align-items: center; justify-content: center;
  border-radius: var(--ag-avatar-radius);
}
.ag-avatar-letter { font-size: 56px; font-weight: 700; color: var(--ag-muted); }

.ag-id { flex: 1; min-width: 0; padding-top: 6px; }
.ag-name { font-size: 28px; font-weight: 700; margin: 0 0 4px; line-height: 1.15; word-wrap: break-word; }
.ag-handle { font-size: 14px; color: var(--ag-muted); margin: 0 0 12px; font-family: ui-monospace, monospace; }

.ag-chip {
  display: inline-block;
  padding: 4px 10px;
  background: var(--ag-accent);
  color: var(--ag-fg);
  font-size: 13px; font-weight: 500;
  margin: 0 6px 6px 0;
  border: 1px solid var(--ag-border);
}
.ag-chip-primary {
  background: var(--ag-accent2);
  color: var(--ag-bg);
  border-color: var(--ag-accent2);
}

.ag-bio {
  margin: 32px 0 24px;
  font-size: 17px;
  line-height: 1.55;
  max-width: 60ch;
  word-wrap: break-word;
}

/* Links: original horizontal chip row */
.ag-links { display: flex; flex-wrap: wrap; gap: 6px; margin: 20px 0 32px; }
.ag-link {
  display: inline-block;
  padding: 4px 9px;
  background: transparent;
  color: var(--ag-fg);
  text-decoration: none;
  font-size: 13px;
  border: 1px solid var(--ag-border);
  transition: border-color 120ms ease, color 120ms ease;
}
.ag-link:hover { border-color: var(--ag-accent2); color: var(--ag-accent2); }

.ag-section-title {
  font-size: 11px; letter-spacing: .14em; text-transform: uppercase;
  color: var(--ag-muted); margin: 0 0 12px; font-weight: 700;
}

/* Badges area -- structural slot. Real artwork comes from awards/badDB/ once badges are wired. */
.ag-badges-section { margin: 28px 0 20px; }
.ag-badges-grid {
  display: flex; flex-wrap: wrap; gap: 12px;
  align-items: flex-start;
}
.ag-badge-item { /* per-badge container; sized by the form factor SVG itself */ }
.ag-badge-link {
  display: inline-block; line-height: 0;
  text-decoration: none; color: inherit;
  border-radius: 50%;
  transition: transform 0.18s ease, filter 0.18s ease;
}
.ag-badge-link:hover { transform: scale(1.04); filter: drop-shadow(0 4px 10px rgba(0,0,0,0.2)); }
.ag-badge-link:focus-visible { outline: 2px solid var(--ag-accent); outline-offset: 3px; }
.ag-badges-empty {
  margin: 0; padding: 14px 16px;
  font-size: 13px; color: var(--ag-muted); font-style: italic;
  border: 1px dashed var(--ag-border);
  background: transparent;
  text-align: center;
}

/* Badges -- top-priority area. Circular avatar-style placeholders. */
.ag-badges-section { margin: 24px 0 28px; }
.ag-badges {
  display: flex; flex-wrap: wrap; gap: 16px;
  padding: 4px 0 6px;
}
.ag-badge {
  display: flex; flex-direction: column; align-items: center;
  text-decoration: none; color: var(--ag-fg);
  width: 76px;
  transition: transform 120ms ease;
}
.ag-badge:hover { transform: translateY(-2px); }
.ag-badge-icon {
  width: 56px; height: 56px;
  display: flex; align-items: center; justify-content: center;
  font-size: 24px;
  background: var(--ag-accent);
  border: 1px solid var(--ag-border);
  border-radius: 50%;
  margin-bottom: 6px;
}
.ag-badge-label {
  font-size: 10px; color: var(--ag-muted);
  text-align: center;
  line-height: 1.2;
}

/* Recognition: horizontal (default) + timeline (toggle). */
.ag-roles-section { margin: 28px 0 16px; }
.ag-roles-section .ag-section-row {
  display: flex; justify-content: space-between; align-items: center;
}
.ag-view-toggle {
  background: transparent;
  border: 1px solid var(--ag-border);
  color: var(--ag-muted);
  width: 22px; height: 22px;
  font-size: 11px;
  padding: 0; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  line-height: 1;
  margin-bottom: 12px;
  transition: color 120ms ease, border-color 120ms ease;
}
.ag-view-toggle:hover { color: var(--ag-accent2); border-color: var(--ag-accent2); }

/* Toggle which view is shown */
.ag-roles-section.view-horizontal .ag-roles-timeline { display: none; }
.ag-roles-section.view-timeline   .ag-roles-horizontal { display: none; }
/* Toggle button icon swaps to indicate the view it switches TO */
.ag-roles-section.view-horizontal .view-icon-horizontal { display: none; }
.ag-roles-section.view-timeline   .view-icon-timeline   { display: none; }

/* Horizontal view */
.ag-roles-horizontal { display: flex; flex-wrap: wrap; gap: 6px; }
.ag-role-chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px;
  background: var(--ag-accent);
  color: var(--ag-fg);
  font-size: 13px; font-weight: 500;
  border: 1px solid var(--ag-border);
}
.ag-role-year {
  font-family: ui-monospace, monospace;
  font-size: 11px;
  color: var(--ag-muted);
}

/* Timeline view (tighter than before) */
.ag-roles-timeline .ag-year-row {
  display: flex; gap: 14px; padding: 8px 0;
  border-top: 1px solid var(--ag-border);
}
.ag-roles-timeline .ag-year-row:last-child { border-bottom: 1px solid var(--ag-border); }
.ag-roles-timeline .ag-year-label { width: 50px; font-weight: 700; flex-shrink: 0; font-size: 13px; }
.ag-roles-timeline .ag-year-chips { flex: 1; }

/* Footer pinned to bottom of viewport on short pages (flex-shrink:0 + body flex column).
   Footer follows page (light/dark) mode, not theme. */
.ag-footer {
  flex-shrink: 0;
  padding: 20px 24px;
  font-size: 12px;
  color: var(--ag-page-muted);
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 12px;
  width: 100%;
  max-width: 720px;
  margin: 0 auto;
}
.ag-footer > :first-child { justify-self: start; }
.ag-footer > :last-child  { justify-self: end; }

/* Aurora wordmark: link home, no underline, hover -> light pink. */
.ag-footer .ag-footer-brand {
  color: var(--ag-page-muted);
  text-decoration: none;
  border-bottom: none;
  transition: color 120ms ease;
}
.ag-footer .ag-footer-brand:hover { color: var(--ag-light-pink); }

/* Great Creations footer line: per-word hover colors. Underline only under "Great Creations". */
.ag-footer-gc {
  color: var(--ag-page-muted);
  text-decoration: none;
}
.ag-footer-gc .gc-underlined {
  text-decoration: underline;
  text-decoration-color: var(--ag-page-muted);
  text-underline-offset: 2px;
  transition: text-decoration-color 120ms ease;
}
.ag-footer-gc:hover .gc-underlined { text-decoration-color: var(--gc-pink); }
.ag-footer-gc .gc-word { transition: color 120ms ease; }
.ag-footer-gc:hover .gc-a        { color: var(--gc-pink); }
.ag-footer-gc:hover .gc-great    { color: var(--gc-orange); }
.ag-footer-gc:hover .gc-creations{ color: var(--gc-cyan); }
.ag-footer-gc:hover .gc-property { color: var(--gc-pink); }

/* Light/dark mode toggle: tiny circle in the footer center. Always visible (footer is sticky). */
#ag-mode-toggle {
  background: transparent;
  border: 1px solid var(--ag-page-muted);
  color: var(--ag-page-muted);
  width: 18px; height: 18px;
  font-size: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border-radius: 50%;
  opacity: 0.55;
  transition: opacity 120ms ease, color 120ms ease, border-color 120ms ease;
  flex-shrink: 0;
  line-height: 1;
}
#ag-mode-toggle:hover { opacity: 1; color: var(--ag-light-pink); border-color: var(--ag-light-pink); }
#ag-mode-toggle .mode-icon-light { display: inline; }
#ag-mode-toggle .mode-icon-dark  { display: none; }
:root.ag-dark #ag-mode-toggle .mode-icon-light { display: none; }
:root.ag-dark #ag-mode-toggle .mode-icon-dark  { display: inline; }

@media (max-width: 600px) {
  .ag-card-container { padding: 24px 20px; }
  .ag-header { flex-direction: column; }
  .ag-avatar { width: 120px; height: 120px; }
  .ag-name { font-size: 24px; }
  .ag-bio { font-size: 16px; }
}
"""

    bio_html = f'<p class="ag-bio">{safe(bio)}</p>' if bio else ''
    if horizontal_html or timeline_html:
        awards_html = (
            '<section class="ag-roles-section view-horizontal">'
            '<div class="ag-section-row">'
            '<h2 class="ag-section-title">Recognition</h2>'
            '<button class="ag-view-toggle" type="button" aria-label="Toggle view" title="Switch view">'
            '<span class="view-icon-horizontal">&#9776;</span>'  # hamburger -> shows in timeline mode (switch to horizontal)
            '<span class="view-icon-timeline">&#9783;</span>'   # bento -> shows in horizontal mode (switch to timeline)
            '</button>'
            '</div>'
            f'{horizontal_html}'
            f'<div class="ag-roles-timeline">{timeline_html}</div>'
            '</section>'
        )
    else:
        awards_html = ""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{safe(og_title)}</title>
<meta name="description" content="{safe(og_desc)}">
<meta property="og:type" content="profile">
<meta property="og:title" content="{safe(og_title)}">
<meta property="og:description" content="{safe(og_desc)}">
<meta property="og:url" content="/u/{safe(slug_or_id)}">
<meta property="og:site_name" content="Aurora Gracewood">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{safe(og_title)}">
<meta name="twitter:description" content="{safe(og_desc)}">
<style>{css}</style>
</head>
<body>
<main class="ag-page">
  <div class="ag-card-container">
    <header class="ag-header">
      {avatar_html}
      <div class="ag-id">
        <h1 class="ag-name">{safe(name)}</h1>
        <p class="ag-handle">@{safe(slug_or_id)}</p>
        {primary_chip}
      </div>
    </header>
    {bio_html}
    {links_html}
    {badges_html}
    {awards_html}
  </div>
</main>
<footer class="ag-footer">
  <a class="ag-footer-brand" href="/">Aurora Gracewood</a>
  <button id="ag-mode-toggle" type="button" aria-label="Toggle light/dark mode" title="Toggle light/dark"><span class="mode-icon-light">&#9728;</span><span class="mode-icon-dark">&#9790;</span></button>
  <a class="ag-footer-gc" href="https://greatcreations.art" target="_blank" rel="noopener"><span class="gc-word gc-a">a</span> <span class="gc-underlined"><span class="gc-word gc-great">Great</span> <span class="gc-word gc-creations">Creations</span></span> <span class="gc-word gc-property">property</span></a>
</footer>
<script>
(function () {{
  // Light/dark mode persistence
  var saved;
  try {{ saved = localStorage.getItem('ag-mode'); }} catch (e) {{}}
  if (saved === 'dark') document.documentElement.classList.add('ag-dark');
  var modeBtn = document.getElementById('ag-mode-toggle');
  if (modeBtn) modeBtn.addEventListener('click', function () {{
    var isDark = document.documentElement.classList.toggle('ag-dark');
    try {{ localStorage.setItem('ag-mode', isDark ? 'dark' : 'light'); }} catch (e) {{}}
  }});
  // Recognition view toggle (horizontal <-> timeline)
  var rolesSection = document.querySelector('.ag-roles-section');
  var viewBtn = document.querySelector('.ag-view-toggle');
  if (rolesSection && viewBtn) viewBtn.addEventListener('click', function () {{
    if (rolesSection.classList.contains('view-horizontal')) {{
      rolesSection.classList.remove('view-horizontal');
      rolesSection.classList.add('view-timeline');
    }} else {{
      rolesSection.classList.remove('view-timeline');
      rolesSection.classList.add('view-horizontal');
    }}
  }});
}})();
</script>
</body>
</html>"""


def render_404():
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Not found · Aurora Gracewood</title>
<meta name="robots" content="noindex">
<style>
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; min-height: 100vh; }
body {
  background: #f6f7fb;
  color: #1c1f2a;
  font-family: 'Inter', system-ui, sans-serif;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  text-align: center; padding: 24px;
}
h1 { font-size: 96px; font-weight: 700; margin: 0; color: #4a5fc1; letter-spacing: -3px; line-height: 1; }
p { font-size: 18px; color: #7d8a99; margin: 12px 0 32px; max-width: 36ch; }
a { color: #4a5fc1; text-decoration: none; border-bottom: 1px solid #e6e8ee; padding-bottom: 2px; font-size: 14px; }
a:hover { border-color: #4a5fc1; }
.ag-footer-mini { position: fixed; bottom: 24px; font-size: 12px; color: #7d8a99; }
.ag-footer-mini a { font-size: 12px; }
</style>
</head>
<body>
<h1>404</h1>
<p>This profile doesn't exist or isn't public.</p>
<a href="/">aurora gracewood &rarr;</a>
<div class="ag-footer-mini">a <a href="https://greatcreations.art">Great Creations</a> property</div>
</body>
</html>"""
