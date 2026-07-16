/* CareCircle – fully dynamic frontend. All data comes from Flask APIs. */
'use strict';

const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
const icon = id => `<svg><use href="#${id}"/></svg>`;
const esc = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/* ─── Toast ─────────────────────────────────────────────────────────── */
function toast(message) {
  const t = $('#toast');
  t.textContent = message;
  t.classList.add('show');
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => t.classList.remove('show'), 2800);
}

/* ─── API helper ─────────────────────────────────────────────────────── */
async function api(url, opts = {}) {
  const res = await fetch(url, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Request failed.' }));
    throw new Error(err.error || 'Request failed.');
  }
  return res.json();
}

/* ─── Chart helpers ──────────────────────────────────────────────────── */
function destroyChart(id) {
  const canvas = document.getElementById(id);
  if (!canvas) return;
  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();
}

const COLORS = ['#2e7d6b', '#4db6ac', '#8dcfc4', '#d4e9e4', '#f4b400', '#e8a838', '#b0d8d0', '#7cbcb3'];
const BASE_OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'bottom', labels: { boxWidth: 9, usePointStyle: true, font: { family: 'DM Sans', size: 11 } } },
  },
};

function makeChart(id, type, labels, values, opts = {}) {
  destroyChart(id);
  const isDoughnut = type === 'doughnut';
  const isLine = type === 'line';
  return new Chart($(`#${id}`), {
    type,
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: isDoughnut ? COLORS : (isLine ? 'transparent' : COLORS[1]),
        borderColor: '#2e7d6b',
        borderWidth: isLine ? 2 : 0,
        fill: false,
        tension: 0.35,
        borderRadius: type === 'bar' ? 5 : 0,
        borderSkipped: false,
        hoverOffset: isDoughnut ? 3 : 0,
        pointRadius: isLine ? 3 : 0,
      }],
    },
    options: {
      ...BASE_OPTS,
      ...opts,
      plugins: {
        ...BASE_OPTS.plugins,
        legend: { ...BASE_OPTS.plugins.legend, display: isDoughnut },
        ...(opts.plugins || {}),
      },
      scales: isDoughnut ? {} : {
        x: { grid: { display: false } },
        y: { grid: { color: '#edf2f1' }, ticks: { stepSize: opts.stepSize } },
      },
      cutout: isDoughnut ? '67%' : undefined,
    },
  });
}

/* ─── Stress helpers ─────────────────────────────────────────────────── */
function stressLabel(c) {
  if (c.stress_level) return c.stress_level;
  if (c.zbi != null) return c.zbi >= 61 ? 'High' : c.zbi >= 41 ? 'Moderate' : 'Low';
  return null;
}
function stressClass(c) {
  const l = stressLabel(c);
  return l ? l.toLowerCase() : '';
}
function initials(name) {
  return String(name).split(' ').map(x => x[0]).filter(Boolean).slice(0, 2).join('');
}

/* ══════════════════════════════════════════════════════════════════════
   DASHBOARD
══════════════════════════════════════════════════════════════════════ */
async function loadDashboard() {
  try {
    const data = await api('/dashboard');
    renderKpis(data);
    renderDashboardCharts(data);
    renderRecentAlerts(data);
    // Update sidebar alert badge from live data
    const upcoming = Array.isArray(data.upcoming_birthdays) ? data.upcoming_birthdays.length : 0;
    const grants   = Array.isArray(data.grant_followups_due) ? data.grant_followups_due.length : 0;
    const checkins = Array.isArray(data.monthly_checkins_due) ? data.monthly_checkins_due.length : 0;
    const badge = document.querySelector('.nav-item[data-page="alerts"] b');
    if (badge) badge.textContent = (upcoming + grants + checkins) || '';
  } catch {
    $('#kpiGrid').innerHTML = '<p class="empty-state" style="grid-column:1/-1">Could not load dashboard data.</p>';
  }
}

function renderKpis(data) {
  const total = data.total_caregivers || 0;
  if (total === 0) {
    $('#kpiGrid').innerHTML = `
      <div class="empty-state-full" style="grid-column:1/-1;text-align:center;padding:48px 24px">
        <p style="font-size:15px;margin-bottom:16px">No caregiver data found.</p>
        <button class="button" onclick="navigateTo('import')">Import Excel</button>
      </div>`;
    return;
  }
  const upcoming = Array.isArray(data.upcoming_birthdays) ? data.upcoming_birthdays.length : 0;
  const grants   = Array.isArray(data.grant_followups_due) ? data.grant_followups_due.length : 0;
  const checkins = Array.isArray(data.monthly_checkins_due) ? data.monthly_checkins_due.length : 0;
  const stress   = data.high_zbi_count ?? 0;
  const newThis  = data.new_caregivers_this_month ?? 0;
  const kpis = [
    [total,    'Total caregivers',       'i-users',    ''],
    [upcoming, 'Upcoming birthdays',     'i-calendar', 'This month'],
    [grants,   'Grant follow-ups due',   'i-bell',     grants > 0 ? `${grants} due` : ''],
    [checkins, 'Monthly check-ins due',  'i-calendar', ''],
    [stress,   'High stress caregivers', 'i-target',   stress > 0 ? 'Review needed' : ''],
    [newThis,  'New caregivers',         'i-users',    'This month'],
  ];
  $('#kpiGrid').innerHTML = kpis.map(([val, label, ico, trend]) =>
    `<article class="panel kpi-card">
      <div class="metric-icon">${icon(ico)}</div>
      <strong>${esc(val)}</strong>
      <span>${esc(label)}</span>
      ${trend ? `<em class="trend">${esc(trend)}</em>` : ''}
    </article>`
  ).join('');
}

function renderDashboardCharts(data) {
  if (!data.total_caregivers) return;
  const ag   = data.age_distribution || data.age_groups || {};
  const lang = data.language_distribution || data.languages || {};
  makeChart('ageChart', 'bar',
    ['Under 40', '40–49', '50–59', '60–69', '70+'],
    [ag.under_40 || 0, ag['40_49'] || 0, ag['50_59'] || 0, ag['60_69'] || 0, ag['70_plus'] || 0],
    { plugins: { legend: { display: false } } }
  );
  makeChart('languageChart', 'doughnut', Object.keys(lang), Object.values(lang));
}

function renderRecentAlerts(data) {
  const all = [
    ...(data.birthdays_today || []),
    ...(data.grant_followups_due || []),
    ...(data.monthly_checkins_due || []),
    ...(data.upcoming_birthdays || []),
  ].slice(0, 3);
  $('#recentAlerts').innerHTML = all.length
    ? all.map(smallAlertHtml).join('')
    : '<p class="empty-state">No alerts today.</p>';
}

/* ══════════════════════════════════════════════════════════════════════
   ALERTS
══════════════════════════════════════════════════════════════════════ */
async function loadAlerts() {
  try {
    const data = await api('/alerts');
    renderAlerts(data);
    // Refresh the alert count badge in sidebar
    const total = Object.values(data).reduce((s, arr) => s + arr.length, 0);
    const badge = document.querySelector('.nav-item[data-page="alerts"] b');
    if (badge) badge.textContent = total || '';
  } catch {
    $('#alertSections').innerHTML = '<p class="empty-state">Could not load alerts.</p>';
  }
}

function alertPriority(a) {
  if (a.type === 'grant_followup' || a.type === 'monthly_checkin') return 'high';
  if (a.type === 'birthday') return 'medium';
  return 'low';
}

function smallAlertHtml(a) {
  const c    = a.caregiver || {};
  const name = c.name || '—';
  const ini  = initials(name);
  const pri  = alertPriority(a);
  const due  = a.due_date
    ? new Date(a.due_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
    : 'Today';
  const cls  = pri === 'high' ? 'pink' : pri === 'medium' ? 'yellow' : 'teal';
  return `<div class="alert-row">
    <span class="avatar ${cls}">${esc(ini)}</span>
    <div><h3>${esc(name)}</h3><p>${esc(a.message || '')}</p></div>
    <span class="alert-date">${esc(due)}</span>
    <span class="badge ${pri}">${pri} priority</span>
    <button class="button secondary view-alert" data-id="${esc(c.id || '')}">View</button>
  </div>`;
}

function alertCardHtml(a) {
  const c    = a.caregiver || {};
  const name = c.name || '—';
  const ini  = initials(name);
  const pri  = alertPriority(a);
  const due  = a.due_date
    ? new Date(a.due_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
    : 'Today';
  return `<article class="panel alert-card">
    <div class="alert-card-head">
      <span class="badge ${pri}">${pri} priority</span>
      <button class="icon-btn">${icon('i-dots')}</button>
    </div>
    <div class="alert-person">
      <span class="avatar teal">${esc(ini)}</span>
      <div><strong>${esc(name)}</strong><span>${esc(a.message || '')}</span></div>
    </div>
    <div class="due">Due date: <strong>${esc(due)}</strong></div>
    <div class="alert-card-actions">
      <button class="button secondary view-alert" data-id="${esc(c.id || '')}">View</button>
      <button class="button secondary" data-toast="Reminder marked as completed.">Complete</button>
      <button class="button secondary" data-toast="Email composer opened.">Email</button>
      <button class="button secondary" data-toast="Call details ready.">Call</button>
    </div>
  </article>`;
}

function renderAlerts(data) {
  const groups = [
    { key: 'birthdays_today',   label: "Today's birthdays" },
    { key: 'upcoming_birthdays', label: 'Upcoming birthdays' },
    { key: 'grant_followups',   label: 'Grant follow-ups' },
    { key: 'overdue_checkins',  label: 'Monthly check-ins' },
  ];
  $('#alertSections').innerHTML = groups.map(g => {
    const items = data[g.key] || [];
    const cards = items.length
      ? items.map(alertCardHtml).join('')
      : `<p class="empty-state" style="padding:20px 0;color:var(--muted)">No ${esc(g.label.toLowerCase())} at this time.</p>`;
    return `<div class="alert-group"><h2>${esc(g.label)}</h2><div class="alert-cards">${cards}</div></div>`;
  }).join('');
}

/* ══════════════════════════════════════════════════════════════════════
   CAREGIVERS TABLE
══════════════════════════════════════════════════════════════════════ */
const cgState = { page: 1, search: '', language: '', per_page: 20 };
let _searchTimer = null;

async function loadCaregivers() {
  const params = new URLSearchParams({ page: cgState.page, per_page: cgState.per_page });
  if (cgState.search)   params.set('search',   cgState.search);
  if (cgState.language) params.set('language', cgState.language);
  try {
    const data = await api(`/caregivers?${params}`);
    renderCaregiverTable(data.items, data.pagination);
  } catch {
    $('#caregiverTable').innerHTML =
      '<tr><td colspan="9" style="text-align:center;padding:32px;color:var(--muted)">Could not load caregivers.</td></tr>';
  }
}

function caregiverRow(c) {
  const ini       = initials(c.name);
  const bday      = c.birthday
    ? new Date(c.birthday).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
    : '—';
  const langs     = Array.isArray(c.language) ? c.language.join(', ') : (c.language || '—');
  const domain    = c.situation
    ? (['Dementia', 'Mobility', 'Mental health', 'Chronic illness']
        .find(d => c.situation.toLowerCase().includes(d.toLowerCase())) || '—')
    : '—';
  const sl        = stressLabel(c);
  const sc        = stressClass(c);
  const nextCheck = c.check_when
    ? new Date(c.check_when).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
    : '—';
  return `<tr>
    <td><div class="person-cell">
      <span class="mini-avatar">${esc(ini)}</span>
      <span>${esc(c.name)}<small>${esc(c.centre || '')}</small></span>
    </div></td>
    <td>${esc(c.phone || '—')}</td>
    <td>${esc(bday)}</td>
    <td>${esc(langs)}</td>
    <td>${esc(domain)}</td>
    <td>${sl ? `<span class="stress ${sc}">${esc(sl)}</span>` : '—'}</td>
    <td>${esc(nextCheck)}</td>
    <td><span class="badge success">Active</span></td>
    <td><div class="row-actions">
      <button class="text-btn view-person" data-id="${c.id}">View</button>
      <button class="icon-btn" aria-label="More options">${icon('i-dots')}</button>
    </div></td>
  </tr>`;
}

function renderCaregiverTable(items, pagination) {
  if (!items?.length) {
    $('#caregiverTable').innerHTML =
      `<tr><td colspan="9" style="text-align:center;padding:48px;color:var(--muted)">
        No caregivers found.
        ${!cgState.search && !cgState.language ? '<br><button class="button" style="margin-top:12px" onclick="navigateTo(\'import\')">Import Excel</button>' : ''}
      </td></tr>`;
    $('#paginationInfo').textContent = 'No results';
    $('#paginationBtns').innerHTML = '';
    return;
  }
  $('#caregiverTable').innerHTML = items.map(caregiverRow).join('');
  const { page, per_page, total, pages } = pagination;
  const from = (page - 1) * per_page + 1;
  const to   = Math.min(page * per_page, total);
  $('#paginationInfo').textContent = `Showing ${from}–${to} of ${total} caregivers`;
  const start = Math.max(1, page - 2);
  const end   = Math.min(pages, page + 2);
  let btns = `<button class="page-number" ${page === 1 ? 'disabled' : ''} data-page="${page - 1}">‹</button>`;
  for (let i = start; i <= end; i++) {
    btns += `<button class="page-number ${i === page ? 'selected' : ''}" data-page="${i}">${i}</button>`;
  }
  btns += `<button class="page-number" ${page >= pages ? 'disabled' : ''} data-page="${page + 1}">›</button>`;
  $('#paginationBtns').innerHTML = btns;
}

/* ══════════════════════════════════════════════════════════════════════
   CAREGIVER PROFILE DRAWER
══════════════════════════════════════════════════════════════════════ */
async function openProfile(id) {
  if (!id) return;
  try {
    const c = await api(`/caregiver/${id}`);
    renderProfile(c);
    $('#profileDrawer').classList.add('open');
    $('#drawerBackdrop').classList.add('open');
  } catch {
    toast('Could not load caregiver profile.');
  }
}

function tagChips(items) {
  if (!items?.length) return '<span style="color:var(--muted)">—</span>';
  return items.map(t => `<span class="pill">${esc(t)}</span>`).join(' ');
}

function renderProfile(c) {
  const ini   = initials(c.name);
  const langs = Array.isArray(c.language) ? c.language : (c.language ? [c.language] : []);
  const hobbies = Array.isArray(c.hobbies) ? c.hobbies : (c.hobbies ? [c.hobbies] : []);
  const grants  = Array.isArray(c.grants)  ? c.grants  : (c.grants  ? [c.grants]  : []);
  const needs   = Array.isArray(c.needs)   ? c.needs   : (c.needs   ? [c.needs]   : []);
  const bday    = c.birthday
    ? new Date(c.birthday).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })
    : '—';
  const sl      = stressLabel(c) || '—';
  const nextChk = c.check_when
    ? new Date(c.check_when).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })
    : '—';
  $('#profileContent').innerHTML = `
    <div class="profile-hero">
      <div class="profile-avatar">${esc(ini)}</div>
      <h2>${esc(c.name)}</h2>
      <p>${esc(c.centre || '')} centre</p>
      <button class="button secondary" style="margin-top:15px" data-toast="Edit form will be available in a future update.">Edit profile</button>
    </div>
    <div class="profile-section">
      <h3>Contact details</h3>
      <div class="detail-grid">
        <div>Phone<strong>${esc(c.phone || '—')}</strong></div>
        <div>Birthday<strong>${esc(bday)}</strong></div>
        <div>Language<strong>${tagChips(langs)}</strong></div>
        <div>Centre<strong>${esc(c.centre || '—')}</strong></div>
      </div>
    </div>
    <div class="profile-section">
      <h3>Care profile</h3>
      <div class="detail-grid">
        <div>Caregiving situation<strong>${esc(c.situation || '—')}</strong></div>
        <div>Needs<strong>${tagChips(needs)}</strong></div>
        <div>Hobbies &amp; interests<strong>${tagChips(hobbies)}</strong></div>
        <div>Grants<strong>${tagChips(grants)}</strong></div>
        <div>Stress level<strong>${esc(sl)}${c.stress_score != null ? ` <em style="color:var(--muted);font-size:12px">(score: ${c.stress_score})</em>` : ''}</strong></div>
        <div>Next check-in<strong>${esc(nextChk)}</strong></div>
      </div>
    </div>
    ${c.check_what ? `<div class="profile-section"><h3>Check-in notes</h3><p style="color:var(--muted);font-size:13px;margin:0">${esc(c.check_what)}</p></div>` : ''}
    ${c.flag ? `<div class="profile-section"><h3>Flag</h3><p style="margin:0"><span class="badge high">${esc(c.flag)}</span></p></div>` : ''}`;
}

/* ══════════════════════════════════════════════════════════════════════
   IMPORT / UPLOAD
══════════════════════════════════════════════════════════════════════ */
async function loadImportPreview() {
  try {
    const data = await api('/caregivers?per_page=10&page=1&sort_by=updated_at&sort_direction=desc');
    renderImportPreview(data.items);
  } catch {
    $('#importTable').innerHTML =
      '<tr><td colspan="8" style="text-align:center;padding:32px;color:var(--muted)">No import data yet.</td></tr>';
  }
}

function renderImportPreview(items) {
  if (!items?.length) {
    $('#importTable').innerHTML =
      '<tr><td colspan="8" style="text-align:center;padding:32px;color:var(--muted)">No import data yet. Upload a file to see a preview.</td></tr>';
    return;
  }
  $('#importTable').innerHTML = items.map(c => {
    const langs   = Array.isArray(c.language) ? c.language.join(', ') : (c.language || '—');
    const hobbies = Array.isArray(c.hobbies)  ? c.hobbies.slice(0, 3).join(', ')  : (c.hobbies  || '—');
    const needs   = Array.isArray(c.needs)    ? c.needs.slice(0, 2).join(', ')    : (c.needs    || '—');
    const bday    = c.birthday
      ? new Date(c.birthday).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
      : '—';
    const domain  = c.situation
      ? (['Dementia', 'Mobility', 'Mental health', 'Chronic illness']
          .find(d => c.situation.toLowerCase().includes(d.toLowerCase())) || '—')
      : '—';
    return `<tr>
      <td>${esc(c.name)}</td>
      <td>${esc(c.phone || '—')}</td>
      <td>${esc(bday)}</td>
      <td>${esc(langs)}</td>
      <td>${esc(hobbies)}</td>
      <td>${esc(domain)}</td>
      <td>${esc(needs)}</td>
      <td><span class="badge success">Active</span></td>
    </tr>`;
  }).join('');
}

async function uploadFile(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['csv', 'xls', 'xlsx'].includes(ext)) {
    toast('Only .csv, .xls, and .xlsx files are supported.');
    return;
  }
  $('#importStatus').innerHTML = `
    <span class="file-icon">${esc(ext.toUpperCase())}</span>
    <div><strong>${esc(file.name)}</strong><p>Uploading…</p></div>`;
  const form = new FormData();
  form.append('file', file);
  try {
    const result = await api('/upload', { method: 'POST', body: form });
    const now = new Date().toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    $('#importStatus').innerHTML = `
      <span class="file-icon">${esc(ext.toUpperCase())}</span>
      <div>
        <strong>${esc(file.name)}</strong>
        <p>Imported ${esc(now)} · ${result.imported} imported, ${result.updated} updated, ${result.skipped} skipped</p>
      </div>
      <span class="badge success">Imported</span>`;
    toast(`Import complete: ${result.imported} new, ${result.updated} updated, ${result.skipped} skipped.`);
    if (result.preview?.length) renderImportPreview(result.preview);
    loadDashboard();
  } catch (e) {
    $('#importStatus').innerHTML = `
      <span class="file-icon" style="background:#e53935;color:#fff">!</span>
      <div><strong>${esc(file.name)}</strong><p style="color:#e53935">${esc(e.message)}</p></div>
      <span class="badge high">Error</span>`;
    toast(e.message);
  }
}

function initUpload() {
  const dropzone  = $('#dropzone');
  const fileInput = $('#fileInput');
  fileInput.addEventListener('change', e => {
    if (e.target.files[0]) uploadFile(e.target.files[0]);
  });
  ['dragover', 'dragenter'].forEach(x =>
    dropzone.addEventListener(x, e => { e.preventDefault(); dropzone.classList.add('dragover'); })
  );
  ['dragleave', 'drop'].forEach(x =>
    dropzone.addEventListener(x, e => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
      if (x === 'drop' && e.dataTransfer.files[0]) uploadFile(e.dataTransfer.files[0]);
    })
  );
}

/* ══════════════════════════════════════════════════════════════════════
   RECOMMENDATIONS
══════════════════════════════════════════════════════════════════════ */
function renderRecommendations(items) {
  if (!items?.length) {
    $('#recommendationsGrid').innerHTML = `
      <div style="grid-column:1/-1;text-align:center;padding:48px 24px">
        <p style="font-size:15px;color:var(--muted)">No recommendations generated yet.</p>
        <p style="font-size:13px;color:var(--muted);margin-top:8px">Fill in the workshop builder above and click Generate.</p>
      </div>`;
    return;
  }
  $('#recommendationsGrid').innerHTML = items.map(item => {
    const c       = item.caregiver;
    const ini     = initials(c.name);
    const pct     = Math.min(130, item.score);
    const stars   = Math.round((pct / 130) * 5);
    const starStr = '★'.repeat(stars) + '☆'.repeat(5 - stars);
    const langs   = Array.isArray(c.language) ? c.language.join(', ') : (c.language || '');
    const hobbies = Array.isArray(c.hobbies)  ? c.hobbies.slice(0, 2) : [];
    const age     = c.birthday
      ? new Date().getFullYear() - new Date(c.birthday).getFullYear()
      : null;
    return `<article class="panel recommend-card">
      <span class="score">${starStr}</span>
      <div class="recommend-top">
        <span class="avatar teal">${esc(ini)}</span>
        <div><h3>${esc(c.name)}</h3><p>${age ? age + ' years' : ''}${age && langs ? ' · ' : ''}${esc(langs)}</p></div>
      </div>
      ${hobbies.map(h => `<span class="pill">${esc(h)}</span>`).join('')}
      <div class="reason">
        <strong>Recommendation score ${pct}%</strong>
        ${item.reasons.map(r => `<br>${esc(r)}`).join('')}
      </div>
    </article>`;
  }).join('');
}

async function submitRecommendations(form) {
  const titleInput = form.querySelector('input:not([type="number"])');
  const selects    = form.querySelectorAll('select');
  const numInput   = form.querySelector('input[type="number"]');
  const tags       = [...form.querySelectorAll('.tag.selected')].map(t => t.textContent.trim());
  const workshop   = titleInput?.value.trim() || '';
  const language   = selects[1]?.value || selects[0]?.value || '';
  const maximum_participants = parseInt(numInput?.value) || 12;
  if (!workshop) { toast('Please enter a workshop title.'); return; }
  try {
    const result = await api('/recommendations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workshop, language, interests: tags, maximum_participants }),
    });
    renderRecommendations(result.items);
    $('#recommendCount').textContent =
      `${result.count} caregiver${result.count !== 1 ? 's' : ''} matched to your criteria`;
    toast(`${result.count} recommendation${result.count !== 1 ? 's' : ''} generated.`);
  } catch (e) {
    toast(e.message || 'Could not generate recommendations.');
  }
}

/* ══════════════════════════════════════════════════════════════════════
   ANALYTICS
══════════════════════════════════════════════════════════════════════ */
async function loadAnalytics() {
  try {
    const data = await api('/analytics');
    renderAnalytics(data);
  } catch {
    $('#analyticsGrid').innerHTML = '<p class="empty-state">Could not load analytics data.</p>';
  }
}

function renderAnalytics(data) {
  const ag     = data.age_groups || {};
  const lang   = data.language_distribution || {};
  const centre = data.centre_distribution || {};
  const inter  = data.interest_distribution || {};
  const needs  = data.needs_distribution || {};
  const bmonth = data.birthday_by_month || {};
  const stress = data.stress_distribution || {};
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  const specs = [
    { title: 'Age distribution',     type: 'bar',      labels: ['Under 40','40–49','50–59','60–69','70+'], values: [ag.under_40||0, ag['40_49']||0, ag['50_59']||0, ag['60_69']||0, ag['70_plus']||0] },
    { title: 'Languages',            type: 'doughnut', labels: Object.keys(lang),   values: Object.values(lang) },
    { title: 'Stress levels',        type: 'doughnut', labels: Object.keys(stress), values: Object.values(stress) },
    { title: 'Caregivers by centre', type: 'bar',      labels: Object.keys(centre).slice(0, 8), values: Object.values(centre).slice(0, 8) },
    { title: 'Hobbies & interests',  type: 'bar',      labels: Object.keys(inter).slice(0, 8),  values: Object.values(inter).slice(0, 8) },
    { title: 'Support needs',        type: 'doughnut', labels: Object.keys(needs).slice(0, 6),  values: Object.values(needs).slice(0, 6) },
    { title: 'Birthdays by month',   type: 'line',     labels: months, values: months.map((_, i) => bmonth[String(i + 1)] || 0) },
  ].filter(s => s.values.some(v => v > 0));

  if (!specs.length) {
    $('#analyticsGrid').innerHTML =
      '<p class="empty-state" style="grid-column:1/-1">No analytics data yet. Import caregivers first.</p>';
    return;
  }
  $('#analyticsGrid').innerHTML = specs.map((s, i) =>
    `<article class="panel analytics-card">
      <div class="panel-heading"><div><h2>${esc(s.title)}</h2><p>Current caregiver records</p></div></div>
      <div class="chart-wrap"><canvas id="aC${i}"></canvas></div>
    </article>`
  ).join('');
  specs.forEach((s, i) => makeChart(`aC${i}`, s.type, s.labels, s.values));
}

/* ══════════════════════════════════════════════════════════════════════
   NAVIGATION
══════════════════════════════════════════════════════════════════════ */
const _loaded = {};

function navigateTo(page) {
  $$('.nav-item').forEach(n => n.classList.remove('active'));
  document.querySelector(`.nav-item[data-page="${page}"]`)?.classList.add('active');
  $$('.page').forEach(p => p.classList.remove('active'));
  $(`#${page}`)?.classList.add('active');
  $('.sidebar').classList.remove('open');
  window.scrollTo(0, 0);
  if (!_loaded[page]) {
    _loaded[page] = true;
    if (page === 'caregivers')    loadCaregivers();
    else if (page === 'alerts')   loadAlerts();
    else if (page === 'analytics') loadAnalytics();
    else if (page === 'import')   loadImportPreview();
  }
}

/* ══════════════════════════════════════════════════════════════════════
   EVENT DELEGATION
══════════════════════════════════════════════════════════════════════ */
document.addEventListener('click', e => {
  const nav = e.target.closest('.nav-item[data-page]');
  if (nav) { e.preventDefault(); navigateTo(nav.dataset.page); return; }

  const go = e.target.closest('[data-go]');
  if (go) { navigateTo(go.dataset.go); return; }

  const toastBtn = e.target.closest('[data-toast]');
  if (toastBtn) { e.preventDefault(); toast(toastBtn.dataset.toast); }

  const viewPerson = e.target.closest('.view-person');
  if (viewPerson) { openProfile(viewPerson.dataset.id); return; }

  const viewAlert = e.target.closest('.view-alert');
  if (viewAlert?.dataset.id) { openProfile(viewAlert.dataset.id); return; }

  if (e.target.closest('.close-drawer') || e.target === $('#drawerBackdrop')) {
    $('#profileDrawer').classList.remove('open');
    $('#drawerBackdrop').classList.remove('open');
  }
  if (e.target.closest('.menu-btn')) $('.sidebar').classList.toggle('open');
  if (e.target.closest('.tag'))      e.target.closest('.tag').classList.toggle('selected');

  const pageBtn = e.target.closest('.page-number[data-page]');
  if (pageBtn && !pageBtn.disabled) {
    cgState.page = parseInt(pageBtn.dataset.page);
    loadCaregivers();
  }
});

$('#caregiverSearch').addEventListener('input', e => {
  clearTimeout(_searchTimer);
  _searchTimer = setTimeout(() => {
    cgState.search = e.target.value.trim();
    cgState.page = 1;
    loadCaregivers();
  }, 300);
});

document.querySelector('select[aria-label="Filter by language"]')?.addEventListener('change', e => {
  cgState.language = e.target.value === 'All languages' ? '' : e.target.value;
  cgState.page = 1;
  loadCaregivers();
});

$('#workshopForm').addEventListener('submit', e => { e.preventDefault(); submitRecommendations(e.target); });

/* ══════════════════════════════════════════════════════════════════════
   INIT
══════════════════════════════════════════════════════════════════════ */
initUpload();
loadDashboard();
renderRecommendations([]);  // show empty state on first load
