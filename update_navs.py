"""
Rewrite the <nav class="nav">...</nav> block in every realm HTML file to a
canonical, ordered list. Same item order across all three realms (omitting
items that don't apply to that role); each realm gets the same "Menu" dropdown
at the end.

Run once, then delete this script (it's a one-shot migration).
"""
import re
from pathlib import Path

ROOT = Path(__file__).parent / "account"

# Canonical order: Profile, Edit profile, Submissions, Messages, Sessions,
# Activity, Notifications, Settings, [Manage Users / Clients].
# Plus the "Menu" dropdown overlay at the end.
MENU_BLOCK = """    <span class="nav-menu-wrap">
      <span class="nav-menu-ghost">Menu &#9662;</span>
      <span class="nav-menu" data-state="closed">
        <button type="button" class="nav-menu-toggle" aria-haspopup="true" aria-expanded="false"><span class="nav-menu-label">Menu</span><span class="nav-menu-arrow">&#9662;</span></button>
        <span class="nav-menu-list">
          <a href="/">Home</a>
          <a href="/awards/">Awards</a>
          <a href="#" data-public-profile-link>Public profile</a>
          <a href="/awards/#submit">Submit entry</a>
        </span>
      </span>
    </span>"""

NAVS = {
    "g-1vl00d": [
        ("/g-1vl00d/superuser", "Profile"),
        ("/g-1vl00d/profile-edit", "Edit profile"),
        ("/g-1vl00d/submissions", "Submissions"),
        ("/g-1vl00d/messages", "Messages"),
        ("/g-1vl00d/sessions", "Sessions"),
        ("/g-1vl00d/activity", "Activity"),
        ("/g-1vl00d/notifications", "Notifications"),
        ("/g-1vl00d/settings", "Settings"),
        ("/g-1vl00d/manage-users", "Manage users"),
    ],
    "admin": [
        ("/admin/admin", "Profile"),
        ("/admin/profile-edit", "Edit profile"),
        ("/admin/submissions", "Submissions"),
        ("/admin/messages", "Messages"),
        ("/admin/activity", "Activity"),
        ("/admin/notifications", "Notifications"),
        ("/admin/clients", "Clients"),
    ],
    "client": [
        ("/client/client", "Profile"),
        ("/client/profile-edit", "Edit profile"),
        ("/client/submissions", "Submissions"),
        ("/client/messages", "Messages"),
        ("/client/activity", "Activity"),
        ("/client/notifications", "Notifications"),
    ],
}

NAV_RE = re.compile(r'<nav class="nav">.*?</nav>', re.DOTALL)


def build_nav(realm):
    lines = ['<nav class="nav">']
    for href, label in NAVS[realm]:
        lines.append(f'    <a data-realm-link href="{href}">{label}</a>')
    lines.append(MENU_BLOCK)
    lines.append("  </nav>")
    return "\n".join(lines)


def main():
    changed = 0
    for realm in NAVS:
        nav_html = build_nav(realm)
        for f in (ROOT / realm).glob("*.html"):
            txt = f.read_text(encoding="utf-8")
            new_txt, n = NAV_RE.subn(nav_html, txt, count=1)
            if n == 0:
                print(f"  SKIP {f.relative_to(ROOT.parent)} (no <nav class=\"nav\"> found)")
                continue
            if new_txt != txt:
                f.write_text(new_txt, encoding="utf-8")
                print(f"  OK   {f.relative_to(ROOT.parent)}")
                changed += 1
            else:
                print(f"  SAME {f.relative_to(ROOT.parent)}")
    print(f"\n{changed} files updated.")


if __name__ == "__main__":
    main()
