window.AURORA = (function () {
  // Cookie auth is the only auth path. ?as= is honored ONLY if explicitly present in the URL
  // AND the cookie session belongs to a superuser (enforced server-side in get_actor).
  // No more test-user fallback IDs — every account is real.
  const url = new URL(window.location.href);
  const asId = url.searchParams.get("as") || null;

  function withAs(path) {
    const u = new URL(path, window.location.origin);
    if (asId) u.searchParams.set("as", asId);
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
  function actorRoleHome(role) {
    return ({ superuser: '/g-1vl00d/superuser', admin: '/admin/admin', client: '/client/client' })[role] || '/awards/';
  }

  function showAuthRequired(actorRole) {
    /* Full-screen frost + centered CTA. Two modes:
         actorRole undefined → not signed in → "Sign in required"
         actorRole defined   → signed in but wrong realm for that role → "Wrong realm"
       Idempotent — only renders once. Locks scroll so the page can't be navigated
       underneath. No leaks of internal IDs or hostnames. */
    if (document.getElementById("aurora-auth-required")) return;
    const path = window.location.pathname;
    const realmName =
      path.startsWith("/g-1vl00d") ? "Superuser" :
      path.startsWith("/admin")    ? "Admin"     :
      path.startsWith("/client")   ? "Client"    : "Aurora Gracewood";
    let title, body, ctaHref, ctaText;
    if (actorRole) {
      title = "Wrong realm";
      body = "The " + realmName + " realm is for " + realmName.toLowerCase() +
             " accounts only. You're signed in as a " + actorRole + ".";
      ctaHref = actorRoleHome(actorRole);
      ctaText = "Go to your dashboard →";
    } else {
      title = "Sign in required";
      body = "The " + realmName + " realm is private. Sign in to continue.";
      ctaHref = "/account/?next=" + encodeURIComponent(path);
      ctaText = "Sign in →";
    }
    const overlay = document.createElement("div");
    overlay.id = "aurora-auth-required";
    overlay.innerHTML =
      '<div class="aurora-auth-required-card">' +
        '<h2>' + title + '</h2>' +
        '<p>' + body + '</p>' +
        '<a class="aurora-auth-required-btn" href="' + ctaHref + '">' + ctaText + '</a>' +
        '<div class="aurora-auth-required-home"><a href="/awards/">← Aurora Awards</a></div>' +
      '</div>';
    document.body.appendChild(overlay);
    document.body.style.overflow = "hidden";
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

  /* ============== UNREAD INDICATOR + AUTH-CONTROL BANNER BUTTONS ==============
     The realm-banner is hardcoded HTML in every role page. realm.js injects the
     unread-count indicator (existing) and the signin/signout button (new) on
     page load, so we don't have to update every role page when these change. */
  let _signedIn = false;
  function isSignedIn() { return _signedIn; }
  function setSignedIn(v) { _signedIn = !!v; }

  function adjustUnreadIndicator(delta) {
    const banner = document.querySelector(".realm-banner");
    if (!banner) return;
    const dot = banner.querySelector(".unread-indicator");
    if (!dot) return;
    const cur = parseInt(dot.textContent.replace(/\+$/, ""), 10) || 0;
    const next = Math.max(0, cur + delta);
    if (next === 0) dot.remove();
    else dot.textContent = next > 9 ? "9+" : String(next);
  }

  async function markMessageRead(messageId) {
    /* Calls the backend mark-read endpoint, decrements the banner indicator on
       success. Caller is responsible for updating the message-row UI (e.g.,
       removing the UNREAD pill) after the promise resolves. */
    await api("PUT", "/api/messages/" + encodeURIComponent(messageId) + "/read");
    adjustUnreadIndicator(-1);
  }
  async function markMessageUnread(messageId) {
    /* Reverse of markMessageRead — flips a read message back to unread,
       increments the banner indicator on success. */
    await api("PUT", "/api/messages/" + encodeURIComponent(messageId) + "/unread");
    adjustUnreadIndicator(+1);
  }

  function renderBannerAuthControl(signedIn) {
    /* Adds a sign-in or sign-out button to the realm-banner on page load.
       Sign-in -> redirect to /account/ which has the modal; on success the
       user lands back here via that page's "Open Aurora Awards" button or
       direct URL. Sign-out -> POST /api/signout, reload to clear UI state. */
    const banner = document.querySelector(".realm-banner");
    if (!banner) return;
    const existing = banner.querySelector(".realm-auth-btn");
    if (existing) existing.remove();
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "realm-auth-btn " + (signedIn ? "is-out" : "is-in");
    btn.textContent = signedIn ? "Sign out" : "Sign in";
    btn.style.cssText =
      "margin-left:12px;padding:4px 12px;border-radius:6px;font:inherit;font-size:.78rem;font-weight:700;cursor:pointer;" +
      (signedIn
        ? "background:transparent;color:#fff;border:1px solid rgba(255,255,255,.40);"
        : "background:linear-gradient(135deg,#4a5fc1,#f4cfd9);color:#08101b;border:0;");
    btn.addEventListener("click", async () => {
      if (signedIn) {
        try {
          await fetch("/api/signout", { method: "POST", credentials: "include" });
        } catch (e) {}
        window.location.reload();
      } else {
        const next = encodeURIComponent(window.location.pathname);
        window.location.href = "/account/?next=" + next;
      }
    });
    banner.appendChild(btn);
  }

  return { asId, withAs, api, el, setStatus, fmtTs, avatarHTML, rolesChips, showFatal, showAuthRequired, showAccountChangedBanner,
           openBadgeModal, closeBadgeModal,
           isSignedIn, setSignedIn, adjustUnreadIndicator, markMessageRead, markMessageUnread, renderBannerAuthControl };
})();

// =====================================================================
// Themed dialog helpers (window.AGUI) — replaces native alert/confirm/prompt.
// Defined here AND in auth.js so every page that loads either script gets them.
// Last loaded wins; the implementations are identical so duplication is harmless.
// =====================================================================
(function () {
  function toast(msg, opts) {
    opts = opts || {};
    const type = opts.type || 'info';
    const ttl = opts.ttl != null ? opts.ttl : 4000;
    let host = document.getElementById('ag-toast-host');
    if (!host) {
      host = document.createElement('div');
      host.id = 'ag-toast-host';
      document.body.appendChild(host);
    }
    const t = document.createElement('div');
    t.className = 'ag-toast ag-toast-' + type;
    t.textContent = msg;
    host.appendChild(t);
    requestAnimationFrame(() => t.classList.add('ag-toast-shown'));
    setTimeout(() => {
      t.classList.remove('ag-toast-shown');
      setTimeout(() => { if (t.parentNode) t.parentNode.removeChild(t); }, 250);
    }, ttl);
  }
  function _esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  }
  function confirmDialog(msg, opts) {
    opts = opts || {};
    const yes = opts.yesLabel || 'Confirm';
    const no = opts.noLabel || 'Cancel';
    const title = opts.title || '';
    const danger = !!opts.danger;
    return new Promise(resolve => {
      const ov = document.createElement('div');
      ov.className = 'ag-confirm-overlay';
      ov.innerHTML =
        '<div class="ag-confirm-card" role="dialog" aria-modal="true">' +
          (title ? '<h3 class="ag-confirm-title">' + _esc(title) + '</h3>' : '') +
          '<div class="ag-confirm-msg">' + _esc(msg) + '</div>' +
          '<div class="ag-confirm-actions">' +
            '<button type="button" class="ag-confirm-no">' + _esc(no) + '</button>' +
            '<button type="button" class="ag-confirm-yes' + (danger ? ' is-danger' : '') + '">' + _esc(yes) + '</button>' +
          '</div>' +
        '</div>';
      document.body.appendChild(ov);
      function close(v) {
        document.removeEventListener('keydown', onKey);
        ov.remove();
        resolve(v);
      }
      function onKey(e) { if (e.key === 'Escape') close(false); }
      ov.querySelector('.ag-confirm-yes').addEventListener('click', () => close(true));
      ov.querySelector('.ag-confirm-no').addEventListener('click', () => close(false));
      document.addEventListener('keydown', onKey);
      setTimeout(() => ov.querySelector('.ag-confirm-yes').focus(), 50);
    });
  }
  function promptDialog(msg, opts) {
    opts = opts || {};
    const title = opts.title || '';
    const placeholder = opts.placeholder || '';
    const submit = opts.submitLabel || 'Submit';
    const cancel = opts.cancelLabel || 'Cancel';
    const initialValue = opts.value || '';
    const danger = !!opts.danger;
    return new Promise(resolve => {
      const ov = document.createElement('div');
      ov.className = 'ag-confirm-overlay';
      ov.innerHTML =
        '<div class="ag-confirm-card" role="dialog" aria-modal="true">' +
          (title ? '<h3 class="ag-confirm-title">' + _esc(title) + '</h3>' : '') +
          '<div class="ag-confirm-msg">' + _esc(msg) + '</div>' +
          '<input type="text" class="ag-prompt-input" placeholder="' + _esc(placeholder) + '" autocomplete="off" value="' + _esc(initialValue) + '">' +
          '<div class="ag-confirm-actions">' +
            '<button type="button" class="ag-confirm-no">' + _esc(cancel) + '</button>' +
            '<button type="button" class="ag-confirm-yes' + (danger ? ' is-danger' : '') + '">' + _esc(submit) + '</button>' +
          '</div>' +
        '</div>';
      document.body.appendChild(ov);
      const input = ov.querySelector('.ag-prompt-input');
      function close(v) {
        document.removeEventListener('keydown', onKey);
        ov.remove();
        resolve(v);
      }
      function onKey(e) { if (e.key === 'Escape') close(null); }
      ov.querySelector('.ag-confirm-yes').addEventListener('click', () => close(input.value));
      ov.querySelector('.ag-confirm-no').addEventListener('click', () => close(null));
      input.addEventListener('keydown', e => {
        if (e.key === 'Enter') close(input.value);
      });
      document.addEventListener('keydown', onKey);
      setTimeout(() => input.focus(), 50);
    });
  }
  window.AGUI = { toast: toast, confirmDialog: confirmDialog, promptDialog: promptDialog };
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
        AURORA.setSignedIn(!!me.signed_in);
        AURORA.renderBannerAuthControl(!!me.signed_in);
        // Role gate: each realm path is for one role only. Mismatch (e.g., signed-in
        // admin trying to view /g-1vl00d/*) → frost overlay with "Wrong realm" copy.
        // Superuser viewing /g-1vl00d, admin viewing /admin, client viewing /client all pass.
        const path = window.location.pathname;
        const expectedRole =
          path.startsWith("/g-1vl00d") ? "superuser" :
          path.startsWith("/admin")    ? "admin"     :
          path.startsWith("/client")   ? "client"    : null;
        if (expectedRole && me.role !== expectedRole) {
          AURORA.showAuthRequired(me.role);
          return;
        }
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
        AURORA.showAuthRequired();
      }
    }
  }
  pollMe(true);
  setInterval(function () { pollMe(false); }, 8000);
});
