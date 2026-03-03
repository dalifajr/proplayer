/* ═══════════════════════════════════════════════════════════════════
   GitHub Edu Pro — Frontend (pywebview JS bridge)
   ═══════════════════════════════════════════════════════════════════ */

const api = () => window.pywebview && window.pywebview.api;

// ── State ────────────────────────────────────────────────────────────
let currentPage  = 'login';
let pageHistory   = [];
let benApps       = [];
let searchResults = [];
let schoolList    = [];
let selectedSess  = -1;
let tfaClipText   = '';
let tfaSavedPath  = '';
let _translations = {};
let _currentLang  = 'id';

// ── Helpers ──────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);
const $$ = (sel) => document.querySelectorAll(sel);
const esc = (s) => {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
};

async function safeClipboard(text, label = '') {
  try {
    await navigator.clipboard.writeText(text);
    toast((label ? label + ' ' : '') + 'Copied to clipboard!');
    return true;
  } catch (e) {
    await modal('Copy Manually', (label ? label + ' — ' : '') + 'Copy the text below:', { input: true, defaultValue: text });
    return false;
  }
}

// ── i18n ─────────────────────────────────────────────────────────────
function i18n(key, fallback = null) {
  return _translations[key] || fallback || key;
}

async function loadTranslations(lang = null) {
  const r = await callApi('get_translations', lang);
  if (r && r.ok) {
    _translations = r.data;
    _currentLang = lang || _currentLang;
    applyTranslations();
  }
}

function applyTranslations() {
  $$('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    if (_translations[key]) el.textContent = _translations[key];
  });
  $$('[data-i18n-placeholder]').forEach(el => {
    const key = el.dataset.i18nPlaceholder;
    if (_translations[key]) el.placeholder = _translations[key];
  });
}

// ── Loading State ────────────────────────────────────────────────────
let _loadingCount = 0;

function showLoading() {
  _loadingCount++;
  if (_loadingCount === 1) {
    $('loading-overlay').classList.remove('hidden');
    $('loading-overlay').classList.add('flex');
  }
}

function hideLoading() {
  _loadingCount = Math.max(0, _loadingCount - 1);
  if (_loadingCount === 0) {
    $('loading-overlay').classList.add('hidden');
    $('loading-overlay').classList.remove('flex');
  }
}

function callApi(method, ...args) {
  const a = api();
  if (!a) { toast(i18n('ui_error', 'pywebview not ready'), 'err'); return Promise.resolve(null); }
  return a[method](...args).then(r => JSON.parse(r));
}

// Wrapper with loading indicator for important operations
async function callApiWithLoading(method, ...args) {
  showLoading();
  try {
    return await callApi(method, ...args);
  } finally {
    hideLoading();
  }
}

// ── Form Validation ──────────────────────────────────────────────────
function validateRequired(inputId, errorMsg = null) {
  const el = $(inputId);
  if (!el) return true;
  const val = el.value.trim();
  const msg = errorMsg || i18n('ui_required_field', 'This field is required');
  if (!val) {
    setFieldError(el, msg);
    return false;
  }
  clearFieldError(el);
  return true;
}

function validateEmail(inputId) {
  const el = $(inputId);
  if (!el) return true;
  const val = el.value.trim();
  if (!val) return true; // Empty is ok, use validateRequired for empty check
  const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRe.test(val)) {
    setFieldError(el, i18n('ui_invalid_email', 'Invalid email format'));
    return false;
  }
  clearFieldError(el);
  return true;
}

function setFieldError(el, msg) {
  el.classList.add('inp-error');
  let errEl = el.nextElementSibling;
  if (!errEl || !errEl.classList.contains('field-error')) {
    errEl = document.createElement('span');
    errEl.className = 'field-error text-xs mt-0.5';
    errEl.style.color = 'var(--md-error)';
    el.parentNode.insertBefore(errEl, el.nextSibling);
  }
  errEl.textContent = msg;
}

function clearFieldError(el) {
  el.classList.remove('inp-error');
  const errEl = el.nextElementSibling;
  if (errEl && errEl.classList.contains('field-error')) {
    errEl.remove();
  }
}

function clearAllFieldErrors() {
  $$('.inp-error').forEach(el => el.classList.remove('inp-error'));
  $$('.field-error').forEach(el => el.remove());
}

function toast(msg, type = 'ok') {
  const container = $('toast-container');
  if (!container) return;

  const ICONS = { ok: '&#10003;', err: '&#10007;', warn: '&#9888;' };
  const COLORS = {
    ok:   { bg: 'var(--md-inverse-surface)',    fg: 'var(--md-inverse-on-surface)' },
    err:  { bg: 'var(--md-error)',               fg: 'var(--md-on-error)' },
    warn: { bg: '#7B5800',                       fg: '#FFFFFF' },
  };
  const { bg, fg } = COLORS[type] || COLORS.ok;
  const icon = ICONS[type] || ICONS.ok;

  const el = document.createElement('div');
  el.className = 'toast-item';
  el.style.background = bg;
  el.style.color = fg;
  el.innerHTML = `<span>${esc(msg)}</span><span class="toast-close" onclick="this.parentElement.remove()">&#10005;</span>`;

  container.prepend(el);
  requestAnimationFrame(() => requestAnimationFrame(() => el.classList.add('show')));

  clearTimeout(el._tid);
  el._tid = setTimeout(() => {
    el.classList.remove('show');
    setTimeout(() => el.remove(), 320);
  }, 3500);
}

function modal(title, body, { input = false, placeholder = '', okText = 'OK', cancelText = 'Cancel', showCancel = true } = {}) {
  return new Promise((resolve) => {
    $('modal-title').textContent = title;
    $('modal-body').textContent = body;
    const inp = $('modal-input');
    inp.value = '';
    inp.placeholder = placeholder;
    inp.classList.toggle('hidden', !input);
    $('modal-ok').textContent = okText;
    $('modal-cancel').textContent = cancelText;
    $('modal-cancel').classList.toggle('hidden', !showCancel);
    $('modal-overlay').classList.remove('hidden');
    $('modal-overlay').classList.add('flex');
    const close = (val) => {
      $('modal-overlay').classList.add('hidden');
      $('modal-overlay').classList.remove('flex');
      resolve(val);
    };
    $('modal-ok').onclick = () => close(input ? inp.value : true);
    $('modal-cancel').onclick = () => close(null);
  });
}

// ── Navigation ───────────────────────────────────────────────────────
function nav(name) {
  if (currentPage && currentPage !== name) pageHistory.push(currentPage);
  currentPage = name;
  $$('.page').forEach(p => p.classList.add('hidden'));
  const el = $('page-' + name);
  if (el) { el.classList.remove('hidden'); el.style.animation = 'none'; el.offsetHeight; el.style.animation = ''; }
  // per-page hooks
  if (name === 'sessions') refreshSessions();
  if (name === 'billing')  loadBilling();
  if (name === 'edit_profile') loadProfileForm();
  if (name === 'settings') loadSettings();
  if (name === 'auto')     { refreshSchoolDropdown(); initStepper(); }
  if (name === 'logs')     refreshLogs();
  if (name === 'history')  loadHistory();
  // toolbar
  $('btn-back').classList.toggle('hidden', name === 'login' || name === 'action');
  $('btn-logout').classList.toggle('hidden', name === 'login');
}

function goBack() {
  if (pageHistory.length) { const p = pageHistory.pop(); currentPage = null; nav(p); }
  else nav('action');
}

function doLogout() {
  modal('Logout', 'Logout and return to login page?', { okText: 'Logout' }).then(ok => {
    if (!ok) return;
    callApi('logout');
    setStatus('Not logged in', 'text-m3-primary');
    $('btn-logout').classList.add('hidden');
    pageHistory = [];
    nav('login');
  });
}

function setStatus(text, cls) {
  const s = $('status-bar');
  s.textContent = text;
  s.className = 'text-xs ' + cls;
}

// ── Stepper ──────────────────────────────────────────────────────────
const STEP_LABELS = [
  'Init', 'Profile', '2FA', 'Location', 'School',
  'Pick', 'Fill', 'Submit', 'Verify', 'Done',
];

function initStepper() {
  const container = $('stepper');
  if (!container) return;
  container.innerHTML = '';
  for (let i = 1; i <= 10; i++) {
    const item = document.createElement('div');
    item.className = 'stepper-item';
    item.id = `stp-${i}`;
    const dot = document.createElement('div');
    dot.className = 'stepper-dot';
    dot.textContent = i;
    dot.title = STEP_LABELS[i - 1] || `Step ${i}`;
    item.appendChild(dot);
    if (i < 10) {
      const line = document.createElement('div');
      line.className = 'stepper-line';
      item.appendChild(line);
    }
    container.appendChild(item);
  }
}

function updateStepper(n) {
  for (let i = 1; i <= 10; i++) {
    const item = $(`stp-${i}`);
    if (!item) continue;
    const dot  = item.querySelector('.stepper-dot');
    const line = item.querySelector('.stepper-line');
    if (!dot) continue;
    if (i < n) {
      dot.className = 'stepper-dot done';
      dot.textContent = '\u2713';
      if (line) line.className = 'stepper-line done';
    } else if (i === n) {
      dot.className = 'stepper-dot active';
      dot.textContent = i;
      if (line) line.className = 'stepper-line';
    } else {
      dot.className = 'stepper-dot';
      dot.textContent = i;
      if (line) line.className = 'stepper-line';
    }
  }
}

// ── Auth ─────────────────────────────────────────────────────────────
async function loginCookie() {
  const ck = $('inp-cookie').value.trim();
  if (!ck) return toast(i18n('ui_cookie_empty', 'Cookie is empty'), 'warn');
  setStatus(i18n('ui_loading', 'Logging in...'), 'text-m3-primary');
  showLoading();
  try {
    const r = await callApi('login_cookie', ck);
    if (!r) return;
    if (r.ok) {
      onLoginOk(r.data, ck);
    } else {
      toast(r.error, 'err');
      setStatus(i18n('ui_login_failed', 'Login failed'), 'text-m3-error');
    }
  } finally {
    hideLoading();
  }
}

async function loginPassword() {
  const u = $('inp-user').value.trim(), p = $('inp-pass').value.trim();
  if (!u || !p) return toast('Username and password required', 'warn');
  setStatus(i18n('ui_loading', 'Logging in...'), 'text-m3-primary');
  showLoading();
  try {
    const r = await callApi('login_password', u, p);
    if (!r) return;
    if (r.ok && r.data.needs_2fa) {
      hideLoading(); // Hide during modal
      const otp = await modal('2FA Required', 'Enter OTP code:', { input: true, placeholder: '123456' });
      if (!otp) return;
      setStatus('Verifying 2FA...', 'text-m3-primary');
      showLoading();
      const r2 = await callApi('submit_2fa', otp);
      if (r2 && r2.ok) onLoginOk(r2.data, null);
      else { toast(r2 ? r2.error : 'Failed', 'err'); setStatus(i18n('ui_login_failed', 'Login failed'), 'text-m3-error'); }
    } else if (r.ok) {
      onLoginOk(r.data, null);
    } else {
      toast(r.error, 'err');
      setStatus(i18n('ui_login_failed', 'Login failed'), 'text-m3-error');
    }
  } finally {
    hideLoading();
  }
}

function onLoginOk(info, cookieStr) {
  setStatus('✔ ' + (info.username || '?'), 'text-m3-tertiary');
  fillDashboard(info);
  if (cookieStr) {
    modal('Save Session', `Save session for '${info.username}'?`).then(ok => {
      if (ok) callApi('save_current_session', info.username, cookieStr);
    });
  }
  pageHistory = [];
  nav('action');
}

function fillDashboard(info) {
  $('d-user').textContent  = info.username || '—';
  $('d-name').textContent  = info.name || '—';
  $('d-email').textContent = info.email || '—';
  const age = info.age_days || 0;
  const cr  = (info.created || '').slice(0, 10);
  $('d-age').textContent = cr ? `${age} days (${cr})` : `${age} days`;
  const tfa = $('d-tfa');
  if (info.tfa) { tfa.textContent = '✅ Enabled'; tfa.className = 'info-v text-m3-tertiary'; }
  else          { tfa.textContent = '❌ Not Enabled'; tfa.className = 'info-v text-m3-error'; }
}

async function refreshDashboard() {
  setStatus('Refreshing...', 'text-m3-primary');
  const r = await callApi('get_profile');
  if (r && r.ok) { fillDashboard(r.data); setStatus('✔ ' + (r.data.username || '?') + ' (refreshed)', 'text-m3-tertiary'); }
  else toast(r ? r.error : 'Failed', 'err');
}

// ── Sessions ─────────────────────────────────────────────────────────
async function refreshSessions() {
  const r = await callApi('get_sessions');
  const list = $('sess-list');
  list.innerHTML = '';
  selectedSess = -1;
  if (!r || !r.ok || !r.data.length) { list.innerHTML = '<li class="text-m3-on-surface-v text-sm px-3 py-2">No saved sessions</li>'; return; }
  r.data.forEach((s, i) => {
    const li = document.createElement('li');
    li.className = 'list-item';
    li.textContent = `${s.label}  —  ${(s.created || '?').slice(0, 16)}`;
    li.onclick = () => { $$('#sess-list .list-item').forEach(x => x.classList.remove('active')); li.classList.add('active'); selectedSess = i; };
    list.appendChild(li);
  });
}

async function useSession() {
  if (selectedSess < 0) return toast('Select a session', 'warn');
  setStatus('Verifying...', 'text-m3-primary');
  const r = await callApi('use_session', selectedSess);
  if (r && r.ok) onLoginOk(r.data, null);
  else toast(r ? r.error : 'Session expired', 'err');
}

async function deleteSession() {
  if (selectedSess < 0) return toast('Select a session', 'warn');
  const ok = await modal('Confirm', 'Delete this session?');
  if (!ok) return;
  await callApi('delete_session', selectedSess);
  refreshSessions();
  toast('Session deleted');
}

// ── Billing ──────────────────────────────────────────────────────────
const billMap = { first_name:'bill-first', last_name:'bill-last', address1:'bill-addr1', address2:'bill-addr2',
                  city:'bill-city', region:'bill-region', postal_code:'bill-postal', country_code:'bill-country' };

async function loadBilling() {
  $('bill-status').textContent = 'Loading...';
  $('bill-status').className = 'text-sm text-m3-primary';
  const r = await callApi('get_billing');
  if (!r || !r.ok) { $('bill-status').textContent = '✘ ' + (r ? r.error : 'Error'); $('bill-status').className = 'text-sm text-m3-error'; return; }
  for (const [k, id] of Object.entries(billMap)) $(id).value = r.data[k] || '';
  const has = Object.values(r.data).some(v => v);
  $('bill-status').textContent = has ? '✔ Loaded' : '⚠ No data — fill manually';
  $('bill-status').className = 'text-sm ' + (has ? 'text-m3-tertiary' : 'text-m3-primary');
}

async function saveBilling() {
  clearAllFieldErrors();
  // Validate required fields
  let valid = true;
  valid = validateRequired('bill-country') && valid;
  valid = validateRequired('bill-postal') && valid;
  if (!valid) {
    toast(i18n('ui_validation_error', 'Please fix the errors in the form'), 'err');
    return;
  }
  
  const d = {};
  for (const [k, id] of Object.entries(billMap)) d[k] = $(id).value.trim();
  showLoading();
  try {
    const r = await callApi('save_billing', JSON.stringify(d));
    if (r && r.ok) { toast(i18n('ui_billing_saved', 'Billing saved!')); $('bill-status').textContent = '✔ Saved!'; $('bill-status').className = 'text-sm text-m3-tertiary'; }
    else toast(r ? r.error : 'Failed', 'err');
  } finally {
    hideLoading();
  }
}

// ── Edit Profile ─────────────────────────────────────────────────────
const profMap = { name:'pf-name', email:'pf-email', bio:'pf-bio', pronouns:'pf-pronouns',
                  website:'pf-website', company:'pf-company', location:'pf-location' };

async function loadProfileForm() {
  $('prof-edit-status').textContent = i18n('ui_loading', 'Loading...');
  $('prof-edit-status').className = 'text-sm text-m3-primary';
  const r = await callApi('get_profile_form');
  if (!r || !r.ok) { $('prof-edit-status').textContent = '✘ ' + (r ? r.error : 'Error'); $('prof-edit-status').className = 'text-sm text-m3-error'; return; }
  for (const [k, id] of Object.entries(profMap)) $(id).value = r.data[k] || '';
  $('prof-edit-status').textContent = '✔ Loaded';
  $('prof-edit-status').className = 'text-sm text-m3-tertiary';
  clearAllFieldErrors();
}

async function saveProfile() {
  clearAllFieldErrors();
  // Validate email format if provided
  if (!validateEmail('pf-email')) {
    toast(i18n('ui_validation_error', 'Please fix the errors in the form'), 'err');
    return;
  }
  
  const d = {};
  for (const [k, id] of Object.entries(profMap)) d[k] = $(id).value.trim();
  showLoading();
  try {
    const r = await callApi('update_profile', JSON.stringify(d));
    if (r && r.ok) { toast(i18n('ui_profile_updated', 'Profile updated!')); $('prof-edit-status').textContent = '✔ Saved'; $('prof-edit-status').className = 'text-sm text-m3-tertiary'; }
    else toast(r ? r.error : 'Failed', 'err');
  } finally {
    hideLoading();
  }
}

// ── Profile (read-only) ─────────────────────────────────────────────
async function openProfile() {
  nav('profile');
  ['p-username','p-name','p-email','p-age','p-created','p-bio','p-company','p-location','p-website','p-repos','p-followers','p-following']
    .forEach(id => $(id).textContent = 'Loading...');
  ['pb-first','pb-last','pb-addr1','pb-addr2','pb-city','pb-region','pb-postal','pb-country']
    .forEach(id => $(id).textContent = 'Loading...');
  $('p-2fa').textContent = 'Checking...';
  $('p-2fa').className = 'text-sm font-bold text-m3-on-surface-v';
  const r = await callApi('get_full_profile');
  if (!r || !r.ok) { toast(r ? r.error : 'Failed', 'err'); return; }
  const info = r.data.profile || {};
  const bill = r.data.billing || {};
  $('p-username').textContent = info.username || '—';
  $('p-name').textContent     = info.name || '—';
  $('p-email').textContent    = info.email || '—';
  $('p-age').textContent      = `${info.age_days || 0} days`;
  $('p-created').textContent  = (info.created || '—').slice(0, 10);
  $('p-bio').textContent      = info.bio || '—';
  $('p-company').textContent  = info.company || '—';
  $('p-location').textContent = info.location || '—';
  $('p-website').textContent  = info.website || '—';
  $('p-repos').textContent    = info.public_repos ?? '—';
  $('p-followers').textContent = info.followers ?? '—';
  $('p-following').textContent = info.following ?? '—';
  for (const [k, id] of Object.entries({first_name:'pb-first',last_name:'pb-last',address1:'pb-addr1',address2:'pb-addr2',city:'pb-city',region:'pb-region',postal_code:'pb-postal',country_code:'pb-country'}))
    $(id).textContent = bill[k] || '—';
  if (r.data.tfa) { $('p-2fa').textContent = '✅ Enabled'; $('p-2fa').className = 'text-sm font-bold text-m3-tertiary'; }
  else            { $('p-2fa').textContent = '❌ Not Enabled'; $('p-2fa').className = 'text-sm font-bold text-m3-error'; }
}

// ── Benefits ─────────────────────────────────────────────────────────
async function openBenefits() {
  nav('benefits');
  $('ben-summary').textContent = 'Loading...';
  $('ben-list').innerHTML = '';
  $('ben-detail').textContent = '';
  const r = await callApi('get_benefits');
  if (!r || !r.ok) { toast(r ? r.error : 'Failed', 'err'); return; }
  benApps = r.data || [];
  if (!benApps.length) { $('ben-summary').textContent = 'No applications found.'; return; }
  const ap = benApps.filter(a => /approved/i.test(a.status)).length;
  const pn = benApps.filter(a => /pending/i.test(a.status)).length;
  const rj = benApps.filter(a => /rejected|denied/i.test(a.status)).length;
  $('ben-summary').textContent = `Total: ${benApps.length}  ·  ✔ ${ap}  ·  ⏳ ${pn}  ·  ✘ ${rj}`;
  const list = $('ben-list');
  benApps.forEach((a, i) => {
    const icon = /approved/i.test(a.status) ? '✅' : (/rejected|denied/i.test(a.status) ? '❌' : '⏳');
    const li = document.createElement('li');
    li.className = 'list-item';
    li.textContent = `${icon}  #${i + 1}  ${a.status}  —  ${a.submitted || ''}`;
    li.onclick = () => showBenefitDetail(i);
    list.appendChild(li);
  });
}

function showBenefitDetail(i) {
  const a = benApps[i]; if (!a) return;
  let txt = a.status + '\n' + '='.repeat(45) + '\n\n';
  for (const [k, l] of [['submitted','Submitted'],['type','Type'],['approved_on','Date'],['expires','Expires']])
    if (a[k]) txt += `${l}: ${a[k]}\n`;
  if (a.message) txt += '\n' + '─'.repeat(45) + '\n' + a.message + '\n';
  $('ben-detail').textContent = txt;
}

// ── Search ───────────────────────────────────────────────────────────
function manualSearch() {
  const q = $('inp-search-q').value.trim();
  if (!q) return toast('Enter a keyword', 'warn');
  $('s-status').textContent = 'Searching...';
  $('s-bar').style.width = '0%';
  $('s-results').innerHTML = '';
  callApi('search_manual', q);
}

function autoSearch() {
  $('s-status').textContent = 'Searching...';
  $('s-bar').style.width = '0%';
  $('s-results').innerHTML = '';
  callApi('search_auto');
}

// Callbacks from Python
window.onSearchProgress = (i, t, q) => {
  $('s-bar').style.width = (i / t * 100) + '%';
  $('s-status').textContent = `[${i}/${t}] ${q}`;
};

window.onSearchDone = (qualified, totalFound, stopped) => {
  searchResults = qualified;
  $('s-status').textContent = 'Done!' + (stopped ? ' (stopped)' : '');
  $('s-bar').style.width = '100%';
  $('s-count').textContent = `Found: ${totalFound} | Qualified: ${qualified.length}`;
  const list = $('s-results');
  list.innerHTML = '';
  if (!qualified.length) { list.innerHTML = '<li class="text-m3-on-surface-v">No qualifying schools found.</li>'; return; }
  qualified.forEach((s, i) => {
    const li = document.createElement('li');
    li.className = 'list-item cursor-pointer';
    li.textContent = `${i + 1}. ${s.name}  (ID: ${s.id})`;
    li.onclick = () => {
      safeClipboard(`${s.name} (ID: ${s.id})`, 'School name');
      $('s-info').textContent = `✔ Copied: ${s.name}`;
      $('s-info').className = 'text-xs text-m3-tertiary mt-2';
    };
    list.appendChild(li);
  });
  $('s-info').textContent = 'Saved to daftar_sekolah.txt';
  $('s-info').className = 'text-xs text-m3-on-surface-v mt-2';
};

window.onSearchError = (msg) => {
  $('s-status').textContent = '✘ ' + msg;
  toast(msg, 'err');
};

// ── Auto Pipeline ────────────────────────────────────────────────────
async function startFullAuto() { nav('auto'); }

async function refreshSchoolDropdown() {
  const r = await callApi('get_school_list');
  const sel = $('auto-school');
  sel.innerHTML = '<option value="">⚡ Auto (random)</option>';
  schoolList = (r && r.ok) ? r.data : [];
  schoolList.forEach((s, i) => {
    const o = document.createElement('option');
    o.value = JSON.stringify(s);
    o.textContent = `${s.name}  (ID: ${s.id})`;
    sel.appendChild(o);
  });
}

async function loadDefaultCoords() {
  const r = await callApi('get_default_coords');
  if (r && r.ok) {
    $('auto-lat').value = r.data.lat || '-2.9761';
    $('auto-lon').value = r.data.lon || '104.7754';
  }
}

function runAuto() {
  $('a-log').textContent = '';
  $('a-bar').style.width = '0%';
  $('a-step').textContent = 'Starting...';
  $('a-sub').textContent = '';
  // Reset stepper
  initStepper();
  // Hide 2FA result card from previous run
  const tfaCard = $('a-tfa-result');
  if (tfaCard) { tfaCard.classList.add('hidden'); }
  const lat = $('auto-lat').value.trim();
  const lon = $('auto-lon').value.trim();
  const school = $('auto-school').value || null;
  const camFilter = $('auto-cam-filter').value || null;
  // Full auto: profile check → 2FA check/setup → pipeline (mirrors CLI flow)
  callApi('run_full_auto', lat, lon, school, camFilter);
}

window.onAutoStep = (n, t) => {
  $('a-step').textContent = `Step ${n}/10 · ${t}`;
  $('a-bar').style.width = (n / 10 * 100) + '%';  updateStepper(n);};
window.onAutoLog = (msg, tag) => {
  const box = $('a-log');
  const span = document.createElement('span');
  span.textContent = msg + '\n';
  if (tag === 'ok')    span.style.color = 'var(--md-tertiary)';
  else if (tag === 'err')  span.style.color = 'var(--md-error)';
  else if (tag === 'warn') span.style.color = '#E6A100';
  else if (tag === 'info') span.style.color = 'var(--md-primary)';
  else if (tag === 'hdr')  span.style.color = 'var(--md-primary)';
  else if (tag === 'dim')  span.style.color = 'var(--md-on-surface-variant)';
  box.appendChild(span);
  box.scrollTop = box.scrollHeight;
};
window.onAutoSub = (msg) => { $('a-sub').textContent = msg; };
window.onAutoAskExisting = async (count) => {
  const ok = await modal('School List', `Found ${count} qualifying schools in file.\n\nUse existing list?`, { okText: 'Yes', cancelText: 'No' });
  callApi('answer_existing', !!ok);
};

window.onAutoConfirmSubmit = async (info) => {
  const msg = `School : ${info.school}\nCity   : ${info.city}, ${info.region}\nCoords : ${info.lat}, ${info.lon}\n\nProceed with submission?`;
  const ok = await modal('Ready to Submit', msg, { okText: 'Submit', cancelText: 'Cancel' });
  callApi('answer_confirm_submit', !!ok);
};
// ── Status Monitor ───────────────────────────────────────────────────
let _monitorInterval = null;
let _monitorCount    = 0;
let _statusHistory   = [];    // [{time, status, sl}] newest first

window.onAutoDone = () => {
  $('a-step').textContent += ' \u2014 Done!';
  // Mark all steps as done in stepper
  updateStepper(11);  // 11 > 10, so all show as done
  toast('Auto pipeline finished');
  startMonitor();
};

function startMonitor() {
  stopMonitor();
  _monitorCount = 0;
  _statusHistory = [];
  const mon = $('a-monitor');
  if (mon) mon.classList.remove('hidden');
  pollStatus();
  _monitorInterval = setInterval(pollStatus, 7000);
}

function stopMonitor() {
  if (_monitorInterval) { clearInterval(_monitorInterval); _monitorInterval = null; }
  const mon = $('a-monitor');
  if (mon) mon.classList.add('hidden');
}

async function pollStatus() {
  _monitorCount++;
  const tick = $('a-mon-tick');
  if (tick) tick.textContent = `#${_monitorCount} · ${new Date().toLocaleTimeString()}`;
  const r = await callApi('get_app_status');
  if (!r || !r.ok || !r.data) {
    if ($('a-mon-status')) $('a-mon-status').textContent = 'No data — check again later';
    return;
  }
  const app = r.data;
  const st  = app.status || 'Unknown';
  const sl  = st.toLowerCase();
  const sts = $('a-mon-status');
  if (sts) {
    sts.textContent = st;
    sts.style.color = /approved/i.test(sl) ? 'var(--md-tertiary)'
      : /rejected|denied/i.test(sl)        ? 'var(--md-error)'
      : '#E6A100';
  }
  if ($('a-mon-submitted')) $('a-mon-submitted').textContent = app.submitted  || '—';
  if ($('a-mon-type'))      $('a-mon-type').textContent      = app.type       || '—';
  if ($('a-mon-approved'))  $('a-mon-approved').textContent  = app.approved_on|| '—';
  if ($('a-mon-expires'))   $('a-mon-expires').textContent   = app.expires    || '—';

  // ── Mini status history chart ─────────────────────────────────────
  const timeStr = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit', second:'2-digit'});
  _statusHistory.unshift({ time: timeStr, status: st, sl });
  if (_statusHistory.length > 10) _statusHistory.pop();

  const histEl = $('a-mon-history');
  if (histEl) {
    histEl.innerHTML = _statusHistory.map(ph => {
      const isApproved = /approved/i.test(ph.sl);
      const isRejected = /rejected|denied/i.test(ph.sl);
      const bg    = isApproved ? 'var(--md-tertiary)' : isRejected ? 'var(--md-error)' : '#B07800';
      const label = isApproved ? '✓' : isRejected ? '✗' : '⏳';
      return `<span class="mon-hist-dot" title="${esc(ph.time + ': ' + ph.status)}" style="background:${bg}">${label}</span>`;
    }).join('');
  }

  if (/approved|rejected|denied/i.test(sl)) {
    stopMonitor();
    toast(st, /approved/i.test(sl) ? 'ok' : 'err');
    if (window._lastInfo) fillDashboard({ ...window._lastInfo, status: st });
  }
}

window.onAutoTfaDone = (result, clipText) => {
  // Show 2FA result inline on the auto page
  const card = $('a-tfa-result');
  if (card) {
    $('a-tfa-key').textContent = result.setup_key || '—';
    const codes = result.recovery_codes || [];
    $('a-tfa-codes').textContent = codes.length
      ? codes.map((c, i) => `  ${String(i + 1).padStart(2)}. ${c}`).join('\n')
      : '(not available)';
    const fn = (result.saved_to || '').split(/[\\/]/).pop();
    $('a-tfa-file').textContent = fn ? '💾 Saved: ' + fn : '';
    card.classList.remove('hidden');
  }
  // Copy to clipboard
  if (clipText) safeClipboard(clipText, '2FA info');
  // Mirror to dashboard
  const d = $('d-tfa');
  if (d) { d.textContent = '✅ Enabled'; d.className = 'info-v text-m3-tertiary'; }
};

function stopAction() { callApi('stop'); toast('Stop signal sent', 'warn'); }

// ── 2FA ──────────────────────────────────────────────────────────────
async function openTfa() {
  nav('tfa');
  $('tfa-status').textContent = 'Checking...';
  $('tfa-status').className = 'text-sm font-bold text-m3-on-surface-v';
  $('tfa-log').textContent = '';
  const r = await callApi('check_2fa');
  if (!r || !r.ok) { toast(r ? r.error : 'Error', 'err'); return; }
  if (r.data) {
    $('tfa-status').textContent = '✅ 2FA is already enabled.';
    $('tfa-status').className = 'text-sm font-bold text-m3-tertiary';
    toast('2FA already enabled');
  } else {
    $('tfa-status').textContent = '❌ Not Enabled — Ready to setup';
    $('tfa-status').className = 'text-sm font-bold text-m3-primary';
    $('tfa-log').textContent = 'Click START SETUP to begin.\n';
  }
}

function runTfaSetup() {
  $('tfa-log').textContent = '';
  $('tfa-start-btn').disabled = true;
  $('tfa-start-btn').classList.add('opacity-50', 'pointer-events-none');
  callApi('setup_2fa');
}

window.onTfaLog = (msg) => {
  $('tfa-log').textContent += msg + '\n';
  $('tfa-log').scrollTop = $('tfa-log').scrollHeight;
};

window.onTfaDone = (result, clipText) => {
  $('tfa-start-btn').disabled = false;
  $('tfa-start-btn').classList.remove('opacity-50', 'pointer-events-none');
  $('tfa-status').textContent = '✅ 2FA Setup Complete!';
  $('tfa-status').className = 'text-sm font-bold text-m3-tertiary';
  $('d-tfa').textContent = '✅ Enabled';
  $('d-tfa').className = 'info-v text-m3-tertiary';
  $('tfa-key').textContent = 'Setup Key: ' + result.setup_key;
  const codes = result.recovery_codes || [];
  $('tfa-codes').textContent = codes.length
    ? codes.map((c, i) => `  ${String(i + 1).padStart(2)}. ${c}`).join('\n')
    : 'Recovery codes not extracted.\nCheck GitHub Settings > Security.';
  if (result.saved_to) {
    tfaSavedPath = result.saved_to;
    const fn = result.saved_to.split(/[/\\]/).pop();
    $('tfa-file').textContent = '💾 Saved: ' + fn;
    $('tfa-open-btn').classList.remove('opacity-50', 'pointer-events-none');
  }
  tfaClipText = clipText;
  safeClipboard(clipText, '2FA info').then(ok => {
    if (ok) $('tfa-copy-btn').classList.remove('hidden');
  });
  // summary in log
  $('tfa-log').textContent += '\n' + '='.repeat(45) + '\n';
  $('tfa-log').textContent += `  Setup Key : ${result.setup_key}\n`;
  if (codes.length) $('tfa-log').textContent += `  Recovery  : ${codes.length} codes saved\n`;
  $('tfa-log').textContent += '='.repeat(45) + '\n';
  $('tfa-log').textContent += '\n📋 Copied to clipboard!\n';
  $('tfa-log').scrollTop = $('tfa-log').scrollHeight;
};

window.onTfaError = (msg) => {
  $('tfa-start-btn').disabled = false;
  $('tfa-start-btn').classList.remove('opacity-50', 'pointer-events-none');
  $('tfa-status').textContent = '❌ Failed';
  $('tfa-status').className = 'text-sm font-bold text-m3-error';
  $('tfa-log').textContent += '✘ ERROR: ' + msg + '\n';
  toast(msg, 'err');
};

function openTfaFile() { if (tfaSavedPath) callApi('open_file', tfaSavedPath); }
function copyTfaClip() {
  if (tfaClipText) safeClipboard(tfaClipText, '2FA info');
}

// ── Settings ─────────────────────────────────────────────────────────
const settMap = {
  default_address:'s-address', default_city:'s-city', default_region:'s-region',
  default_postal:'s-postal', default_country:'s-country',
  default_lat:'s-lat', default_lon:'s-lon',
  document_label:'s-doclabel', search_delay:'s-delay', id_validity_days:'s-validity'
};

async function loadSettings() {
  const r = await callApi('get_settings');
  if (!r || !r.ok) return;
  for (const [k, id] of Object.entries(settMap)) $(id).value = r.data[k] || '';
  const theme = r.data.theme || 'dark';
  document.querySelector(`input[name="theme"][value="${theme}"]`).checked = true;
  applyTheme(theme);  const lang = r.data.language || 'id';
  const langRadio = document.querySelector(`input[name="language"][value="${lang}"]`);
  if (langRadio) langRadio.checked = true;  $('sett-status').textContent = '✔ Settings loaded';
  $('sett-status').className = 'text-sm text-m3-tertiary';
  refreshFileInfo();
}

async function saveSettings() {
  const cfg = {};
  for (const [k, id] of Object.entries(settMap)) cfg[k] = $(id).value.trim();
  const theme = document.querySelector('input[name="theme"]:checked').value;
  cfg.theme = theme;
  const language = document.querySelector('input[name="language"]:checked');
  const newLang = language ? language.value : 'id';
  cfg.language = newLang;
  cfg.ua_rotate = true;
  
  showLoading();
  try {
    const r = await callApi('save_settings', JSON.stringify(cfg));
    if (r && r.ok) {
      toast(i18n('ui_settings_saved', 'Settings saved!'));
      $('sett-status').textContent = '✔ Settings saved!';
      $('sett-status').className = 'text-sm text-m3-tertiary';
      applyTheme(theme);
      // Reload translations if language changed
      if (newLang !== _currentLang) {
        await loadTranslations(newLang);
        await callApi('set_language', newLang);
      }
    } else toast(r ? r.error : 'Failed', 'err');
  } finally {
    hideLoading();
  }
}

function applyTheme(theme) {
  if (theme === 'dark') {
    document.documentElement.classList.add('dark');
    $('btn-theme').innerHTML = '&#127769;'; // Moon for dark
  } else {
    document.documentElement.classList.remove('dark');
    $('btn-theme').innerHTML = '&#9728;'; // Sun for light
  }
}

function toggleTheme() {
  const isDark = document.documentElement.classList.contains('dark');
  const newTheme = isDark ? 'light' : 'dark';
  applyTheme(newTheme);
  // Save preference
  callApi('get_settings').then(r => {
    if (r && r.ok) {
      const cfg = r.data;
      cfg.theme = newTheme;
      callApi('save_settings', JSON.stringify(cfg));
    }
  });
  // Update settings page radio if visible
  const radio = document.querySelector(`input[name="theme"][value="${newTheme}"]`);
  if (radio) radio.checked = true;
}

// theme radio -> live preview
document.addEventListener('change', e => {
  if (e.target.name === 'theme') applyTheme(e.target.value);
});

// ── File Upload ──────────────────────────────────────────────────────
async function refreshFileInfo() {
  const r = await callApi('get_file_info');
  if (!r || !r.ok) return;
  const d = r.data;
  $('file-school-info').textContent = d.school_exists
    ? `✔ ${d.school_count} qualified school(s) loaded`
    : '⚠ No school list file found';
  $('file-school-info').className = 'text-xs mb-1.5 ' + (d.school_exists ? 'text-m3-tertiary' : 'text-m3-primary');
  $('file-kw-info').textContent = d.kw_exists
    ? `✔ ${d.kw_count} keyword(s) loaded`
    : `ℹ Using ${d.kw_count} built-in keywords`;
  $('file-kw-info').className = 'text-xs mb-1.5 ' + (d.kw_exists ? 'text-m3-tertiary' : 'text-m3-on-surface-v');
}

async function uploadSchoolList() {
  const r = await callApi('upload_school_list');
  if (!r || !r.ok) { toast(r ? r.error : 'Failed', 'err'); return; }
  if (!r.data.uploaded) return; // user cancelled
  toast(`School list uploaded! (${r.data.count} qualified)`);
  refreshFileInfo();
}

async function uploadKeywords() {
  const r = await callApi('upload_keywords');
  if (!r || !r.ok) { toast(r ? r.error : 'Failed', 'err'); return; }
  if (!r.data.uploaded) return;
  toast(`Keywords uploaded! (${r.data.count} keywords)`);
  refreshFileInfo();
}

// ── Logs ─────────────────────────────────────────────────────────────
async function refreshLogs() {
  const r = await callApi('get_log');
  $('log-box').textContent = (r && r.ok) ? r.data : '';
  $('log-box').scrollTop = $('log-box').scrollHeight;
}

async function clearLogs() {
  const ok = await modal('Clear Log', 'Clear the log file?');
  if (ok) { await callApi('clear_log'); refreshLogs(); toast('Log cleared'); }
}

// ── Submission History ───────────────────────────────────────────────
async function loadHistory() {
  const sumEl  = $('hist-summary');
  const listEl = $('hist-list');
  const detEl  = $('hist-detail');
  if (sumEl)  sumEl.textContent  = 'Loading...';
  if (listEl) listEl.innerHTML   = '';
  if (detEl)  detEl.textContent  = '';
  const r = await callApi('get_history');
  if (!r || !r.ok) { if (sumEl) sumEl.textContent = '✘ Error loading history'; return; }
  const entries = (r.data || []).slice().reverse();     // newest first
  if (sumEl) sumEl.textContent = `Total: ${entries.length} submission(s)`;
  if (!entries.length) {
    if (listEl) listEl.innerHTML = '<li class="text-xs px-2 py-1" style="color:var(--md-outline);">No history yet.</li>';
    return;
  }
  entries.forEach((e, idx) => {
    const li  = document.createElement('li');
    li.className = 'list-item cursor-pointer text-xs';
    const icon = /approved/i.test(e.status || '') ? '✅'
               : /pending/i.test(e.status  || '') ? '⏳' : '📝';
    li.textContent = `${icon}  ${e.submitted_at || '?'} · @${e.username || '?'} · ${e.school || '?'} (${e.status || 'submitted'})`;
    li.onclick = () => {
      if (detEl) detEl.textContent = JSON.stringify(e, null, 2);
    };
    if (listEl) listEl.appendChild(li);
  });
}

async function clearHistory() {
  const ok = await modal('Clear History', 'Delete all submission history? This cannot be undone.');
  if (!ok) return;
  await callApi('clear_history');
  toast('History cleared');
  loadHistory();
}

// ── Init (wait for pywebview ready) ──────────────────────────────────
window.addEventListener('pywebviewready', () => {
  loadDefaultCoords();
  // load settings (theme, language)
  callApi('get_settings').then(r => {
    if (r && r.ok) {
      if (r.data.theme) applyTheme(r.data.theme);
      // Load translations for the configured language
      const lang = r.data.language || 'id';
      loadTranslations(lang);
    } else {
      // Default to Indonesian if settings fail
      loadTranslations('id');
    }
  });
});
