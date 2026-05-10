/* ============================================================
   Aurora Gracewood — shared auth module
   ============================================================
   Source-of-truth: server `users`/`sessions` tables, identified
   client-side by the `ag_session` HttpOnly cookie set on
   /api/signin or /api/verify success. ZERO localStorage / IndexedDB
   usage — the only client-side state is an in-memory cache of the
   last /api/me response, refreshed on every page load and after
   each auth-changing action.

   Public surface:
     AGAuth.isLoggedIn()              -> boolean
     AGAuth.getUser()                 -> {name,email,role,username,slug,id} | null
     AGAuth.requireAuth(action, opts) -> if logged in, run action;
                                          else open modal, run on success
     AGAuth.signOut()                 -> POST /api/signout, refresh chip
     AGAuth.installNav(slot)          -> mount the auth chip in `slot`
     AGAuth.showModal(opts)           -> open modal directly (signin/signup/forgot-password)
     AGAuth.ready                     -> Promise<user|null>, resolves after first /api/me
   ============================================================ */

(function () {
  // FastAPI backend lives at the apex via Cloudflare Tunnel. Same-origin from
  // every Aurora-Gracewood page, so /api/* fetches don't need CORS.
  const BACKEND_ORIGIN = 'https://aurora-gracewood.com';

  // In-memory cache of the last /api/me. Set by syncFromBackend(); cleared on
  // signOut() or on a 401 from /api/me. Never persisted to disk.
  let _currentUser = null;
  let _readyResolve = null;
  const _ready = new Promise((res) => { _readyResolve = res; });

  function getUser() { return _currentUser; }
  function isLoggedIn() { return !!_currentUser; }

  function _setUser(u) {
    _currentUser = u;
    document.dispatchEvent(new CustomEvent('agauth:change', { detail: u }));
  }

  async function syncFromBackend() {
    try {
      const url = (window.location.origin === BACKEND_ORIGIN)
        ? '/api/me'
        : BACKEND_ORIGIN + '/api/me';
      const r = await fetch(url, { credentials: 'include', mode: 'cors' });
      if (!r.ok) {
        _setUser(null);
        return null;
      }
      const data = await r.json();
      // signed_in: true only when a real cookie session backs the request, not the
      // dev ?as= override. Treat ?as= as "not signed in" from the chip's perspective —
      // the dashboard pages show their data via the override, but auth-gated UI elsewhere
      // (chip, edit-profile, signin/signout button) must respect the real session state.
      if (!data.signed_in) {
        _setUser(null);
        return null;
      }
      _setUser({
        name: data.display_name || data.username || data.email,
        email: data.email,
        username: data.username,
        role: data.role,
        slug: data.slug,
        id: data.id,
      });
      return _currentUser;
    } catch (e) {
      _setUser(null);
      return null;
    }
  }

  async function signOut() {
    try {
      await fetch(BACKEND_ORIGIN + '/api/signout', {
        method: 'POST', credentials: 'include', mode: 'cors',
      });
    } catch (e) {}
    _setUser(null);
    renderChip();
  }

  function profileUrl(user) {
    const role = user && user.role;
    const path = ({
      superuser: '/g-1vl00d/superuser',
      admin:     '/admin/admin',
      client:    '/client/client',
    })[role] || null;
    if (!path) return BACKEND_ORIGIN + '/account/';
    return BACKEND_ORIGIN + path;
  }
  function submissionsUrl(user) {
    const role = user && user.role;
    const folder = ({ superuser: 'g-1vl00d', admin: 'admin', client: 'client' })[role] || 'client';
    return BACKEND_ORIGIN + '/' + folder + '/submissions';
  }

  /* The chip mounts into a nav slot. It re-renders on agauth:change so any
     page using it stays in sync without polling. */
  let chipSlot = null;
  function installNav(slot) {
    chipSlot = slot;
    renderChip();
    document.addEventListener('agauth:change', renderChip);
    // Always sync from /api/me on mount — that's the single source of truth.
    syncFromBackend().finally(() => { if (_readyResolve) { _readyResolve(_currentUser); _readyResolve = null; } });
  }
  function renderChip() {
    if (!chipSlot) return;
    const user = _currentUser;
    if (user) {
      chipSlot.innerHTML = `
        <div class="ag-chip ag-chip-in" data-open="false">
          <button class="ag-chip-btn" type="button" aria-haspopup="true">
            <span class="ag-chip-avatar">${initials(user.name || user.email)}</span>
            <span class="ag-chip-name">${esc(user.name || (user.email || '').split('@')[0])}</span>
            <span class="ag-chip-caret">▾</span>
          </button>
          <div class="ag-chip-menu" role="menu">
            <a role="menuitem" href="${profileUrl(user)}">My Profile</a>
            <a role="menuitem" href="${submissionsUrl(user)}">My Submissions</a>
            <a role="menuitem" href="${BACKEND_ORIGIN}/awards/#submit">Submit New Entry</a>
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

  /* Modal — three modes:
       signin           : email + password
       signup           : email only (backend emails verify link)
       forgot-password  : email only (backend emails reset link)
     Always opens over current page; never reloads. */
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
          <label class="ag-field">
            <span>Email</span>
            <input name="email" type="email" autocomplete="email" required />
          </label>
          <label class="ag-field ag-field-password">
            <span>Password</span>
            <input name="password" type="password" autocomplete="current-password" minlength="8" />
          </label>
          <button class="ag-submit" type="submit"></button>
          <div class="ag-modal-links" style="margin-top:12px;text-align:center;font-size:.84rem">
            <a href="#" data-mode-link="forgot-password" style="color:rgba(246,247,251,.65);text-decoration:underline;text-decoration-color:rgba(246,247,251,.3)">Forgot password?</a>
          </div>
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
    modalEl.querySelectorAll('[data-mode-link]').forEach((a) => {
      a.addEventListener('click', (e) => { e.preventDefault(); setMode(a.dataset.modeLink); });
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
    const isForgot = mode === 'forgot-password';
    const isSignin = mode === 'signin' || (!isSignup && !isForgot);
    const titleEl = modalEl.querySelector('.ag-modal-title');
    const subEl = modalEl.querySelector('.ag-modal-sub');
    const submitBtn = modalEl.querySelector('.ag-submit');
    if (isSignup) {
      titleEl.textContent = 'Sign up — free Aurora Gracewood account';
      subEl.textContent = "Enter your email and I'll send a setup link. Choose a username and password from there.";
      submitBtn.textContent = 'Send Setup Link';
    } else if (isForgot) {
      titleEl.textContent = 'Forgot your password?';
      subEl.textContent = "Enter your email and I'll send a reset link. Check your inbox in a minute.";
      submitBtn.textContent = 'Send Reset Link';
    } else {
      titleEl.textContent = 'Welcome back';
      subEl.textContent = 'Sign in to continue where you left off.';
      submitBtn.textContent = 'Sign In';
    }
    modalEl.querySelectorAll('.ag-modal-tab').forEach((t) => {
      t.classList.toggle('is-active', t.dataset.mode === (isForgot ? 'signin' : mode));
    });
    // Password field: only shown for signin. Signup + forgot-password are email-only.
    const pwField = modalEl.querySelector('.ag-field-password');
    if (pwField) pwField.style.display = isSignin ? '' : 'none';
    const pwInput = modalEl.querySelector('input[name="password"]');
    pwInput.required = isSignin;
    pwInput.setAttribute('autocomplete', isSignin ? 'current-password' : 'new-password');
    // Forgot link: hide on forgot mode (already there), show on signin, hide on signup.
    const links = modalEl.querySelector('.ag-modal-links');
    if (links) links.style.display = isSignin ? '' : 'none';
    modalEl.querySelector('.ag-modal-error').textContent = '';
    // Reset form visibility (signup-success / forgot-success hide the form to show
    // a "check your email" message; on next mode change the form must be visible again).
    const formEl = modalEl.querySelector('.ag-modal-form');
    if (formEl) formEl.style.display = '';
    modalEl.dataset.mode = mode;
  }
  function showModal(opts) {
    opts = opts || {};
    ensureModal();
    setMode(opts.mode || 'signin');
    modalEl.setAttribute('aria-hidden', 'false');
    modalOnSuccess = typeof opts.onSuccess === 'function' ? opts.onSuccess : null;
    setTimeout(() => {
      const focusEl = modalEl.querySelector('input[name="email"]');
      if (focusEl) focusEl.focus();
    }, 50);
  }
  function closeModal() {
    if (!modalEl) return;
    modalEl.setAttribute('aria-hidden', 'true');
    modalOnSuccess = null;
  }
  async function handleSubmit(form) {
    const data = new FormData(form);
    const mode = modalEl.dataset.mode;
    const email = (data.get('email') || '').toString().trim();
    const password = (data.get('password') || '').toString();
    const errEl = modalEl.querySelector('.ag-modal-error');
    errEl.textContent = '';
    if (!email) { errEl.textContent = 'Email is required.'; return; }
    if (mode === 'signin' && !password) { errEl.textContent = 'Password is required to sign in.'; return; }

    const submitBtn = modalEl.querySelector('.ag-submit');
    const origLabel = submitBtn.textContent;
    submitBtn.disabled = true; submitBtn.textContent = 'Working…';

    try {
      let endpoint, payload;
      if (mode === 'signup') {
        endpoint = '/api/signup'; payload = { email };
      } else if (mode === 'forgot-password') {
        endpoint = '/api/forgot-password'; payload = { email };
      } else {
        endpoint = '/api/signin'; payload = { email, password };
      }
      const r = await fetch(BACKEND_ORIGIN + endpoint, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || ('HTTP ' + r.status));
      }

      if (mode === 'signin') {
        // Cookie now set; pull the canonical user record and update chip.
        await syncFromBackend();
        const user = _currentUser;
        closeModal();
        renderChip();
        if (modalOnSuccess) { try { modalOnSuccess(user); } catch (e) {} }
      } else {
        // signup / forgot-password — confirmation message, leave modal open.
        modalEl.querySelector('.ag-modal-title').textContent = 'Check your email';
        modalEl.querySelector('.ag-modal-sub').textContent = mode === 'signup'
          ? 'I just emailed ' + email + ' a setup link. Click it within 24 hours to choose a username and password.'
          : 'If an account exists for ' + email + ', I just sent a reset link. It expires in 1 hour.';
        form.style.display = 'none';
      }
    } catch (e) {
      errEl.textContent = e.message || 'Something went wrong. Try again.';
    } finally {
      submitBtn.disabled = false; submitBtn.textContent = origLabel;
    }
  }

  function requireAuth(action, opts) {
    if (isLoggedIn()) { action(_currentUser); return; }
    showModal(Object.assign({ mode: 'signin' }, opts || {}, { onSuccess: action }));
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
    isLoggedIn, getUser, signOut, installNav, showModal, requireAuth,
    ready: _ready,
    refresh: syncFromBackend,
  };

  // Auto-sync on script load so pages that use AGAuth.getUser() / isLoggedIn() without
  // calling installNav (e.g., /account/index.html) still get the current user state.
  // installNav still triggers a sync — this is a redundant safety net for non-chip pages.
  syncFromBackend().finally(() => { if (_readyResolve) { _readyResolve(_currentUser); _readyResolve = null; } });
})();
