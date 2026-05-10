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
            <div class="ag-pw-row">
              <input name="password" type="password" autocomplete="current-password" />
              <button type="button" class="ag-eye-btn" data-eye="password" aria-label="Show password" title="Show / hide password">👁</button>
            </div>
            <div class="ag-caps-warning" id="ag-caps-warning" hidden>⚠ Caps Lock is on</div>
          </label>
          <label class="ag-checkline ag-field-remember">
            <input name="remember" type="checkbox" />
            <span>Remember this device for 30 days. Leave unchecked on shared computers.</span>
          </label>
          <button class="ag-submit" type="submit"></button>
          <div class="ag-modal-links" style="margin-top:12px;text-align:center;font-size:.84rem">
            <a href="#" data-mode-link="forgot-password" style="color:rgba(246,247,251,.65);text-decoration:underline;text-decoration-color:rgba(246,247,251,.3)">Forgot password?</a>
            <span style="color:rgba(246,247,251,.3);margin:0 8px">·</span>
            <a href="#" data-mode-link="forgot-username" style="color:rgba(246,247,251,.65);text-decoration:underline;text-decoration-color:rgba(246,247,251,.3)">Forgot username?</a>
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
    // Eye-icon toggles for any password field in the modal.
    modalEl.querySelectorAll('.ag-eye-btn').forEach((b) => {
      b.addEventListener('click', () => {
        const inp = modalEl.querySelector('input[name="' + b.dataset.eye + '"]');
        if (!inp) return;
        const showing = inp.type === 'text';
        inp.type = showing ? 'password' : 'text';
        b.textContent = showing ? '👁' : '🙈';
        b.setAttribute('aria-label', showing ? 'Show password' : 'Hide password');
      });
    });
    // Caps Lock detector on the password field — common cause of failed sign-in.
    const pwInput = modalEl.querySelector('input[name="password"]');
    const capsWarning = modalEl.querySelector('#ag-caps-warning');
    function updateCapsHint(ev) {
      if (!capsWarning) return;
      const on = ev.getModifierState && ev.getModifierState('CapsLock');
      capsWarning.hidden = !on;
    }
    if (pwInput) {
      pwInput.addEventListener('keydown', updateCapsHint);
      pwInput.addEventListener('keyup', updateCapsHint);
      pwInput.addEventListener('blur', () => { if (capsWarning) capsWarning.hidden = true; });
    }
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && modalEl.getAttribute('aria-hidden') === 'false') closeModal();
    });
    return modalEl;
  }
  function setMode(mode) {
    const isSignup = mode === 'signup';
    const isForgotPw = mode === 'forgot-password';
    const isForgotUser = mode === 'forgot-username';
    const isForgot = isForgotPw || isForgotUser;
    const isSignin = mode === 'signin' || (!isSignup && !isForgot);
    const titleEl = modalEl.querySelector('.ag-modal-title');
    const subEl = modalEl.querySelector('.ag-modal-sub');
    const submitBtn = modalEl.querySelector('.ag-submit');
    if (isSignup) {
      titleEl.textContent = 'Sign up — free Aurora Gracewood account';
      subEl.textContent = "Enter your email and I'll send a setup link. Choose a username and password from there.";
      submitBtn.textContent = 'Send Setup Link';
    } else if (isForgotPw) {
      titleEl.textContent = 'Forgot your password?';
      subEl.textContent = "Enter your email and I'll send a reset link plus your username. Check your inbox in a minute.";
      submitBtn.textContent = 'Send Reset Link';
    } else if (isForgotUser) {
      titleEl.textContent = 'Forgot your username?';
      subEl.textContent = "Enter your email and I'll send your username. Check your inbox in a minute.";
      submitBtn.textContent = 'Send My Username';
    } else {
      titleEl.textContent = 'Welcome back';
      subEl.textContent = 'Sign in to continue where you left off.';
      submitBtn.textContent = 'Sign In';
    }
    modalEl.querySelectorAll('.ag-modal-tab').forEach((t) => {
      t.classList.toggle('is-active', t.dataset.mode === (isForgot ? 'signin' : mode));
    });
    // Password field: only shown for signin. Signup + forgot-* are email-only.
    const pwField = modalEl.querySelector('.ag-field-password');
    if (pwField) pwField.style.display = isSignin ? '' : 'none';
    const pwInput = modalEl.querySelector('input[name="password"]');
    pwInput.required = isSignin;
    pwInput.setAttribute('autocomplete', isSignin ? 'current-password' : 'new-password');
    // Remember-me: only for signin.
    const rmField = modalEl.querySelector('.ag-field-remember');
    if (rmField) rmField.style.display = isSignin ? '' : 'none';
    // Forgot links cluster: only on signin.
    const links = modalEl.querySelector('.ag-modal-links');
    if (links) links.style.display = isSignin ? '' : 'none';
    modalEl.querySelector('.ag-modal-error').textContent = '';
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
  // Same shape as backend EMAIL_RE in main.py — at least 1 char before @, at least 2 chars
  // for the domain label, dot, at least 2 chars for the TLD. Catches typos like trailing
  // backslashes, missing TLDs, single-char domains.
  const EMAIL_RE = /^[^@\s]+@[^@\s.]{2,}\.[^@\s]{2,}$/;

  async function handleSubmit(form) {
    const data = new FormData(form);
    const mode = modalEl.dataset.mode;
    const email = (data.get('email') || '').toString().trim();
    const password = (data.get('password') || '').toString();
    const errEl = modalEl.querySelector('.ag-modal-error');
    errEl.textContent = '';
    if (!email) { errEl.textContent = 'Email is required.'; return; }
    if (!EMAIL_RE.test(email)) {
      errEl.textContent = "That doesn't look like a valid email. Format: name@example.com";
      return;
    }
    if (mode === 'signin' && !password) { errEl.textContent = 'Password is required to sign in.'; return; }

    const submitBtn = modalEl.querySelector('.ag-submit');
    const origLabel = submitBtn.textContent;
    submitBtn.disabled = true; submitBtn.textContent = 'Working…';

    try {
      let endpoint, payload;
      const remember = !!data.get('remember');
      if (mode === 'signup') {
        endpoint = '/api/signup'; payload = { email };
      } else if (mode === 'forgot-password') {
        endpoint = '/api/forgot-password'; payload = { email };
      } else if (mode === 'forgot-username') {
        endpoint = '/api/forgot-username'; payload = { email };
      } else {
        endpoint = '/api/signin'; payload = { email, password, remember };
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
        // signup / forgot-* — confirmation message, leave modal open.
        modalEl.querySelector('.ag-modal-title').textContent = 'Check your email';
        let confirmMsg;
        if (mode === 'signup') {
          confirmMsg = 'I just emailed ' + email + ' a setup link. Click it within 24 hours to choose a username and password.';
        } else if (mode === 'forgot-password') {
          confirmMsg = 'If an account exists for ' + email + ', I just sent a reset link plus your username. The reset link expires in 1 hour.';
        } else {
          confirmMsg = 'If an account exists for ' + email + ', I just sent your username.';
        }
        modalEl.querySelector('.ag-modal-sub').textContent = confirmMsg;
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

// =====================================================================
// Themed dialog helpers (window.AGUI) — same definitions as in realm.js so
// /awards/, /account/, and any page that loads only auth.js (no realm.js)
// also gets toast / confirmDialog / promptDialog. Last loaded wins.
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
      input.addEventListener('keydown', e => { if (e.key === 'Enter') close(input.value); });
      document.addEventListener('keydown', onKey);
      setTimeout(() => input.focus(), 50);
    });
  }
  window.AGUI = { toast: toast, confirmDialog: confirmDialog, promptDialog: promptDialog };
})();
