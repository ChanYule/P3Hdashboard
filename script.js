/* CareCircle – fully dynamic frontend. All data comes from Flask APIs. */
'use strict';

const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
const icon = id => `<svg><use href="#${id}"/></svg>`;
const esc = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/* ─── Toast ─────────────────────────────────────────────────────────── */
function toast(message, type = 'info') {
  const t = $('#toast');
  t.textContent = message;
  t.classList.add('show');
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => t.classList.remove('show'), 3000);
}

/* ─── API helper ─────────────────────────────────────────────────────── */
async function api(url, opts = {}) {
  const res = await fetch(url, opts);
  if (res.status === 401) {
    const data = await res.json().catch(() => ({}));
    if (data.redirect) { location.href = data.redirect; }
    throw new Error(data.error || 'Authentication required.');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Request failed.' }));
    throw new Error(err.error || 'Request failed.');
  }
  return res.json();
}

/* ─── Auth guard on load ─────────────────────────────────────────────── */
let _currentUser = null;

async function initApp() {
  try {
    _currentUser = await api('/auth/me');
    renderSidebarUser(_currentUser);
    renderDashboardGreeting(_currentUser);
    startClock();
    loadDashboard();
    renderRecommendations([]);
  } catch {
    location.href = '/login.html';
  }
}

function renderSidebarUser(user) {
  const ini = initials(user.full_name);
  if ($('#sidebarAvatar')) $('#sidebarAvatar').textContent = ini;
  if ($('#sidebarName'))   $('#sidebarName').textContent   = user.full_name;
  if ($('#sidebarRole'))   $('#sidebarRole').textContent   = user.role;
  if ($('#topAvatar'))     $('#topAvatar').textContent     = ini;
}

function renderDashboardGreeting(user) {
  const hour = new Date().getHours();
  const greet = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  const firstName = user.full_name.split(' ')[0];
  if ($('#dashGreeting')) $('#dashGreeting').textContent = `${greet}, ${firstName}`;
  if ($('#dashDate')) {
    $('#dashDate').textContent = new Date().toLocaleDateString('en-GB', {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
    }).toUpperCase();
  }
}

/* ─── Live clock ─────────────────────────────────────────────────────── */
function startClock() {
  function tick() {
    const el = $('#dashTime');
    if (el) {
      el.textContent = new Date().toLocaleTimeString('en-GB', {
        hour: '2-digit', minute: '2-digit'
      });
    }
  }
  tick();
  setInterval(tick, 30000);
}

/* ─── Keyboard shortcut: Cmd/Ctrl+K focuses search ──────────────────── */
document.addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault();
    const input = $('#globalSearchInput') || $('#caregiverSearch');
    if (input) { input.focus(); input.select(); }
  }
});

/* Global search: navigate to caregivers with query */
$('#globalSearchInput')?.addEventListener('input', e => {
  const q = e.target.value.trim();
  if (q.length > 1) {
    navigateTo('caregivers');
    const cgInput = $('#caregiverSearch');
    if (cgInput) {
      cgInput.value = q;
      cgInput.dispatchEvent(new Event('input'));
    }
  }
});

/* ─── Chart helpers ──────────────────────────────────────────────────── */
function destroyChart(id) {
  const canvas = document.getElementById(id);
  if (!canvas) return;
  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();
}

const COLORS = [
  '#2e7d6b','#4db6ac','#8dcfc4','#d4e9e4',
  '#f4b400','#e8a838','#b0d8d0','#7cbcb3','#a8d5cc','#c9e8e4'
];

const BASE_OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'bottom',
      labels: {
        boxWidth: 9,
        usePointStyle: true,
        padding: 16,
        font: { family: 'DM Sans', size: 11 },
      },
    },
    tooltip: {
      backgroundColor: '#173b33',
      titleFont: { family: 'Manrope', size: 12, weight: '700' },
      bodyFont:  { family: 'DM Sans', size: 11 },
      padding: 10,
      cornerRadius: 8,
      callbacks: {
        label: ctx => {
          const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
          const pct   = total ? Math.round((ctx.parsed / total) * 100) : 0;
          return ` ${ctx.parsed}  (${pct}%)`;
        }
      }
    },
  },
};

function makeChart(id, type, labels, values, opts = {}) {
  destroyChart(id);
  const isDoughnut = type === 'doughnut';
  const isLine     = type === 'line';
  return new Chart($(`#${id}`), {
    type,
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: isDoughnut ? COLORS : (isLine ? 'rgba(46,125,107,.08)' : COLORS[0]),
        borderColor: '#2e7d6b',
        borderWidth: isLine ? 2 : (isDoughnut ? 0 : 0),
        fill: isLine,
        tension: 0.38,
        borderRadius: type === 'bar' ? 6 : 0,
        borderSkipped: false,
        hoverOffset: isDoughnut ? 4 : 0,
        pointRadius: isLine ? 4 : 0,
        pointBackgroundColor: '#2e7d6b',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
      }],
    },
    options: {
      ...BASE_OPTS,
      ...opts,
      plugins: {
        ...BASE_OPTS.plugins,
        legend: {
          ...BASE_OPTS.plugins.legend,
          display: isDoughnut,
        },
        ...(opts.plugins || {}),
        tooltip: { ...BASE_OPTS.plugins.tooltip, ...(opts.plugins?.tooltip || {}) },
      },
      scales: isDoughnut ? {} : {
        x: {
          grid: { display: false },
          ticks: { font: { family: 'DM Sans', size: 10 } },
        },
        y: {
          grid: { color: '#edf2f1', drawBorder: false },
          ticks: { font: { family: 'DM Sans', size: 10 }, stepSize: opts.stepSize },
          beginAtZero: true,
        },
      },
      cutout: isDoughnut ? '68%' : undefined,
    },
  });
}

/* ─── Stress helpers ─────────────────────────────────────────────────── */
function stressLabel(c) {
  if (c.stress_level) return c.stress_level;
  if (c.zbi != null) return c.zbi >= 61 ? 'High' : c.zbi >= 41 ? 'Moderate' : 'Low';
  return null;
}
function stressClass(c) { const l = stressLabel(c); return l ? l.toLowerCase() : ''; }
function initials(name) {
  return String(name).split(' ').map(x => x[0]).filter(Boolean).slice(0, 2).join('').toUpperCase();
}

/* ══════════════════════════════════════════════════════════════════════
   DASHBOARD
══════════════════════════════════════════════════════════════════════ */
async function loadDashboard() {
  try {
    const data = await api('/dashboard');
    renderKpis(data);
    renderTodaysPriorities(data);
    renderDashboardCharts(data);
    renderRecentAlerts(data);

    // Update last-import display
    if (data.last_import_at) {
      const el = $('#dashLastImport');
      if (el) {
        el.textContent = new Date(data.last_import_at).toLocaleDateString('en-GB', {
          day: 'numeric', month: 'short', year: 'numeric'
        });
      }
    }

    // Update sidebar alert badge
    const upcoming    = Array.isArray(data.upcoming_birthdays)   ? data.upcoming_birthdays.length   : 0;
    const grants      = Array.isArray(data.grant_followups_due)  ? data.grant_followups_due.length  : 0;
    const checkins    = Array.isArray(data.monthly_checkins_due) ? data.monthly_checkins_due.length : 0;
    const grantChecks = Array.isArray(data.grant_checks_due)     ? data.grant_checks_due.length     : 0;
    const badge = $('#alertBadge');
    if (badge) badge.textContent = (upcoming + grants + checkins + grantChecks) || '';
  } catch {
    if ($('#kpiGrid'))
      $('#kpiGrid').innerHTML = emptyStateFull('i-activity', 'Could not load dashboard', 'Check that the server is running and try refreshing.', '');
    if ($('#prioritiesGrid')) $('#prioritiesGrid').innerHTML = '';
  }
}

/* ── KPI cards ───────────────────────────────────────────────────────── */
function renderKpis(data) {
  const total = data.total_caregivers || 0;
  if (total === 0) {
    $('#kpiGrid').innerHTML = `
      <div style="grid-column:1/-1">
        ${emptyStateFull('i-users', 'No caregiver data yet', 'Import an Excel or CSV file to get started.', `<button class="button" onclick="navigateTo('import')">${icon('i-upload')} Import data</button>`)}
      </div>`;
    return;
  }
  const upcoming   = Array.isArray(data.upcoming_birthdays)   ? data.upcoming_birthdays.length   : 0;
  const grants     = Array.isArray(data.grant_followups_due)  ? data.grant_followups_due.length  : 0;
  const checkins   = Array.isArray(data.monthly_checkins_due) ? data.monthly_checkins_due.length : 0;
  const highStress = data.high_stress_count ?? data.high_zbi_count ?? 0;
  const newThis    = data.new_caregivers_this_month ?? 0;

  const kpis = [
    { val: total,     label: 'Total caregivers',      icon: 'i-users',    trend: newThis > 0 ? `+${newThis} this month` : null,        cls: '' },
    { val: upcoming,  label: 'Upcoming birthdays',    icon: 'i-calendar', trend: 'This month',                                         cls: '' },
    { val: grants,    label: 'Grant follow-ups due',  icon: 'i-bell',     trend: grants  > 0 ? `${grants} due`    : 'All clear',       cls: grants  > 0 ? 'warn' : '' },
    { val: checkins,  label: 'Monthly check-ins due', icon: 'i-clock',    trend: checkins > 0 ? `${checkins} pending` : 'All clear',   cls: checkins > 0 ? 'warn' : '' },
    { val: highStress,label: 'High stress caregivers',icon: 'i-activity', trend: highStress > 0 ? 'Review needed' : 'Within range',    cls: highStress > 0 ? 'warn' : '' },
    { val: newThis,   label: 'New caregivers',        icon: 'i-trending', trend: 'This month',                                         cls: '' },
  ];
  $('#kpiGrid').innerHTML = kpis.map(k =>
    `<article class="panel kpi-card">
      <div class="metric-icon">${icon(k.icon)}</div>
      <strong>${esc(k.val)}</strong>
      <span>${esc(k.label)}</span>
      ${k.trend ? `<em class="trend ${k.cls}">${esc(k.trend)}</em>` : ''}
    </article>`
  ).join('');
}

/* ── Today's priorities ──────────────────────────────────────────────── */
function renderTodaysPriorities(data) {
  const el = $('#prioritiesGrid');
  if (!el) return;

  const birthdaysToday = data.birthdays_today     || [];
  const grantsDue      = data.grant_followups_due || data.grant_checks_due || [];
  const checkinsDue    = data.monthly_checkins_due || data.overdue_checkins || [];
  const highStress     = data.high_stress_count ?? 0;
  const upcoming       = data.upcoming_birthdays || [];

  const cards = [];

  // Birthdays today (urgent)
  const bClass = birthdaysToday.length > 0 ? 'urgent' : '';
  const bNames = birthdaysToday.slice(0, 3).map(a => (a.caregiver?.name || '—')).join(', ');
  cards.push(`
    <article class="panel priority-card ${bClass}">
      <div class="priority-card-head">
        <div class="priority-card-icon">${icon('i-calendar')}</div>
        <h3>Birthdays today</h3>
      </div>
      <span class="priority-count">${birthdaysToday.length}</span>
      <span class="priority-label">caregiver${birthdaysToday.length !== 1 ? 's' : ''} celebrating today</span>
      ${bNames ? `<p class="priority-names">${esc(bNames)}${birthdaysToday.length > 3 ? ` +${birthdaysToday.length - 3} more` : ''}</p>` : '<p class="priority-names" style="color:var(--muted)">No birthdays today</p>'}
      <div class="priority-card-actions">
        <button class="button secondary" data-go="alerts">View</button>
        ${birthdaysToday.length > 0 ? `<button class="button" data-toast="Opening birthday messages…">${icon('i-bell')} Notify</button>` : ''}
      </div>
    </article>`);

  // Grant follow-ups (warning if any)
  const gClass = grantsDue.length > 0 ? 'warning' : '';
  const gNames = grantsDue.slice(0, 3).map(a => (a.caregiver?.name || '—')).join(', ');
  cards.push(`
    <article class="panel priority-card ${gClass}">
      <div class="priority-card-head">
        <div class="priority-card-icon">${icon('i-target')}</div>
        <h3>Grant follow-ups</h3>
      </div>
      <span class="priority-count">${grantsDue.length}</span>
      <span class="priority-label">follow-up${grantsDue.length !== 1 ? 's' : ''} pending</span>
      ${gNames ? `<p class="priority-names">${esc(gNames)}${grantsDue.length > 3 ? ` +${grantsDue.length - 3} more` : ''}</p>` : '<p class="priority-names" style="color:var(--muted)">No follow-ups due</p>'}
      <div class="priority-card-actions">
        <button class="button secondary" data-go="alerts">View</button>
      </div>
    </article>`);

  // Monthly check-ins (warning if any)
  const cClass = checkinsDue.length > 0 ? 'warning' : '';
  const cNames = checkinsDue.slice(0, 3).map(a => (a.caregiver?.name || '—')).join(', ');
  cards.push(`
    <article class="panel priority-card ${cClass}">
      <div class="priority-card-head">
        <div class="priority-card-icon">${icon('i-check')}</div>
        <h3>Monthly check-ins</h3>
      </div>
      <span class="priority-count">${checkinsDue.length}</span>
      <span class="priority-label">check-in${checkinsDue.length !== 1 ? 's' : ''} due</span>
      ${cNames ? `<p class="priority-names">${esc(cNames)}${checkinsDue.length > 3 ? ` +${checkinsDue.length - 3} more` : ''}</p>` : '<p class="priority-names" style="color:var(--muted)">No check-ins due</p>'}
      <div class="priority-card-actions">
        <button class="button secondary" data-go="alerts">View</button>
      </div>
    </article>`);

  el.innerHTML = cards.join('');
}

/* ── Charts ──────────────────────────────────────────────────────────── */
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
  renderStressBreakdown(data);
}

function renderStressBreakdown(data) {
  const panel = $('#stressPanel');
  const el    = $('#stressBreakdown');
  if (!panel || !el) return;
  const high  = data.high_stress_count     ?? 0;
  const mod   = data.moderate_stress_count ?? 0;
  const low   = data.low_stress_count      ?? 0;
  const total = high + mod + low;
  if (total === 0) { panel.style.display = 'none'; return; }
  panel.style.display = '';
  const pct = n => total ? Math.round((n / total) * 100) : 0;
  const bar = (n, cls, label) => `
    <div class="stress-bar-row">
      <span class="stress-bar-label">${label}</span>
      <div class="stress-bar-track">
        <div class="stress-bar-fill ${cls}" style="width:${pct(n)}%"></div>
      </div>
      <span class="stress-bar-count">
        <strong>${n}</strong>
        <em>${pct(n)}%</em>
      </span>
    </div>`;
  el.innerHTML = `
    <div class="stress-summary">
      ${bar(high, 'high',     'High')}
      ${bar(mod,  'moderate', 'Moderate')}
      ${bar(low,  'low',      'Low')}
    </div>
    <p class="stress-footnote">${total} of ${data.total_caregivers ?? total} caregivers assessed · scores from ZBI column</p>`;
}

/* ── Recent alerts ───────────────────────────────────────────────────── */
function renderRecentAlerts(data) {
  const all = [
    ...(data.birthdays_today       || []),
    ...(data.grant_checks_due      || []),
    ...(data.grant_followups_due   || []),
    ...(data.monthly_checkins_due  || []),
    ...(data.upcoming_birthdays    || []),
  ].slice(0, 4);
  $('#recentAlerts').innerHTML = all.length
    ? all.map(smallAlertHtml).join('')
    : `<div style="padding:28px 0;text-align:center;color:var(--muted)">
        ${icon('i-check')} No alerts today — you're all caught up.
       </div>`;
}

/* ══════════════════════════════════════════════════════════════════════
   ALERTS
══════════════════════════════════════════════════════════════════════ */
async function loadAlerts() {
  const container = $('#alertSections');
  if (container) container.innerHTML = '<div style="padding:32px 0;color:var(--muted);text-align:center">Loading alerts…</div>';
  try {
    const data = await api('/alerts');
    renderAlerts(data);
    const total = Object.values(data).reduce((s, arr) => Array.isArray(arr) ? s + arr.length : s, 0);
    const badge = $('#alertBadge');
    if (badge) badge.textContent = total || '';
  } catch {
    if ($('#alertSections'))
      $('#alertSections').innerHTML = emptyStateFull('i-bell', 'Could not load alerts', 'Please refresh the page and try again.', '');
  }
}

function alertPriority(a) {
  if (a.type === 'grant_followup' || a.type === 'monthly_checkin' || a.type === 'grant_check') return 'high';
  if (a.type === 'birthday' || a.type === 'upcoming_birthday') return 'medium';
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
    <span class="badge ${pri}">${pri === 'high' ? 'Urgent' : pri === 'medium' ? 'Soon' : 'Low'}</span>
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
  const avatarCls = pri === 'high' ? 'pink' : pri === 'medium' ? 'yellow' : 'teal';
  return `<article class="panel alert-card">
    <div class="alert-card-head">
      <span class="badge ${pri}">${pri === 'high' ? 'Urgent' : pri === 'medium' ? 'Upcoming' : 'Low'}</span>
      <button class="icon-btn" aria-label="More options">${icon('i-dots')}</button>
    </div>
    <div class="alert-person">
      <span class="avatar ${avatarCls}">${esc(ini)}</span>
      <div><strong>${esc(name)}</strong><span>${esc(a.message || '')}</span></div>
    </div>
    <div class="due">Due: <strong>${esc(due)}</strong></div>
    <div class="alert-card-actions">
      <button class="button secondary view-alert" data-id="${esc(c.id || '')}">View profile</button>
      <button class="button secondary" data-toast="Marked as completed.">Complete</button>
      <button class="button secondary" data-toast="Email composer opened.">Email</button>
      <button class="button secondary" data-toast="Call details ready.">Call</button>
    </div>
  </article>`;
}

function renderAlerts(data) {
  const groups = [
    { key: 'birthdays_today',    label: "Today's birthdays",   urgent: true  },
    { key: 'upcoming_birthdays', label: 'Upcoming birthdays',  urgent: false },
    { key: 'grant_checks',       label: 'Grant check dates',   urgent: false },
    { key: 'grant_followups',    label: 'Grant follow-ups',    urgent: true  },
    { key: 'overdue_checkins',   label: 'Monthly check-ins',   urgent: true  },
  ];
  $('#alertSections').innerHTML = groups.map(g => {
    const items = data[g.key] || [];
    const cards = items.length
      ? items.map(alertCardHtml).join('')
      : `<div style="padding:28px 0;color:var(--muted);font-size:13px">
           No ${esc(g.label.toLowerCase())} at this time — all clear.
         </div>`;
    const countBadge = items.length
      ? `<span class="badge ${g.urgent ? 'high' : 'neutral'}" style="margin-left:10px">${items.length}</span>`
      : '';
    return `<div class="alert-group">
      <div class="alert-group-header">
        <h2>${esc(g.label)}${countBadge}</h2>
      </div>
      <div class="alert-cards">${cards}</div>
    </div>`;
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

  // Show skeleton while loading
  const tbody = $('#caregiverTable');
  if (tbody && !cgState.search) {
    tbody.innerHTML = Array(5).fill(0).map(() => `
      <tr>${Array(10).fill(0).map(() =>
        `<td><span class="skeleton" style="display:block;height:14px;width:80%;border-radius:4px">&nbsp;</span></td>`
      ).join('')}</tr>`).join('');
  }

  try {
    const data = await api(`/caregivers?${params}`);
    renderCaregiverTable(data.items, data.pagination);
  } catch {
    if (tbody)
      tbody.innerHTML = `<tr><td colspan="10" style="text-align:center;padding:40px;color:var(--muted)">
        ${icon('i-activity')} Could not load caregivers. Please refresh.
      </td></tr>`;
  }
}

function caregiverRow(c) {
  const ini    = initials(c.name);
  const bday   = c.birthday
    ? new Date(c.birthday).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
    : '—';
  const langs  = Array.isArray(c.language) ? c.language.join(', ') : (c.language || '—');
  const domain = c.situation
    ? (['Dementia','Mobility','Mental health','Chronic illness']
        .find(d => c.situation.toLowerCase().includes(d.toLowerCase())) || '—')
    : '—';
  const sl    = stressLabel(c);
  const sc    = stressClass(c);
  const nextChk = c.check_when
    ? new Date(c.check_when).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
    : '—';
  const avatarColors = ['teal', 'pink', 'yellow'];
  const avatarCls = avatarColors[Math.abs(c.name.charCodeAt(0)) % avatarColors.length];
  return `<tr>
    <td><div class="person-cell">
      <span class="mini-avatar ${avatarCls}">${esc(ini)}</span>
      <span>${esc(c.name)}<small>${esc(c.centre || '')}</small></span>
    </div></td>
    <td>${esc(c.phone || '—')}</td>
    <td>${esc(bday)}</td>
    <td>${esc(langs)}</td>
    <td>${esc(domain)}</td>
    <td>${sl ? `<span class="stress ${sc}">${esc(sl)}</span>` : '—'}</td>
    <td>${c.stress_score != null ? `<span class="zbi-score">${esc(c.stress_score)}</span>` : '—'}</td>
    <td>${esc(nextChk)}</td>
    <td><span class="badge success">Active</span></td>
    <td><div class="row-actions">
      <button class="text-btn view-person" data-id="${c.id}">View</button>
      <button class="icon-btn" aria-label="More">${icon('i-dots')}</button>
    </div></td>
  </tr>`;
}

function renderCaregiverTable(items, pagination) {
  if (!items?.length) {
    $('#caregiverTable').innerHTML = `<tr><td colspan="10">
      ${emptyStateFull('i-users',
        cgState.search ? 'No results found' : 'No caregivers yet',
        cgState.search ? `No caregivers match "${esc(cgState.search)}"` : 'Import an Excel or CSV file to get started.',
        !cgState.search && !cgState.language
          ? `<button class="button" onclick="navigateTo('import')">${icon('i-upload')} Import data</button>`
          : ''
      )}
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
  for (let i = start; i <= end; i++)
    btns += `<button class="page-number ${i === page ? 'selected' : ''}" data-page="${i}">${i}</button>`;
  btns += `<button class="page-number" ${page >= pages ? 'disabled' : ''} data-page="${page + 1}">›</button>`;
  $('#paginationBtns').innerHTML = btns;
}

/* ══════════════════════════════════════════════════════════════════════
   CAREGIVER PROFILE DRAWER
══════════════════════════════════════════════════════════════════════ */
async function openProfile(id) {
  if (!id) return;
  const drawer = $('#profileDrawer');
  const content = $('#profileContent');
  if (content) content.innerHTML = `<div style="padding:60px 0;text-align:center;color:var(--muted)">Loading profile…</div>`;
  drawer?.classList.add('open');
  $('#drawerBackdrop')?.classList.add('open');
  try {
    const c = await api(`/caregiver/${id}`);
    renderProfile(c);
  } catch {
    if (content) content.innerHTML = `<div style="padding:60px 0;text-align:center;color:var(--muted)">Could not load profile.</div>`;
    toast('Could not load caregiver profile.');
  }
}

function tagChips(items) {
  if (!items?.length) return '<span style="color:var(--muted)">—</span>';
  return items.map(t => `<span class="pill">${esc(t)}</span>`).join(' ');
}

function renderProfile(c) {
  const ini     = initials(c.name);
  const langs   = Array.isArray(c.language) ? c.language : (c.language ? [c.language] : []);
  const hobbies = Array.isArray(c.hobbies)  ? c.hobbies  : (c.hobbies  ? [c.hobbies]  : []);
  const grants  = Array.isArray(c.grants)   ? c.grants   : (c.grants   ? [c.grants]   : []);
  const needs   = Array.isArray(c.needs)    ? c.needs    : (c.needs    ? [c.needs]    : []);
  const bday    = c.birthday
    ? new Date(c.birthday).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })
    : '—';
  const sl      = stressLabel(c) || '—';
  const sc      = stressClass(c);
  const nextChk = c.check_when
    ? new Date(c.check_when).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })
    : '—';
  const reminderType = c.check_what
    ? (c.check_what.toLowerCase().includes('monthly') ? 'Monthly check-in' : 'Grant follow-up')
    : '—';

  $('#profileContent').innerHTML = `
    <div class="profile-hero">
      <div class="profile-avatar">${esc(ini)}</div>
      <h2>${esc(c.name)}</h2>
      <p>${esc(c.centre || '')}${c.centre ? ' Centre' : ''}</p>
      ${sl !== '—' ? `<span class="badge ${sc === 'high' ? 'high' : sc === 'moderate' ? 'medium' : 'low'}" style="margin-top:8px">${esc(sl)} stress</span>` : ''}
      <button class="button secondary" style="margin-top:16px" data-toast="Edit form will be available in a future update.">${icon('i-save')} Edit profile</button>
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
      </div>
    </div>

    <div class="profile-section">
      <h3>Wellbeing</h3>
      <div class="detail-grid">
        <div>Stress level<strong>${sl !== '—' ? `<span class="stress ${sc}">${esc(sl)}</span>` : '—'}${c.stress_score != null ? ` <em style="color:var(--muted);font-size:11px">(ZBI: ${c.stress_score})</em>` : ''}</strong></div>
        <div>Next check-in<strong>${esc(nextChk)}</strong></div>
        <div>Reminder type<strong>${esc(reminderType)}</strong></div>
        ${c.check_what ? `<div>Notes<strong style="font-weight:400;color:var(--muted)">${esc(c.check_what)}</strong></div>` : ''}
      </div>
    </div>

    ${c.flag ? `<div class="profile-section"><h3>Flag</h3><p style="margin:0"><span class="badge high">${esc(c.flag)}</span></p></div>` : ''}

    <div class="profile-section" style="border-bottom:0">
      <h3>Activity</h3>
      <div class="timeline">
        <div><strong>Record created</strong><p>Added to CareCircle database</p></div>
        ${c.check_when ? `<div><strong>Next check-in scheduled</strong><p>${esc(nextChk)}</p></div>` : ''}
      </div>
    </div>`;
}

/* ══════════════════════════════════════════════════════════════════════
   IMPORT / UPLOAD
══════════════════════════════════════════════════════════════════════ */
async function loadImportPreview() {
  try {
    const data = await api('/caregivers?per_page=10&page=1');
    renderImportPreview(data.items);
  } catch {
    if ($('#importTable'))
      $('#importTable').innerHTML = `<tr><td colspan="8" style="text-align:center;padding:32px;color:var(--muted)">No import data yet.</td></tr>`;
  }
}

function renderImportPreview(items) {
  if (!items?.length) {
    $('#importTable').innerHTML = `<tr><td colspan="8">
      ${emptyStateFull('i-upload', 'No data imported yet', 'Upload a CSV or Excel file to see a preview here.', '')}
    </td></tr>`;
    if ($('#importRowCount')) $('#importRowCount').textContent = '0 rows';
    return;
  }
  if ($('#importRowCount')) $('#importRowCount').textContent = `${items.length} rows`;
  $('#importTable').innerHTML = items.map(c => {
    const langs   = Array.isArray(c.language) ? c.language.join(', ')         : (c.language || '—');
    const hobbies = Array.isArray(c.hobbies)  ? c.hobbies.slice(0,3).join(', ') : (c.hobbies  || '—');
    const needs   = Array.isArray(c.needs)    ? c.needs.slice(0,2).join(', ')   : (c.needs    || '—');
    const bday    = c.birthday
      ? new Date(c.birthday).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
      : '—';
    const domain  = c.situation
      ? (['Dementia','Mobility','Mental health','Chronic illness']
          .find(d => c.situation.toLowerCase().includes(d.toLowerCase())) || '—')
      : '—';
    return `<tr>
      <td>${esc(c.name)}</td><td>${esc(c.phone||'—')}</td><td>${esc(bday)}</td>
      <td>${esc(langs)}</td><td>${esc(hobbies)}</td><td>${esc(domain)}</td>
      <td>${esc(needs)}</td><td><span class="badge success">Active</span></td>
    </tr>`;
  }).join('');
}

async function uploadFile(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['csv','xls','xlsx'].includes(ext)) {
    toast('Only .csv, .xls, and .xlsx files are supported.');
    return;
  }
  const statusEl = $('#importStatus');
  statusEl.style.display = 'flex';
  statusEl.innerHTML = `<span class="file-icon">${esc(ext.toUpperCase())}</span>
    <div><strong>${esc(file.name)}</strong><p>Uploading…</p></div>`;
  const form = new FormData();
  form.append('file', file);
  try {
    const result = await api('/upload', { method: 'POST', body: form });
    const now = new Date().toLocaleString('en-GB', {
      day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
    });
    statusEl.innerHTML = `
      <span class="file-icon">${esc(ext.toUpperCase())}</span>
      <div>
        <strong>${esc(file.name)}</strong>
        <p>Imported ${esc(now)} · ${result.imported} new, ${result.updated} updated, ${result.skipped} skipped</p>
      </div>
      <span class="badge success">Imported</span>`;
    toast(`Import complete: ${result.imported} new, ${result.updated} updated, ${result.skipped} skipped.`);
    if (result.preview?.length) renderImportPreview(result.preview);
    delete _loaded['caregivers'];
    loadDashboard();
  } catch (e) {
    statusEl.innerHTML = `
      <span class="file-icon" style="background:#e53935;color:#fff">!</span>
      <div><strong>${esc(file.name)}</strong><p style="color:#e53935">${esc(e.message)}</p></div>
      <span class="badge high">Error</span>`;
    toast(e.message);
  }
}

function initUpload() {
  const dropzone  = $('#dropzone');
  const fileInput = $('#fileInput');
  if (!dropzone || !fileInput) return;
  fileInput.addEventListener('change', e => { if (e.target.files[0]) uploadFile(e.target.files[0]); });
  ['dragover','dragenter'].forEach(x =>
    dropzone.addEventListener(x, e => { e.preventDefault(); dropzone.classList.add('dragover'); })
  );
  ['dragleave','drop'].forEach(x =>
    dropzone.addEventListener(x, e => {
      e.preventDefault(); dropzone.classList.remove('dragover');
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
      <div style="grid-column:1/-1">
        ${emptyStateFull('i-target', 'No recommendations yet', 'Fill in the workshop builder above and click Generate.', '')}
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
    const age     = c.birthday ? new Date().getFullYear() - new Date(c.birthday).getFullYear() : null;
    return `<article class="panel recommend-card">
      <span class="score">${starStr}</span>
      <div class="recommend-top">
        <span class="avatar teal">${esc(ini)}</span>
        <div>
          <h3>${esc(c.name)}</h3>
          <p>${age ? age + ' yrs' : ''}${age && langs ? ' · ' : ''}${esc(langs)}</p>
        </div>
      </div>
      ${hobbies.map(h => `<span class="pill">${esc(h)}</span>`).join('')}
      <div class="reason">
        <strong>Match score ${pct}%</strong>
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

  const btn = form.querySelector('.generate');
  if (btn) { btn.disabled = true; btn.textContent = 'Generating…'; }
  try {
    const result = await api('/recommendations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workshop, language, interests: tags, maximum_participants }),
    });
    renderRecommendations(result.items);
    if ($('#recommendCount'))
      $('#recommendCount').textContent = `${result.count} caregiver${result.count !== 1 ? 's' : ''} matched to your criteria`;
    toast(`${result.count} recommendation${result.count !== 1 ? 's' : ''} generated.`);
  } catch (e) {
    toast(e.message || 'Could not generate recommendations.');
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = `${icon('i-zap')}Generate recommendations`; }
  }
}

/* ══════════════════════════════════════════════════════════════════════
   ANALYTICS
══════════════════════════════════════════════════════════════════════ */
async function loadAnalytics() {
  const grid = $('#analyticsGrid');
  if (grid) grid.innerHTML = '<div style="padding:40px;color:var(--muted);text-align:center;grid-column:1/-1">Loading analytics…</div>';
  try {
    const data = await api('/analytics');
    renderAnalytics(data);
  } catch {
    if ($('#analyticsGrid'))
      $('#analyticsGrid').innerHTML = emptyStateFull('i-chart', 'Could not load analytics', 'Please refresh the page.', '');
  }
}

function renderAnalytics(data) {
  const ag     = data.age_groups || {};
  const lang   = data.language_distribution || {};
  const centre = data.centre_distribution || {};
  const bmonth = data.birthday_by_month || {};
  const stress = data.stress_distribution || {};
  const grants = data.grant_type_distribution || {};
  const mfol   = data.monthly_followup_distribution || {};
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

  const specs = [
    { title: 'Age distribution',     sub: 'By age group',              type: 'bar',      labels: ['Under 40','40–49','50–59','60–69','70+'], values: [ag.under_40||0,ag['40_49']||0,ag['50_59']||0,ag['60_69']||0,ag['70_plus']||0] },
    { title: 'Languages',            sub: 'Preferred language',         type: 'doughnut', labels: Object.keys(lang),              values: Object.values(lang) },
    { title: 'Stress levels',        sub: 'ZBI assessment results',     type: 'doughnut', labels: Object.keys(stress),            values: Object.values(stress) },
    { title: 'Caregivers by centre', sub: 'Distribution across centres',type: 'bar',      labels: Object.keys(centre).slice(0,8), values: Object.values(centre).slice(0,8) },
    { title: 'Grant types',          sub: 'Grant programme breakdown',  type: 'doughnut', labels: Object.keys(grants).slice(0,8), values: Object.values(grants).slice(0,8) },
    { title: 'Monthly follow-ups',   sub: 'Due by month',               type: 'bar',      labels: months, values: months.map((_,i) => mfol[String(i+1)]||0) },
    { title: 'Birthdays by month',   sub: 'Celebration planning',       type: 'line',     labels: months, values: months.map((_,i) => bmonth[String(i+1)]||0) },
  ].filter(s => s.values.some(v => v > 0));

  if (!specs.length) {
    $('#analyticsGrid').innerHTML = `<div style="grid-column:1/-1">${emptyStateFull('i-chart', 'No analytics data yet', 'Import caregivers first to see insights.', `<button class="button" onclick="navigateTo('import')">${icon('i-upload')} Import data</button>`)}</div>`;
    return;
  }
  $('#analyticsGrid').innerHTML = specs.map((s, i) =>
    `<article class="panel analytics-card">
      <div class="panel-heading"><div><h2>${esc(s.title)}</h2><p>${esc(s.sub)}</p></div></div>
      <div class="chart-wrap"><canvas id="aC${i}"></canvas></div>
    </article>`
  ).join('');
  specs.forEach((s, i) => makeChart(`aC${i}`, s.type, s.labels, s.values));
}

/* ══════════════════════════════════════════════════════════════════════
   SETTINGS
══════════════════════════════════════════════════════════════════════ */
let _settings = {};

async function loadSettings() {
  try {
    _settings = await api('/settings');
    renderSettings(_settings);
  } catch { toast('Could not load settings.'); }
}

function renderSettings(s) {
  $('#settingsGrid').innerHTML = `
    <!-- General -->
    <article class="panel setting-section">
      <h2>General</h2>
      <p>Application-wide configuration.</p>
      <label>Application Name<input type="text" id="s_app_name" value="${esc(s.app_name || 'CareCircle')}"></label>
      <label style="margin-top:12px">Default Centre<input type="text" id="s_default_centre" value="${esc(s.default_centre || '')}" placeholder="e.g. Buona Vista"></label>
    </article>

    <!-- Notifications -->
    <article class="panel setting-section">
      <h2>Notification preferences</h2>
      <p>Choose which alerts appear in CareCircle.</p>
      <label class="toggle-row">Birthday alerts<input type="checkbox" id="s_notify_birthdays" ${s.notify_birthdays !== 'false' ? 'checked' : ''}><span></span></label>
      <label class="toggle-row">Grant follow-up alerts<input type="checkbox" id="s_notify_grants" ${s.notify_grants !== 'false' ? 'checked' : ''}><span></span></label>
      <label class="toggle-row">Monthly check-in alerts<input type="checkbox" id="s_notify_checkins" ${s.notify_checkins !== 'false' ? 'checked' : ''}><span></span></label>
      <label class="toggle-row">Email notifications<input type="checkbox" id="s_notify_email" ${s.notify_email === 'true' ? 'checked' : ''}><span></span></label>
    </article>

    <!-- Appearance -->
    <article class="panel setting-section">
      <h2>Appearance</h2>
      <p>Choose the look and feel of your workspace.</p>
      <div class="theme-options">
        <button class="theme-choice ${s.theme !== 'dark' && s.theme !== 'system' ? 'active' : ''}" data-theme="light"><span class="theme-preview light"></span>Light</button>
        <button class="theme-choice ${s.theme === 'dark' ? 'active' : ''}" data-theme="dark"><span class="theme-preview dark"></span>Dark</button>
        <button class="theme-choice ${s.theme === 'system' ? 'active' : ''}" data-theme="system"><span class="theme-preview system"></span>System</button>
      </div>
      <div style="margin-top:16px">
        <label style="font-size:11px;font-weight:700;color:#527067;display:grid;gap:6px">
          Accent colour
          <input type="color" id="s_accent_colour" value="${esc(s.accent_colour || '#2e7d6b')}" style="height:36px;border-radius:6px;border:1px solid var(--line);padding:2px 6px;cursor:pointer;width:100%">
        </label>
      </div>
    </article>

    <!-- Data -->
    <article class="panel setting-section">
      <h2>Data management</h2>
      <p>Export, import, or clear your caregiver database.</p>
      <div style="display:grid;gap:9px">
        <a class="button secondary" href="/settings/export" download>${icon('i-download')} Export database</a>
        <button class="button secondary" id="clearDbBtn" style="color:#c0392b;border-color:#f5c6c4">${icon('i-close')} Clear database</button>
      </div>
    </article>

    <!-- Backup -->
    <article class="panel setting-section">
      <h2>Backup</h2>
      <p>Create and restore database snapshots.</p>
      <div style="display:grid;gap:9px;margin-bottom:18px">
        <button class="button secondary" id="createBackupBtn">${icon('i-save')} Create backup now</button>
      </div>
      <h3 style="margin-bottom:10px;font-size:12px;color:var(--muted)">Existing backups</h3>
      <div id="backupList" style="font-size:12px;color:var(--muted)">Loading…</div>
    </article>

    <!-- About -->
    <article class="panel setting-section about">
      <h2>About CareCircle</h2>
      <p>Caregiver Management System · Version 1.0.0</p>
      <p style="margin-top:4px;font-size:12.5px">All data is stored locally in SQLite. No cloud services are used.</p>
      <a href="#" data-toast="Support contact details copied." style="margin-top:12px;display:inline-block">Contact support</a>
    </article>`;

  loadBackups();
  applyTheme(s.theme || 'light');

  $$('.theme-choice').forEach(btn => {
    btn.addEventListener('click', () => {
      $$('.theme-choice').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      applyTheme(btn.dataset.theme);
    });
  });

  $('#clearDbBtn')?.addEventListener('click', async () => {
    if (!confirm('This will permanently delete ALL caregiver records. Continue?')) return;
    try {
      const r = await api('/settings/clear', { method: 'POST' });
      toast(r.message);
      delete _loaded['caregivers'];
      loadDashboard();
    } catch (e) { toast(e.message); }
  });

  $('#createBackupBtn')?.addEventListener('click', async () => {
    try {
      const r = await api('/settings/backup', { method: 'POST' });
      toast(r.message);
      loadBackups();
    } catch (e) { toast(e.message); }
  });
}

async function loadBackups() {
  try {
    const data = await api('/settings/backups');
    const el = $('#backupList');
    if (!el) return;
    if (!data.backups.length) { el.textContent = 'No backups yet.'; return; }
    el.innerHTML = data.backups.map(b =>
      `<div class="backup-row">
        <span>${esc(b.name)}</span>
        <span>${esc(b.size_kb)} KB</span>
        <button class="text-btn restore-backup" data-name="${esc(b.name)}">Restore</button>
      </div>`
    ).join('');
  } catch { if ($('#backupList')) $('#backupList').textContent = 'Could not load backups.'; }
}

function applyTheme(theme) {
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const useDark = theme === 'dark' || (theme === 'system' && prefersDark);
  document.documentElement.setAttribute('data-theme', useDark ? 'dark' : 'light');
}

async function saveSettings() {
  const theme = document.querySelector('.theme-choice.active')?.dataset.theme || 'light';
  const data = {
    app_name:         $('#s_app_name')?.value || 'CareCircle',
    default_centre:   $('#s_default_centre')?.value || '',
    notify_birthdays: String($('#s_notify_birthdays')?.checked ?? true),
    notify_grants:    String($('#s_notify_grants')?.checked ?? true),
    notify_checkins:  String($('#s_notify_checkins')?.checked ?? true),
    notify_email:     String($('#s_notify_email')?.checked ?? false),
    theme,
    accent_colour:    $('#s_accent_colour')?.value || '#2e7d6b',
  };
  try {
    await api('/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    _settings = data;
    applyTheme(theme);
    document.documentElement.style.setProperty('--green', data.accent_colour);
    toast('Settings saved successfully.');
  } catch (e) { toast(e.message); }
}

async function resetSettings() {
  if (!confirm('Reset all settings to their defaults?')) return;
  try {
    const defaults = {
      app_name: 'CareCircle', default_centre: '',
      notify_birthdays: 'true', notify_grants: 'true',
      notify_checkins: 'true', notify_email: 'false',
      theme: 'light', accent_colour: '#2e7d6b'
    };
    await api('/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(defaults) });
    document.documentElement.setAttribute('data-theme', 'light');
    document.documentElement.style.setProperty('--green', '#2e7d6b');
    loadSettings();
    toast('Settings reset to defaults.');
  } catch (e) { toast(e.message); }
}

/* ══════════════════════════════════════════════════════════════════════
   ACCOUNT
══════════════════════════════════════════════════════════════════════ */
async function loadAccount() {
  try {
    const user = await api('/account');
    renderAccount(user);
  } catch { toast('Could not load account.'); }
}

function renderAccount(user) {
  const ini    = initials(user.full_name);
  const joined = new Date(user.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
  const lastLog = user.last_login
    ? new Date(user.last_login).toLocaleString('en-GB', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    : 'First login';

  $('#accountContent').innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">
      <!-- Profile card -->
      <article class="panel setting-section">
        <div style="display:flex;align-items:center;gap:16px;margin-bottom:22px">
          <div style="width:64px;height:64px;border-radius:18px;background:#d9eeea;color:var(--green);font:800 22px Manrope;display:grid;place-items:center;flex-shrink:0">${esc(ini)}</div>
          <div>
            <h2 style="font-size:18px;margin:0 0 3px">${esc(user.full_name)}</h2>
            <p style="color:var(--muted);margin:0;font-size:12px">@${esc(user.username)}</p>
            <span class="badge success" style="margin-top:6px">${esc(user.role)}</span>
          </div>
        </div>
        <div class="detail-grid">
          <div>Email<strong>${esc(user.email)}</strong></div>
          <div>Role<strong>${esc(user.role)}</strong></div>
          <div>Member since<strong>${esc(joined)}</strong></div>
          <div>Last login<strong>${esc(lastLog)}</strong></div>
        </div>
      </article>

      <!-- Edit profile -->
      <article class="panel setting-section">
        <h2>Edit profile</h2>
        <p>Update your display name and email address.</p>
        <form id="editProfileForm">
          <label style="display:grid;gap:6px;font-size:11px;font-weight:700;color:#527067;margin-bottom:14px">
            Full Name
            <input type="text" id="ep_name" value="${esc(user.full_name)}">
          </label>
          <label style="display:grid;gap:6px;font-size:11px;font-weight:700;color:#527067;margin-bottom:18px">
            Email
            <input type="email" id="ep_email" value="${esc(user.email)}">
          </label>
          <button class="button" type="submit" style="width:100%">${icon('i-save')} Save changes</button>
        </form>
      </article>

      <!-- Change password -->
      <article class="panel setting-section">
        <h2>Change password</h2>
        <p>Choose a strong password of at least 8 characters.</p>
        <form id="changePasswordForm">
          <label style="display:grid;gap:6px;font-size:11px;font-weight:700;color:#527067;margin-bottom:12px">
            Current Password<input type="password" id="cp_current" placeholder="Current password">
          </label>
          <label style="display:grid;gap:6px;font-size:11px;font-weight:700;color:#527067;margin-bottom:12px">
            New Password<input type="password" id="cp_new" placeholder="New password (min 8 chars)">
          </label>
          <label style="display:grid;gap:6px;font-size:11px;font-weight:700;color:#527067;margin-bottom:18px">
            Confirm Password<input type="password" id="cp_confirm" placeholder="Confirm new password">
          </label>
          <button class="button" type="submit" style="width:100%">${icon('i-key')} Change password</button>
        </form>
      </article>

      <!-- Account actions -->
      <article class="panel setting-section">
        <h2>Account actions</h2>
        <p>Sign out or manage your session.</p>
        <div style="display:grid;gap:9px;margin-top:6px">
          <button class="button secondary" id="logoutBtn" style="justify-content:flex-start;gap:10px">
            ${icon('i-logout')} Sign out
          </button>
        </div>
      </article>
    </div>`;

  $('#editProfileForm').addEventListener('submit', async e => {
    e.preventDefault();
    try {
      const r = await api('/account', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ full_name: $('#ep_name').value.trim(), email: $('#ep_email').value.trim() }),
      });
      _currentUser = r.user;
      renderSidebarUser(_currentUser);
      toast('Profile updated.');
      loadAccount();
    } catch (e2) { toast(e2.message); }
  });

  $('#changePasswordForm').addEventListener('submit', async e => {
    e.preventDefault();
    try {
      await api('/account/password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_password: $('#cp_current').value,
          new_password:     $('#cp_new').value,
          confirm_password: $('#cp_confirm').value,
        }),
      });
      toast('Password changed successfully.');
      e.target.reset();
    } catch (e2) { toast(e2.message); }
  });

  $('#logoutBtn').addEventListener('click', async () => {
    await fetch('/auth/logout', { method: 'POST' }).catch(() => {});
    location.href = '/login.html';
  });
}

/* ── Empty state helper ──────────────────────────────────────────────── */
function emptyStateFull(iconId, title, sub, action) {
  return `<div class="empty-state-full">
    ${icon(iconId)}
    <h3>${esc(title)}</h3>
    <p>${sub}</p>
    ${action || ''}
  </div>`;
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
  $('.sidebar')?.classList.remove('open');
  window.scrollTo(0, 0);
  if (!_loaded[page]) {
    _loaded[page] = true;
    if      (page === 'caregivers')     loadCaregivers();
    else if (page === 'alerts')         loadAlerts();
    else if (page === 'analytics')      loadAnalytics();
    else if (page === 'import')         loadImportPreview();
    else if (page === 'settings')       loadSettings();
    else if (page === 'account')        loadAccount();
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
  if (toastBtn) { e.preventDefault(); toast(toastBtn.dataset.toast); return; }

  const viewPerson = e.target.closest('.view-person');
  if (viewPerson) { openProfile(viewPerson.dataset.id); return; }

  const viewAlert = e.target.closest('.view-alert');
  if (viewAlert?.dataset.id) { openProfile(viewAlert.dataset.id); return; }

  if (e.target.closest('.close-drawer') || e.target === $('#drawerBackdrop')) {
    $('#profileDrawer')?.classList.remove('open');
    $('#drawerBackdrop')?.classList.remove('open');
    return;
  }
  if (e.target.closest('.menu-btn')) { $('.sidebar')?.classList.toggle('open'); return; }
  if (e.target.closest('.tag'))      { e.target.closest('.tag').classList.toggle('selected'); return; }

  const pageBtn = e.target.closest('.page-number[data-page]');
  if (pageBtn && !pageBtn.disabled) {
    cgState.page = parseInt(pageBtn.dataset.page);
    loadCaregivers();
    return;
  }

  if (e.target.id === 'saveSettingsBtn')  { saveSettings(); return; }
  if (e.target.id === 'resetSettingsBtn') { resetSettings(); return; }
  if (e.target.closest('#staffCard'))     { navigateTo('account'); return; }

  const restoreBtn = e.target.closest('.restore-backup');
  if (restoreBtn) {
    const name = restoreBtn.dataset.name;
    if (confirm(`Restore from backup "${name}"? This will overwrite the current database.`)) {
      api('/settings/restore', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: name }),
      }).then(r => { toast(r.message); delete _loaded['caregivers']; loadDashboard(); })
        .catch(err => toast(err.message));
    }
  }
});

/* Caregiver search */
$('#caregiverSearch')?.addEventListener('input', e => {
  clearTimeout(_searchTimer);
  _searchTimer = setTimeout(() => {
    cgState.search = e.target.value.trim();
    cgState.page = 1;
    _loaded['caregivers'] = true;
    loadCaregivers();
  }, 280);
});

/* Language filter */
document.querySelector('select[aria-label="Filter by language"]')?.addEventListener('change', e => {
  cgState.language = e.target.value === 'All languages' ? '' : e.target.value;
  cgState.page = 1;
  _loaded['caregivers'] = true;
  loadCaregivers();
});

/* Workshop form */
$('#workshopForm')?.addEventListener('submit', e => {
  e.preventDefault();
  submitRecommendations(e.target);
});

/* ══════════════════════════════════════════════════════════════════════
   INIT
══════════════════════════════════════════════════════════════════════ */
initUpload();
initApp();
