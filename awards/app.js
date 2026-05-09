const awardGrid = document.querySelector('#awardGrid');
const awardTemplate = document.querySelector('#awardCardTemplate');
const accordion = document.querySelector('#submissionAccordion');
const accordionTemplate = document.querySelector('#accordionTemplate');

AURORA_CONFIG.awards.forEach((award) => {
  const node = awardTemplate.content.cloneNode(true);
  node.querySelector('h3').textContent = award.title;
  node.querySelector('.award-tier').textContent = award.tier;
  node.querySelector('.award-description').textContent = award.description;
  node.querySelector('.award-meta').textContent = award.meta;
  awardGrid.appendChild(node);
});

function createField([name, label, type, required, options]) {
  const wrap = document.createElement('div');
  wrap.className = `field ${type === 'textarea' ? 'full' : ''}`;
  const labelEl = document.createElement('label');
  labelEl.textContent = label;
  labelEl.setAttribute('for', name);
  let input;
  if (type === 'textarea') {
    input = document.createElement('textarea');
  } else if (type === 'select') {
    input = document.createElement('select');
    const first = document.createElement('option');
    first.value = '';
    first.textContent = 'Choose one';
    input.appendChild(first);
    options.forEach((option) => {
      const opt = document.createElement('option');
      opt.value = option;
      opt.textContent = option;
      input.appendChild(opt);
    });
  } else {
    input = document.createElement('input');
    input.type = type;
  }
  input.name = name;
  input.id = name;
  input.required = required;
  wrap.append(labelEl, input);
  return wrap;
}

/* Open a panel: close siblings, mark this one open, scroll its top into
   the viewport so the user sees the form's first field, not the bottom of
   the previously-opened form. Hash also updates so the URL is shareable. */
function openPanel(panel, opts) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('open'));
  panel.classList.add('open');
  if (!opts || opts.scroll !== false) {
    requestAnimationFrame(() => {
      panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }
  if (panel.dataset.id) {
    history.replaceState(null, '', `#${panel.dataset.id}`);
  }
}

/* Common name-like and email-like field name patterns we'll auto-fill
   from the logged-in user's profile so applicants don't re-type basics. */
const NAME_FIELDS  = new Set(['company_name', 'creator_name', 'listing_name', 'org_name', 'name', 'brand_name']);
const EMAIL_FIELDS = new Set(['contact_email', 'email']);

/* Apply the logged-in / logged-out state to a form: toggles the gated
   visual treatment, prefills name/email fields when known. Idempotent —
   safe to call repeatedly (on init, on login, on logout). */
function applyAuthState(form) {
  const user = (window.AGAuth && AGAuth.getUser) ? AGAuth.getUser() : null;
  const submitBtn = form.querySelector('.submit-btn');
  if (user) {
    form.classList.remove('is-gated');
    if (submitBtn) submitBtn.textContent = 'Submit & Continue to Payment';
    /* Pre-fill any matching field that's currently empty. Don't overwrite
       what the user has typed; only seed empty fields. */
    form.querySelectorAll('input[name], textarea[name]').forEach((el) => {
      if (el.value) return;
      if (NAME_FIELDS.has(el.name) && user.name) el.value = user.name;
      if (EMAIL_FIELDS.has(el.name) && user.email) el.value = user.email;
    });
  } else {
    form.classList.add('is-gated');
    if (submitBtn) submitBtn.textContent = 'Sign in to submit';
  }
}

AURORA_CONFIG.submissionTypes.forEach((type, index) => {
  const node = accordionTemplate.content.cloneNode(true);
  const panel = node.querySelector('.panel');
  const button = node.querySelector('.panel-header');
  panel.dataset.id = type.id;
  node.querySelector('.panel-title').textContent = type.title;
  node.querySelector('.panel-subtitle').textContent = type.subtitle;
  node.querySelector('.panel-price').textContent = type.price;
  node.querySelector('.form-intro').textContent = type.intro;
  node.querySelector('input[name="submission_type"]').value = type.title;
  const formGrid = node.querySelector('.form-grid');
  type.fields.forEach((field) => formGrid.appendChild(createField(field)));
  const req = node.querySelector('.requirements');
  req.innerHTML = `<h4>Requirements</h4><ul>${type.requirements.map(item => `<li>${item}</li>`).join('')}</ul>`;
  button.addEventListener('click', () => openPanel(panel));

  const form = node.querySelector('form');

  /* Submit handler — gated through AGAuth.requireAuth. If logged in, runs
     immediately. If logged out, opens the auth modal; on success, re-runs
     and submits without losing form state (the closure captures form). */
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const doSubmit = () => {
      const formData = new FormData(form);
      const payload = Object.fromEntries(formData.entries());
      const user = AGAuth.getUser();
      if (user) {
        /* Attach enough profile context that the backend can resolve to
           the user record without a separate lookup. Underscore-prefixed
           keys to keep them out of the visible form data namespace. */
        payload._account_email = user.email;
        payload._account_name = user.name;
        payload._account_role = user.role || 'client';
        payload._public_slug = user.public_slug || '';
        payload._submitted_at = new Date().toISOString();
      }
      localStorage.setItem(`aurora_submission_${type.id}_${Date.now()}`, JSON.stringify(payload, null, 2));
      alert('Submission saved locally for day-one testing. Replace this with your live form endpoint and payment checkout.');
    };
    if (window.AGAuth && AGAuth.isLoggedIn && AGAuth.isLoggedIn()) {
      doSubmit();
    } else if (window.AGAuth && AGAuth.requireAuth) {
      AGAuth.requireAuth(() => {
        applyAuthState(form);   /* refresh prefill after login */
        doSubmit();
      }, { mode: 'signup' });
    } else {
      /* AGAuth not loaded — fall back to direct submit so day-one isn't blocked. */
      doSubmit();
    }
  });

  /* Gate-banner sign-in button — explicit click path that doesn't try to
     submit. Opens the auth modal directly; on success the form un-gates. */
  const gateBtn = node.querySelector('.gate-signin');
  if (gateBtn) {
    gateBtn.addEventListener('click', () => {
      if (window.AGAuth && AGAuth.showModal) {
        AGAuth.showModal({ mode: 'signup', onSuccess: () => applyAuthState(form) });
      }
    });
  }

  /* First panel default-open ONLY if no deep link is present; otherwise
     applyHashSelection (below) will choose. Don't scroll on initial render
     to avoid jumping past the hero. */
  if (index === 0 && !window.location.hash) {
    panel.classList.add('open');
  }
  accordion.appendChild(node);

  /* Apply the current auth state to this form right after it's mounted. */
  applyAuthState(form);
});

/* Whenever auth state changes (login, logout) anywhere on the page,
   re-apply the gated/prefilled treatment to every form. */
document.addEventListener('agauth:change', () => {
  document.querySelectorAll('.submission-form').forEach(applyAuthState);
});

/* Mount the auth chip in the nav slot. AGAuth handles its own re-render
   on agauth:change events, so we just install once. */
if (window.AGAuth && AGAuth.installNav) {
  const chipSlot = document.querySelector('#authChip');
  if (chipSlot) AGAuth.installNav(chipSlot);
}

/* Hash-based deep linking. URLs like /#award-entry, /#editorial-coverage,
   /#directory-listing, /#sponsor-partner open the matching panel and scroll
   its top into view. Re-evaluated on hashchange so back/forward navigation
   keeps state in sync. */
function applyHashSelection() {
  const id = window.location.hash.slice(1);
  if (!id) return;
  const target = document.querySelector(`.panel[data-id="${id}"]`);
  if (!target) return;
  openPanel(target);
}
window.addEventListener('hashchange', applyHashSelection);
applyHashSelection();

/* Fill every .year span (and the legacy #year footer id) with the
   current calendar year. Runs after award cards render so cloned
   templates' .year spans get filled. Update once a year by the
   browser clock — never by a developer. */
(function fillYear() {
  const y = new Date().getFullYear();
  document.querySelectorAll('.year').forEach((el) => { el.textContent = y; });
  const legacy = document.querySelector('#year');
  if (legacy && !legacy.textContent) legacy.textContent = y;
})();
