/* ============================================================
   Aurora Gracewood — shared auth module
   ============================================================
   Stub-first: persists to localStorage. Pass-2 swaps in real
   API calls without changing the public surface of this file.
   Public surface (use these from any AG page):
     AGAuth.isLoggedIn()              -> boolean
     AGAuth.getUser()                 -> {name,email,...} | null
     AGAuth.requireAuth(action, opts) -> if logged in, run action;
                                          else open modal, run on success
     AGAuth.signOut()                 -> clear session, refresh chip
     AGAuth.installNav(slot)          -> mount the auth chip in `slot`
     AGAuth.showModal(opts)           -> open modal directly (signin/signup)
   No page reloads anywhere. Modal lifecycle is in-place.
   ============================================================ */

(function () {
  const STORAGE_KEY = 'ag_session_v1';
  // The FastAPI backend (auth source of truth) lives at aurora-gracewood.com.
  // From any apex page (or the awards page on either host) we can fetch /api/me there
  // to learn whether the user has a real session cookie and what their role + slug are.
  const BACKEND_ORIGIN = 'https://aurora-gracewood.com';

  function readSession() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }
  function writeSession(user) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    document.dispatchEvent(new CustomEvent('agauth:change', { detail: user }));
  }
  function clearSession() {
    localStorage.removeItem(STORAGE_KEY);
    document.dispatchEvent(new CustomEvent('agauth:change', { detail: null }));
  }

  function isLoggedIn() { return !!readSession(); }
  function getUser() { return readSession(); }
  function signOut() {
    // Also clear the real backend session if we can reach it (CORS-permitting).
    try {
      fetch(BACKEND_ORIGIN + '/api/signout', { method: 'POST', credentials: 'include', mode: 'cors' }).catch(() => {});
    } catch (e) {}
    clearSession();
    renderChip();
  }

  // Build the per-role URL that "My Profile" should point at, on the rewards backend.
  function profileUrl(user) {
    const role = user && user.role;
    const path = ({
      superuser: '/g-1vl00d/superuser',
      admin:     '/admin/admin',
      client:    '/client/client',
    })[role] || '/awards/';
    // Always absolute to the rewards subdomain so apex pages don't try to serve
    // /account/ as a static path on the wrong host.
    return BACKEND_ORIGIN + path;
  }

  // Fetch the real backend session on page-load. If a session cookie exists on the
  // aurora-gracewood.com domain, this fills in role + slug + email so the chip
  // and "My Profile" link reflect reality. Cross-origin from apex requires CORS on the
  // backend — currently no CORS is configured, so this only works when auth.js is
  // loaded from the rewards subdomain. From apex we silently fall back to localStorage.
  async function syncFromBackend() {
    try {
      const url = (window.location.origin === BACKEND_ORIGIN)
        ? '/api/me'
        : BACKEND_ORIGIN + '/api/me';
      const r = await fetch(url, { credentials: 'include', mode: 'cors' });
      if (!r.ok) {
        // No active backend session. If localStorage thinks we're signed in, leave that
        // alone (stub behavior preserved), but DON'T treat it as authoritative.
        return;
      }
      const data = await r.json();
      const fresh = {
        name: data.display_name || data.username || data.email,
        email: data.email,
        username: data.username,
        role: data.role,
        slug: data.slug,
        id: data.id,
        from_backend: true,
      };
      writeSession(fresh);
    } catch (e) {
      // CORS failure or network error — silent. localStorage stub remains source.
    }
  }

  /* The chip lives in the nav slot. It re-renders on agauth:change so any
     page using it stays in sync without polling. */
  let chipSlot = null;
  function installNav(slot) {
    chipSlot = slot;
    renderChip();
    document.addEventListener('agauth:change', renderChip);
    // Once at install time, sync from the real backend so the chip shows the actual
    // session (role + slug + email) rather than only what's in localStorage.
    syncFromBackend();
  }
  function renderChip() {
    if (!chipSlot) return;
    const user = getUser();
    if (user) {
      chipSlot.innerHTML = `
        <div class="ag-chip ag-chip-in" data-open="false">
          <button class="ag-chip-btn" type="button" aria-haspopup="true">
            <span class="ag-chip-avatar">${initials(user.name || user.email)}</span>
            <span class="ag-chip-name">${esc(user.name || user.email.split('@')[0])}</span>
            <span class="ag-chip-caret">▾</span>
          </button>
          <div class="ag-chip-menu" role="menu">
            <a role="menuitem" href="${profileUrl(user)}">My Profile</a>
            <a role="menuitem" href="${BACKEND_ORIGIN}/awards/#submit">My Submissions</a>
            <a role="menuitem" href="#" data-action="signout">Sign Out</a>
          </div>
        </div>`;
      const root = chipSlot.querySelector('.ag-chip');
      root.querySelector('.ag-chip-btn').addEventListener('click', () => {
        const open = root.getAttribute('data-open') === 'true';
        root.setAttribute('data-open', open ? 'false' : 'true');
      });
      root.querySelector('[data-action="signout"]').addEventListener('click', (e) => {
        e.preventDefault(); signOut();
      });
      document.addEventListener('click', (e) => {
        if (!root.contains(e.target)) root.setAttribute('data-open', 'false');
      });
    } else {
      chipSlot.innerHTML = `
        <div class="ag-chip ag-chip-out">
          <button class="ag-link" type="button" data-mode="signin">Sign In</button>
          <button class="ag-cta" type="button" data-mode="signup">Sign Up Free</button>
        </div>`;
      chipSlot.querySelectorAll('button[data-mode]').forEach((b) => {
        b.addEventListener('click', () => showModal({ mode: b.dataset.mode }));
      });
    }
  }

  /* The modal is the load-bearing UX rule: opens over current page, never
     redirects, never reloads. Captures sign-in/up, on success closes and
     fires the onSuccess action. The user's mid-page state (form inputs,
     scroll position, accordion open state) is preserved. */
  let modalEl = null;
  let modalOnSuccess = null;
  function ensureModal() {
    if (modalEl) return modalEl;
    modalEl = document.createElement('div');
    modalEl.className = 'ag-modal-root';
    modalEl.setAttribute('aria-hidden', 'true');
    modalEl.innerHTML = `
      <div class="ag-modal-backdrop" data-close></div>
      <div class="ag-modal" role="dialog" aria-modal="true" aria-labelledby="ag-modal-title">
        <button class="ag-modal-close" type="button" data-close aria-label="Close">×</button>
        <div class="ag-modal-tabs">
          <button class="ag-modal-tab" data-mode="signin">Sign In</button>
          <button class="ag-modal-tab" data-mode="signup">Sign Up</button>
        </div>
        <h2 id="ag-modal-title" class="ag-modal-title"></h2>
        <p class="ag-modal-sub"></p>
        <form class="ag-modal-form" novalidate>
          <label class="ag-field ag-field-name">
            <span>Display name</span>
            <input name="name" type="text" autocomplete="name" required />
          </label>
          <label class="ag-field">
            <span>Email</span>
            <input name="email" type="email" autocomplete="email" required />
          </label>
          <label class="ag-field">
            <span>Password</span>
            <input name="password" type="password" autocomplete="current-password" required minlength="8" />
          </label>
          <label class="ag-checkline ag-field-share">
            <input name="marketing_share" type="checkbox" />
            <span>I'm OK with my profile being shared across the Great Creations family of brands for relevant offers. (Optional. Awards review is unaffected by this choice.)</span>
          </label>
          <button class="ag-submit" type="submit"></button>
          <p class="ag-modal-error" role="alert"></p>
          <p class="ag-modal-disclosure">Aurora Gracewood accounts work across every Aurora-Gracewood product. Your data is governed by Great Creations' privacy policy.</p>
        </form>
      </div>`;
    document.body.appendChild(modalEl);
    modalEl.querySelectorAll('[data-close]').forEach((el) => {
      el.addEventListener('click', closeModal);
    });
    modalEl.querySelectorAll('.ag-modal-tab').forEach((t) => {
      t.addEventListener('click', () => setMode(t.dataset.mode));
    });
    modalEl.querySelector('.ag-modal-form').addEventListener('submit', (e) => {
      e.preventDefault();
      handleSubmit(e.currentTarget);
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && modalEl.getAttribute('aria-hidden') === 'false') closeModal();
    });
    return modalEl;
  }
  function setMode(mode) {
    const isSignup = mode === 'signup';
    modalEl.querySelector('.ag-modal-title').textContent = isSignup
      ? 'Welcome — set up your free Aurora Gracewood account'
      : 'Welcome back';
    modalEl.querySelector('.ag-modal-sub').textContent = isSignup
      ? "Free. One account works across everything I make."
      : 'Sign in to continue where you left off.';
    modalEl.querySelector('.ag-submit').textContent = isSignup ? 'Create Free Account' : 'Sign In';
    modalEl.querySelectorAll('.ag-modal-tab').forEach((t) => {
      t.classList.toggle('is-active', t.dataset.mode === mode);
    });
    modalEl.querySelector('.ag-field-name').style.display = isSignup ? '' : 'none';
    modalEl.querySelector('.ag-field-share').style.display = isSignup ? '' : 'none';
    modalEl.querySelector('input[name="name"]').required = isSignup;
    modalEl.querySelector('input[name="password"]').setAttribute('autocomplete', isSignup ? 'new-password' : 'current-password');
    modalEl.querySelector('.ag-modal-error').textContent = '';
    modalEl.dataset.mode = mode;
  }
  function showModal(opts) {
    opts = opts || {};
    ensureModal();
    setMode(opts.mode || 'signin');
    modalEl.setAttribute('aria-hidden', 'false');
    modalOnSuccess = typeof opts.onSuccess === 'function' ? opts.onSuccess : null;
    setTimeout(() => {
      const focusEl = modalEl.querySelector(opts.mode === 'signup' ? 'input[name="name"]' : 'input[name="email"]');
      if (focusEl) focusEl.focus();
    }, 50);
  }
  function closeModal() {
    if (!modalEl) return;
    modalEl.setAttribute('aria-hidden', 'true');
    modalOnSuccess = null;
  }
  function handleSubmit(form) {
    const data = new FormData(form);
    const mode = modalEl.dataset.mode;
    const email = (data.get('email') || '').toString().trim();
    const password = (data.get('password') || '').toString();
    const name = (data.get('name') || '').toString().trim();
    const errEl = modalEl.querySelector('.ag-modal-error');
    errEl.textContent = '';
    if (!email || !password) { errEl.textContent = 'Email and password are required.'; return; }
    if (password.length < 8) { errEl.textContent = 'Password must be at least 8 characters.'; return; }
    if (mode === 'signup' && !name) { errEl.textContent = 'Display name is required.'; return; }
    /* Stub auth: accepts any well-formed input. Persists user record locally.
       Pass-2 will replace this with a real fetch() to the Aurora-Gracewood
       auth API. The public surface (signOut, getUser, etc.) does not change. */
    const marketingShare = !!data.get('marketing_share');
    const user = {
      name: name || email.split('@')[0],
      email: email,
      marketing_share: marketingShare,
      created_at: new Date().toISOString()
    };
    writeSession(user);
    closeModal();
    renderChip();
    if (modalOnSuccess) { try { modalOnSuccess(user); } catch (e) { /* swallow */ } }
  }

  function requireAuth(action, opts) {
    if (isLoggedIn()) { action(getUser()); return; }
    showModal(Object.assign({ mode: 'signup' }, opts || {}, { onSuccess: action }));
  }

  function initials(s) {
    if (!s) return '?';
    const parts = s.split(/[\s@.]+/).filter(Boolean);
    return (parts[0] || '?').slice(0, 1).toUpperCase() + (parts[1] ? parts[1].slice(0, 1).toUpperCase() : '');
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  window.AGAuth = {
    isLoggedIn, getUser, signOut, installNav, showModal, requireAuth
  };
})();
