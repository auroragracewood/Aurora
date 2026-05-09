window.AURORA = (function () {
  function defaultAsForPath() {
    const p = window.location.pathname;
    if (p.startsWith("/g-1vl00d")) return "1";
    if (p.startsWith("/admin"))    return "2";
    if (p.startsWith("/client"))   return "9100";
    return "1";
  }
  const url = new URL(window.location.href);
  const asId = url.searchParams.get("as") || defaultAsForPath();

  function withAs(path) {
    const u = new URL(path, window.location.origin);
    u.searchParams.set("as", asId);
    return u.toString();
  }
  async function api(method, path, body) {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body !== undefined) opts.body = JSON.stringify(body);
    const r = await fetch(withAs(path), opts);
    if (!r.ok) {
      let msg = "HTTP " + r.status;
      try { const e = await r.json(); msg = e.detail || msg; } catch {}
      const err = new Error(msg); err.status = r.status; throw err;
    }
    return r.status === 204 ? null : r.json();
  }
  function el(id) { return document.getElementById(id); }
  function setStatus(id, text, ok) {
    const e = el(id); if (!e) return;
    e.className = "status " + (ok === false ? "err" : "ok");
    e.textContent = text;
  }
  function fmtTs(unix) {
    if (!unix) return "—";
    return new Date(unix * 1000).toLocaleString();
  }
  function avatarHTML(user, size) {
    size = size || 96;
    const initial = (user.display_name || user.email || "?")[0].toUpperCase();
    if (user.avatar_url) {
      return '<div class="avatar-circle" style="width:' + size + 'px;height:' + size + 'px;background-image:url(\'' + user.avatar_url + '\')"></div>';
    }
    return '<div class="avatar-circle avatar-letter" style="width:' + size + 'px;height:' + size + 'px;font-size:' + (size * 0.4) + 'px">' + initial + '</div>';
  }
  function rolesChips(roles) {
    if (!roles || !roles.length) return "";
    return '<div class="role-chips">' + roles.map(function (r) {
      return '<span class="role-chip" title="' + r.role_name + (r.year ? " " + r.year : "") + '">' +
        (r.emoji || "") + " " + r.role_name + (r.year ? " " + r.year : "") + '</span>';
    }).join("") + '</div>';
  }
  function showFatal(msg) {
    let box = document.getElementById("aurora-fatal");
    if (!box) {
      box = document.createElement("div");
      box.id = "aurora-fatal";
      box.style.cssText = "position:fixed;top:12px;left:50%;transform:translateX(-50%);z-index:9999;background:#3a0a18;border:1px solid #ff8fd8;color:#ffdde9;padding:14px 22px;border-radius:14px;font-family:Inter,system-ui,sans-serif;font-size:.88rem;box-shadow:0 12px 36px rgba(0,0,0,.5);max-width:560px;";
      document.body.appendChild(box);
    }
    box.innerHTML = msg;
  }
  function showAccountChangedBanner() {
    if (document.getElementById("account-changed-overlay")) return;
    const overlay = document.createElement("div");
    overlay.id = "account-changed-overlay";
    overlay.className = "account-changed-overlay";
    overlay.innerHTML =
      '<div class="account-changed-banner">' +
      '<div class="acc-banner-icon">⚠</div>' +
      '<h2>Your account has been updated</h2>' +
      '<p>An administrator has changed something on your account. Refresh to load the latest data.</p>' +
      '<p class="acc-banner-note">The page is locked until you refresh — to prevent simultaneous edits.</p>' +
      '<button class="btn" onclick="window.location.reload()">↻ Refresh now</button>' +
      '</div>';
    document.body.appendChild(overlay);
  }
  // ============== EMBED-PICKER MODAL ==============
  // Reusable across edit-profile pages for any badge a user owns. Modal HTML is fetched
  // lazily from /api/me/badge-modal/{slug}/{year} so we don't ship ~20KB of snippet markup
  // up-front per badge. The modal frame (backdrop + close + content slot) is created on
  // first call and reused across opens.
  let _modal = null, _modalContent = null, _bodyScrollY = 0;
  function _ensureModal() {
    if (_modal) return;
    _modal = document.createElement("div");
    _modal.id = "ag-badge-modal";
    _modal.className = "ag-modal";
    _modal.hidden = true;
    _modal.setAttribute("role", "dialog");
    _modal.setAttribute("aria-modal", "true");
    _modal.setAttribute("aria-hidden", "true");
    _modal.innerHTML =
      '<div class="ag-modal-backdrop" data-modal-close></div>' +
      '<div class="ag-modal-panel">' +
        '<button type="button" class="ag-modal-close" data-modal-close aria-label="Close">×</button>' +
        '<div class="ag-modal-content" id="ag-modal-content"></div>' +
      '</div>';
    document.body.appendChild(_modal);
    _modalContent = _modal.querySelector(".ag-modal-content");
    _modal.addEventListener("click", function (ev) {
      if (ev.target.matches("[data-modal-close]")) closeBadgeModal();
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && _modal && !_modal.hidden) closeBadgeModal();
    });
    // Copy-to-clipboard event delegation — works for any .ag-copy-btn inside a snippet block.
    _modal.addEventListener("click", function (ev) {
      const btn = ev.target.closest(".ag-copy-btn");
      if (!btn) return;
      const head = btn.closest(".ag-snip-head");
      const block = head ? head.parentNode : null;
      const code = block ? block.querySelector(".ag-snip-code code, .ag-snip-code") : null;
      if (!code) return;
      const text = code.textContent;
      const done = function () {
        const orig = btn.textContent;
        btn.textContent = "Copied ✓";
        btn.classList.add("copied");
        setTimeout(function () {
          btn.textContent = orig === "Copied ✓" ? "Copy" : orig;
          btn.classList.remove("copied");
        }, 1400);
      };
      const fallback = function () {
        const ta = document.createElement("textarea");
        ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
        document.body.appendChild(ta); ta.select();
        try { document.execCommand("copy"); done(); } catch (e) {}
        document.body.removeChild(ta);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done).catch(fallback);
      } else {
        fallback();
      }
    });
  }
  async function openBadgeModal(badgeSlug, designYear) {
    _ensureModal();
    _modalContent.innerHTML = "";
    _modalContent.classList.add("loading");
    _bodyScrollY = window.scrollY || window.pageYOffset || 0;
    document.body.style.position = "fixed";
    document.body.style.top = "-" + _bodyScrollY + "px";
    document.body.style.width = "100%";
    _modal.hidden = false;
    _modal.setAttribute("aria-hidden", "false");
    const closeBtn = _modal.querySelector(".ag-modal-close");
    if (closeBtn) closeBtn.focus();
    try {
      const r = await fetch(withAs("/api/me/badge-modal/" + encodeURIComponent(badgeSlug) + "/" + encodeURIComponent(designYear)));
      if (!r.ok) throw new Error("HTTP " + r.status);
      const html = await r.text();
      _modalContent.classList.remove("loading");
      _modalContent.innerHTML = html;
    } catch (e) {
      _modalContent.classList.remove("loading");
      _modalContent.innerHTML = '<div style="padding:32px 0;text-align:center;color:#ff8fd8">Couldn\'t load badge details. ' + (e.message || "") + '</div>';
    }
  }
  function closeBadgeModal() {
    if (!_modal || _modal.hidden) return;
    _modal.hidden = true;
    _modal.setAttribute("aria-hidden", "true");
    document.body.style.position = "";
    document.body.style.top = "";
    document.body.style.width = "";
    window.scrollTo(0, _bodyScrollY);
    _modalContent.innerHTML = "";
  }

  return { asId, withAs, api, el, setStatus, fmtTs, avatarHTML, rolesChips, showFatal, showAccountChangedBanner,
           openBadgeModal, closeBadgeModal };
})();

document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("a[data-realm-link]").forEach(function (a) {
    a.href = AURORA.withAs(a.getAttribute("href"));
  });

  let baselineChangedAt = null;

  async function pollMe(initial) {
    try {
      const me = await AURORA.api("GET", "/api/me");
      if (initial) {
        baselineChangedAt = me.admin_changed_at || 0;
        if (me.unread_messages && me.unread_messages > 0) {
          const banner = document.querySelector(".realm-banner");
          if (banner && !banner.querySelector(".unread-indicator")) {
            const dot = document.createElement("span");
            dot.className = "unread-indicator";
            dot.title = "You have unread messages";
            dot.textContent = me.unread_messages > 9 ? "9+" : String(me.unread_messages);
            banner.appendChild(dot);
          }
        }
        return;
      }
      // Subsequent polls: detect admin change
      if ((me.admin_changed_at || 0) > baselineChangedAt) {
        AURORA.showAccountChangedBanner();
      }
    } catch (err) {
      if (initial && err.status === 401) {
        const path = window.location.pathname;
        let realm = "superuser", validId = "1";
        if (path.startsWith("/admin")) { realm = "admin"; validId = "2"; }
        else if (path.startsWith("/client")) { realm = "client"; validId = "9100"; }
        const goodUrl = path + "?as=" + validId;
        AURORA.showFatal(
          "<strong>User #" + AURORA.asId + " does not exist.</strong><br><br>" +
          "This is the <em>" + realm + "</em> realm. Use this URL instead:<br>" +
          "<a href=\"" + goodUrl + "\" style=\"color:#45d9ff;text-decoration:underline\">" +
          "http://me-think:8000" + goodUrl + "</a><br><br>" +
          "<small style=\"opacity:.7\">Test users: superuser=1, admin=2, client=9100</small>"
        );
      }
    }
  }
  pollMe(true);
  setInterval(function () { pollMe(false); }, 8000);
});
