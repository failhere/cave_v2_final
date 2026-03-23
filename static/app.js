
const state = {
  user: null,
  users: [],
  zones: [],
  tanks: [],
  lots: [],
  events: [],
  history: [],
  editable: false,
  calendarMonth: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
  calendarSelectedDate: new Date().toISOString().slice(0,10),
};

const STATUS_LABELS = {
  vide: 'Vide',
  occupee_non_pleine: 'Occupée non pleine',
  occupee_pleine: 'Occupée pleine',
  fermentation: 'Fermentation',
  elevage: 'Élevage',
  nettoyage: 'À nettoyer',
  a_derougir: 'À dérougir',
  alerte: 'Alerte',
};

function el(sel){ return document.querySelector(sel); }
function els(sel){ return [...document.querySelectorAll(sel)]; }
function esc(v){
  return String(v ?? '')
    .replaceAll('&','&amp;').replaceAll('<','&lt;')
    .replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'","&#39;");
}
function fmt(n){ return (n ?? 0).toLocaleString('fr-FR', {maximumFractionDigits:2}); }
function dateFmt(v){
  if (!v) return '';
  const d = new Date(v);
  return d.toLocaleString('fr-FR');
}
function dateOnly(v){
  if (!v) return '';
  return new Date(v).toLocaleDateString('fr-FR');
}
function timeOnly(v){
  if (!v) return '';
  return new Date(v).toLocaleTimeString('fr-FR', {hour:'2-digit', minute:'2-digit'});
}

const TEMP_POINTS = [13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28];
const MV_POINTS = [1000,1010,1020,1030,1040,1050,1060,1070,1080,1090,1100,1120,1140,1160,1180,1200];
const MV_CORRECTIONS = {
13:[-1.03,-1.16,-1.28,-1.40,-1.52,-1.62,-1.74,-1.85,-1.85,-2.07,-2.17,-2.38,-2.54,-2.77,-2.94,-3.11],
14:[-0.92,-1.03,-1.14,-1.24,-1.34,-1.44,-1.54,-1.64,-1.73,-1.82,-1.92,-2.08,-2.25,-2.42,-2.57,-2.77],
15:[-0.77,-0.87,-0.96,-1.04,-1.13,-1.21,-1.29,-1.37,-1.45,-1.53,-1.60,-1.75,-1.89,-2.03,-2.16,-2.28],
16:[-0.65,-0.72,-0.79,-0.86,-0.93,-1.00,-1.06,-1.12,-1.19,-1.25,-1.31,-1.43,-1.54,-1.65,-1.75,-1.84],
17:[-0.50,-0.56,-0.61,-0.66,-0.72,-0.76,-0.82,-0.86,-0.91,-0.96,-1.00,-1.09,-1.18,-1.25,-1.32,-1.39],
18:[-0.35,-0.39,-0.43,-0.47,-0.49,-0.53,-0.56,-0.59,-0.63,-0.65,-0.69,-0.74,-0.80,-0.85,-0.90,-0.95],
19:[-0.19,-0.21,-0.23,-0.25,-0.27,-0.28,-0.30,-0.31,-0.33,-0.35,-0.36,-0.39,-0.42,-0.43,-0.46,-0.50],
20:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
21:[0.19,0.21,0.23,0.24,0.26,0.28,0.29,0.31,0.32,0.34,0.36,0.39,0.41,0.44,0.46,0.48],
22:[0.39,0.42,0.45,0.49,0.52,0.55,0.58,0.61,0.64,0.67,0.70,0.76,0.81,0.87,0.93,0.97],
23:[0.61,0.66,0.71,0.76,0.80,0.85,0.90,0.95,0.99,1.04,1.08,1.16,1.25,1.32,1.39,1.46],
24:[0.85,0.91,0.97,1.03,1.09,1.15,1.19,1.25,1.31,1.37,1.43,1.54,1.65,1.76,1.86,1.95],
25:[1.08,1.15,1.23,1.30,1.37,1.44,1.52,1.59,1.67,1.74,1.81,1.95,2.09,2.21,2.34,2.45],
26:[1.30,1.40,1.49,1.58,1.67,1.76,1.84,1.93,2.02,2.10,2.18,2.32,2.49,2.64,2.78,2.91],
27:[1.57,1.68,1.77,1.88,1.98,2.07,2.16,2.26,2.36,2.46,2.56,2.74,2.91,3.07,3.24,3.39],
28:[1.82,1.93,2.05,2.16,2.29,2.39,2.51,2.63,2.74,2.85,2.96,3.16,3.38,3.57,3.75,3.92],
};
function normalizeMustimeterReading(v){
  if (v === null || v === undefined || v === '') return null;
  let n = Number(v);
  if (!Number.isFinite(n) || n <= 0) return null;
  if (n < 10) n *= 1000;
  return n;
}
function interp(points, values, x){
  if (x <= points[0]) return values[0];
  if (x >= points[points.length-1]) return values[values.length-1];
  for(let i=0;i<points.length-1;i++){
    const x0 = points[i], x1 = points[i+1];
    if (x >= x0 && x <= x1){
      const y0 = values[i], y1 = values[i+1];
      return y0 + (y1-y0) * ((x-x0)/(x1-x0));
    }
  }
  return values[values.length-1];
}
function mustimeterCorrection(rawReading, tempC){
  const raw = Math.max(MV_POINTS[0], Math.min(MV_POINTS[MV_POINTS.length-1], normalizeMustimeterReading(rawReading)));
  const temp = Math.max(TEMP_POINTS[0], Math.min(TEMP_POINTS[TEMP_POINTS.length-1], Number(tempC)));
  if (Number.isInteger(temp) && MV_CORRECTIONS[temp]) return interp(MV_POINTS, MV_CORRECTIONS[temp], raw);
  const lower = Math.max(...TEMP_POINTS.filter(t=>t<=temp));
  const upper = Math.min(...TEMP_POINTS.filter(t=>t>=temp));
  const lc = interp(MV_POINTS, MV_CORRECTIONS[lower], raw);
  const uc = interp(MV_POINTS, MV_CORRECTIONS[upper], raw);
  if (lower === upper) return lc;
  return lc + (uc-lc) * ((temp-lower)/(upper-lower));
}
function correctedDensity20(rawReading, tempC){
  const raw = normalizeMustimeterReading(rawReading);
  if (!Number.isFinite(raw) || !Number.isFinite(Number(tempC))) return null;
  return raw + mustimeterCorrection(raw, Number(tempC));
}
function densityToBrix(densityValue){
  if (!Number.isFinite(densityValue)) return null;
  const sg = densityValue >= 100 ? densityValue / 1000 : densityValue;
  return (((182.4601 * sg - 775.6821) * sg + 1262.7794) * sg - 669.5622);
}
function computePotentialAbv(rawReading, tempC){
  const corrected = correctedDensity20(rawReading, tempC);
  if (!Number.isFinite(corrected)) return null;
  return Math.max(0, densityToBrix(Math.round(corrected)) / 1.8);
}
function computeSugar(rawReading, tempC){
  const tav = computePotentialAbv(rawReading, tempC);
  return Number.isFinite(tav) ? tav * 16.83 : null;
}
function computeJuiceYield(volumeHl, grapeWeightKg){
  const v = Number(volumeHl), g = Number(grapeWeightKg);
  if (!Number.isFinite(v) || !Number.isFinite(g) || g <= 0) return {lkg:null, pct:null};
  const liters = v * 100;
  const lkg = liters / g;
  const pct = lkg * 100;
  return {lkg, pct};
}

async function api(url, options = {}) {
  const isForm = options.body instanceof FormData;
  if (options.body && !isForm && !options.headers?.['Content-Type']) {
    options.headers = {...options.headers, 'Content-Type':'application/json'};
    options.body = JSON.stringify(options.body);
  }
  const res = await fetch(url, {...options, credentials:'same-origin'});
  if (res.status === 401) {
    showLogin();
    throw new Error('Non connecté');
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || 'Erreur');
  return data;
}

function showLogin(){ el('#loginScreen').classList.remove('hidden'); el('#appShell').classList.add('hidden'); }
function showApp(){ el('#loginScreen').classList.add('hidden'); el('#appShell').classList.remove('hidden'); }
function modal(html){ el('#modalContent').innerHTML = html; el('#modal').classList.remove('hidden'); }
function closeModal(){ el('#modal').classList.add('hidden'); }

async function refreshAll(){
  const bootstrap = await api('/api/bootstrap');
  Object.assign(state, bootstrap);
  el('#userBadge').textContent = `${state.user.full_name} — ${state.user.role_label}`;
  renderZoneFilter();
  await refreshDataOnly();
  showApp();
}
async function refreshDataOnly(){
  await Promise.all([loadTanks(), loadLots(), loadHistory(), loadEvents()]);
  renderDashboard();
  renderAlerts();
}
async function loadTanks(){
  const zone = el('#zoneFilter').value;
  const status = el('#statusFilter').value;
  const search = el('#searchInput').value;
  state.tanks = await api(`/api/tanks?zone=${encodeURIComponent(zone)}&status=${encodeURIComponent(status)}&search=${encodeURIComponent(search)}`);
  renderStats();
  renderTanks();
}
async function loadLots(){ state.lots = await api('/api/lots'); renderLots(); }
async function loadHistory(){ state.history = await api('/api/history'); renderHistory(); }
async function loadEvents(){ state.events = await api('/api/events'); renderEvents(); }

function renderZoneFilter(){
  const cur = el('#zoneFilter').value;
  el('#zoneFilter').innerHTML = `<option value="">Toutes zones</option>` + state.zones.map(z => `<option value="${z.id}">${esc(z.name)}</option>`).join('');
  el('#zoneFilter').value = cur;
}

function renderStats(){
  const totalCap = state.tanks.reduce((a,t)=>a + (t.capacity_hl || 0), 0);
  const current = state.tanks.reduce((a,t)=>a + (t.current_volume_hl || 0), 0);
  const count = key => state.tanks.filter(t => t.display_status === key).length;
  el('#stats').innerHTML = `
    <div class="stat"><div class="subtle">Contenants visibles</div><div class="n">${state.tanks.length}</div></div>
    <div class="stat"><div class="subtle">Capacité visible</div><div class="n">${fmt(totalCap)} hL</div></div>
    <div class="stat"><div class="subtle">Volume actuel</div><div class="n">${fmt(current)} hL</div></div>
    <div class="stat"><div class="subtle">À dérougir</div><div class="n">${count('a_derougir')}</div></div>
    <div class="stat"><div class="subtle">À nettoyer</div><div class="n">${count('nettoyage')}</div></div>
  `;
}

function renderDashboard(){
  const totalVol = state.tanks.reduce((a,t)=>a + (t.current_volume_hl || 0), 0);
  const totalCap = state.stats?.capacity_total_hl || state.tanks.reduce((a,t)=>a + (t.capacity_hl || 0), 0);
  const count = key => state.tanks.filter(t => t.display_status === key).length;
  const occupied = state.tanks.filter(t => (t.current_volume_hl || 0) > 0).length;
  const lateEvents = getLateEvents();
  el('#dashboardStats').innerHTML = `
    <div class="kpi"><div class="subtle">Volume total en cave</div><div class="n">${fmt(totalVol)} hL</div><div class="subtle">${totalCap ? `${fmt((totalVol / totalCap) * 100)} % de la capacité` : ''}</div></div>
    <div class="kpi"><div class="subtle">Cuves occupées</div><div class="n">${occupied}</div><div class="subtle">${count('occupee_pleine')} pleines · ${count('occupee_non_pleine')} partielles</div></div>
    <div class="kpi"><div class="subtle">Statuts métier</div><div class="n">${count('fermentation') + count('elevage')}</div><div class="subtle">${count('fermentation')} fermentation · ${count('elevage')} élevage</div></div>
    <div class="kpi"><div class="subtle">Cuves à traiter</div><div class="n">${count('nettoyage') + count('a_derougir')}</div><div class="subtle">${count('a_derougir')} à dérougir · ${count('nettoyage')} à nettoyer</div></div>
    <div class="kpi"><div class="subtle">Alertes</div><div class="n">${computeSystemAlerts().length + lateEvents.length}</div><div class="subtle">${lateEvents.length} événements en retard</div></div>
  `;
  const now = new Date();
  el('#todayDateLabel').textContent = now.toLocaleDateString('fr-FR', {weekday:'long', day:'numeric', month:'long'});
  const todayKey = now.toISOString().slice(0,10);
  const todayEvents = state.events.filter(e => String(e.starts_at).slice(0,10) === todayKey)
    .sort((a,b)=>String(a.starts_at).localeCompare(String(b.starts_at)));
  el('#todayEvents').innerHTML = todayEvents.map(ev => `
    <div class="feed-item">
      <strong>${esc(ev.title)}</strong>
      <div class="subtle">${timeOnly(ev.starts_at)} · ${esc(ev.event_type || '')}</div>
      <div class="subtle">Cuve : ${esc(ev.tank_id || '—')} · Lot : ${esc(ev.lot_code || '—')}</div>
    </div>
  `).join('') || '<div class="subtle">Aucun événement aujourd’hui.</div>';

  el('#recentHistory').innerHTML = state.history.slice(0,8).map(h => `
    <div class="feed-item">
      <strong>${esc(h.action_type)}</strong>
      <div class="subtle">${dateFmt(h.created_at)} · ${esc(h.user)}</div>
      <div>${esc(h.message)}</div>
    </div>
  `).join('') || '<div class="subtle">Aucun historique.</div>';

  const cleaningTanks = state.tanks.filter(t => ['nettoyage','a_derougir'].includes(t.display_status));
  el('#dashboardCleaning').innerHTML = cleaningTanks.slice(0,10).map(t => `
    <div class="feed-item">
      <strong>${esc(t.id)}</strong>
      <div class="subtle">${esc(t.zone)} · ${STATUS_LABELS[t.display_status]}</div>
      <div class="actions-row">
        <button class="secondary" data-open-tank="${t.id}">Ouvrir</button>
        ${t.display_status === 'a_derougir' ? `<button data-clear-status="${t.id}">Marquer dérougie</button>` : ''}
        ${t.display_status === 'nettoyage' ? `<button data-clear-status="${t.id}">Marquer nettoyée</button>` : ''}
      </div>
    </div>
  `).join('') || '<div class="subtle">Aucune cuve à traiter.</div>';

  const zones = groupTanksByZone();
  el('#dashboardZones').innerHTML = Object.entries(zones).map(([zone, tanks]) => `
    <div class="mini-zone">
      <div><strong>${esc(zone)}</strong><div class="subtle">${tanks.length} contenants</div></div>
      <div class="subtle">${fmt(tanks.reduce((a,t)=>a+(t.current_volume_hl||0),0))} hL</div>
    </div>
  `).join('');
  bindOpenTankButtons();
  bindClearStatusButtons();
}

function groupTanksByZone(){
  const grouped = {};
  for (const t of state.tanks){
    grouped[t.zone] ??= [];
    grouped[t.zone].push(t);
  }
  return grouped;
}

function renderTanks(){
  const grouped = groupTanksByZone();
  el('#zones').innerHTML = Object.entries(grouped).map(([zone, tanks]) => `
    <section class="zone">
      <h3>${esc(zone)}</h3>
      <div class="subtle">${tanks.length} contenants — ${fmt(tanks.reduce((a,t)=>a+(t.capacity_hl||0),0))} hL</div>
      <div class="tank-grid">
        ${tanks.map(t => `
          <button class="tank ${t.display_status}" data-tank="${t.id}">
            <div class="id">${esc(t.id)}</div>
            <div class="meta">${fmt(t.current_volume_hl)} / ${fmt(t.capacity_hl)} hL</div>
            <div class="meta">${t.current_lot ? esc(t.current_lot.code) : '—'}</div>
          </button>
        `).join('')}
      </div>
    </section>
  `).join('');
  bindOpenTankButtons();
}

function renderLots(){
  el('#lotsBody').innerHTML = state.lots.map(l => `
    <tr>
      <td>${esc(l.code)}</td>
      <td>${l.vintage ?? ''}</td>
      <td>${esc(l.wine_type || '')}</td>
      <td>${fmt(l.volume_total_hl)} hL</td>
      <td>${(l.tank_ids || []).map(esc).join(', ') || '—'}</td>
      <td>${l.active ? '<span class="badge">Actif</span>' : '<span class="badge">Clôturé</span>'}</td>
      <td>${state.editable ? `<button class="secondary" data-edit-lot="${l.id}">Modifier</button>` : ''}</td>
    </tr>
  `).join('') || '<tr><td colspan="7" class="subtle">Aucun lot</td></tr>';
  els('[data-edit-lot]').forEach(b => b.onclick = () => openLotForm(state.lots.find(l => String(l.id) === String(b.dataset.editLot))));
}

function renderHistory(){
  el('#historyBody').innerHTML = state.history.map(h => `
    <tr>
      <td>${dateFmt(h.created_at)}</td>
      <td>${esc(h.user)}</td>
      <td>${esc(h.action_type)}</td>
      <td>${esc(h.tank_id || '')}</td>
      <td>${esc(h.lot_code || '')}</td>
      <td>${esc(h.message)}</td>
    </tr>
  `).join('') || '<tr><td colspan="6" class="subtle">Aucun historique</td></tr>';
}

function populateCalendarFilters(){
  const keep = {
    type: el('#calendarTypeFilter')?.value || '',
    status: el('#calendarStatusFilter')?.value || '',
    user: el('#calendarUserFilter')?.value || '',
    tank: el('#calendarTankFilter')?.value || '',
    lot: el('#calendarLotFilter')?.value || '',
  };
  const types = [...new Set(state.events.map(e => e.event_type).filter(Boolean))];
  el('#calendarTypeFilter').innerHTML = `<option value="">Tous types</option>` + types.map(v => `<option value="${esc(v)}">${esc(v)}</option>`).join('');
  el('#calendarUserFilter').innerHTML = `<option value="">Tous utilisateurs</option>` + state.users.map(u => `<option value="${u.id}">${esc(u.full_name)}</option>`).join('');
  el('#calendarTankFilter').innerHTML = `<option value="">Toutes cuves</option>` + state.tanks.map(t => `<option value="${t.id}">${esc(t.id)}</option>`).join('');
  el('#calendarLotFilter').innerHTML = `<option value="">Tous lots</option>` + state.lots.map(l => `<option value="${l.id}">${esc(l.code)}</option>`).join('');
  el('#calendarTypeFilter').value = keep.type;
  el('#calendarStatusFilter').value = keep.status;
  el('#calendarUserFilter').value = keep.user;
  el('#calendarTankFilter').value = keep.tank;
  el('#calendarLotFilter').value = keep.lot;
}

function getFilteredCalendarEvents(){
  const type = el('#calendarTypeFilter').value || '';
  const status = el('#calendarStatusFilter').value || '';
  const user = el('#calendarUserFilter').value || '';
  const tank = el('#calendarTankFilter').value || '';
  const lot = el('#calendarLotFilter').value || '';
  const q = (el('#calendarSearchInput').value || '').trim().toLowerCase();
  return state.events.filter(ev => {
    if (type && ev.event_type !== type) return false;
    if (status && ev.status !== status) return false;
    if (user && String(ev.assigned_user_id || '') !== String(user)) return false;
    if (tank && String(ev.tank_id || '') !== String(tank)) return false;
    if (lot && String(ev.lot_id || '') !== String(lot)) return false;
    if (q) {
      const hay = `${ev.title || ''} ${ev.comment || ''} ${ev.lot_code || ''} ${ev.tank_id || ''}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function renderEvents(){
  if (!el('#calendarMonthLabel')) return;
  populateCalendarFilters();
  const visibleEvents = getFilteredCalendarEvents();
  const monthStart = new Date(state.calendarMonth.getFullYear(), state.calendarMonth.getMonth(), 1);
  const monthEnd = new Date(state.calendarMonth.getFullYear(), state.calendarMonth.getMonth() + 1, 0);
  el('#calendarMonthLabel').textContent = monthStart.toLocaleDateString('fr-FR', {month:'long', year:'numeric'});
  const firstWeekday = (monthStart.getDay() + 6) % 7;
  const daysInMonth = monthEnd.getDate();
  const grid = [];
  for (let i=0;i<firstWeekday;i++) grid.push(null);
  for (let day=1;day<=daysInMonth;day++) grid.push(new Date(state.calendarMonth.getFullYear(), state.calendarMonth.getMonth(), day));
  while (grid.length % 7 !== 0) grid.push(null);
  const eventsByDate = {};
  for (const ev of visibleEvents){
    const key = String(ev.starts_at).slice(0,10);
    (eventsByDate[key] ??= []).push(ev);
  }
  const todayKey = new Date().toISOString().slice(0,10);
  if (!state.calendarSelectedDate || state.calendarSelectedDate.slice(0,7) !== monthStart.toISOString().slice(0,7)) {
    state.calendarSelectedDate = monthStart.toISOString().slice(0,10);
  }
  const selectedKey = state.calendarSelectedDate;
  el('#calendarGrid').innerHTML = grid.map(date => {
    if (!date) return '<div class="calendar-cell empty"></div>';
    const key = date.toISOString().slice(0,10);
    const dayEvents = (eventsByDate[key] || []).sort((a,b)=>String(a.starts_at).localeCompare(String(b.starts_at)));
    const extra = Math.max(0, dayEvents.length - 3);
    return `<button class="calendar-cell ${key===todayKey?'today':''} ${key===selectedKey?'selected':''}" data-cal-date="${key}">
      <div class="calendar-cell-top"><span class="daynum" aria-label="Jour ${date.getDate()}">${date.getDate()}</span><span class="subtle">${dayEvents.length || ''}</span></div>
      <div class="calendar-items">
        ${dayEvents.slice(0,3).map(ev => `<span class="calendar-chip ${esc(ev.status)}">${esc(timeOnly(ev.starts_at))} ${esc(ev.title)}</span>`).join('')}
        ${extra ? `<span class="calendar-more">+${extra} autre${extra>1?'s':''}</span>` : ''}
      </div>
    </button>`;
  }).join('');
  els('[data-cal-date]').forEach(b => b.onclick = () => { state.calendarSelectedDate = b.dataset.calDate; renderEvents(); });
  renderCalendarDayList(visibleEvents);
}

function renderCalendarDayList(visibleEvents){
  const selectedKey = state.calendarSelectedDate;
  const dayEvents = visibleEvents.filter(ev => String(ev.starts_at).slice(0,10) === selectedKey)
    .sort((a,b)=>String(a.starts_at).localeCompare(String(b.starts_at)));
  const selectedDate = new Date(selectedKey + 'T12:00:00');
  el('#calendarDayLabel').textContent = selectedDate.toLocaleDateString('fr-FR', {weekday:'long', day:'numeric', month:'long', year:'numeric'});
  el('#calendarResultsCount').textContent = `${dayEvents.length} événement${dayEvents.length>1?'s':''}`;
  el('#calendarDayEvents').innerHTML = dayEvents.map(ev => `
    <div class="calendar-event-card">
      <div class="calendar-event-top">
        <strong>${esc(ev.title)}</strong>
        <span class="badge">${esc(ev.status)}</span>
      </div>
      <div class="subtle">${timeOnly(ev.starts_at)}${ev.ends_at ? ` → ${timeOnly(ev.ends_at)}` : ''} · ${esc(ev.event_type || '')}</div>
      <div class="subtle">Cuve : ${esc(ev.tank_id || '—')} · Lot : ${esc(ev.lot_code || '—')} · Assigné : ${esc(ev.assigned_user_name || '—')}</div>
      ${ev.comment ? `<div>${esc(ev.comment)}</div>` : ''}
      <div class="actions-row"><button class="secondary" data-edit-event="${ev.id}">Modifier</button></div>
    </div>
  `).join('') || '<div class="subtle">Aucun événement pour cette journée avec les filtres actuels.</div>';
  els('[data-edit-event]').forEach(b => b.onclick = () => openEventForm(state.events.find(e => String(e.id) === String(b.dataset.editEvent))));
}

function computeSystemAlerts(){
  const alerts = [];
  for (const t of state.tanks){
    if ((t.current_volume_hl || 0) > (t.capacity_hl || 0) + 0.0001) {
      alerts.push({level:'critical', title:`${t.id} dépasse la capacité`, text:`${fmt(t.current_volume_hl)} hL pour ${fmt(t.capacity_hl)} hL.`});
    }
    if ((t.current_volume_hl || 0) > 0 && !t.current_lot) {
      alerts.push({level:'warning', title:`${t.id} a du volume sans lot`, text:`Assigner ou corriger le lot courant.`});
    }
    if (t.display_status === 'alerte') {
      alerts.push({level:'critical', title:`${t.id} est en alerte`, text:`Vérifier le commentaire et l'état de la cuve.`});
    }
  }
  return alerts;
}
function getLateEvents(){
  const now = new Date();
  return state.events.filter(ev => ev.status === 'prevu' && new Date(ev.starts_at) < now);
}
function renderAlerts(){
  const der = state.tanks.filter(t => t.display_status === 'a_derougir');
  const net = state.tanks.filter(t => t.display_status === 'nettoyage');
  const systemAlerts = computeSystemAlerts();
  const lateEvents = getLateEvents();

  el('#countDerougir').textContent = der.length;
  el('#countNettoyer').textContent = net.length;
  el('#countSystemAlerts').textContent = systemAlerts.length;
  el('#countLateEvents').textContent = lateEvents.length;

  el('#alertsDerougir').innerHTML = der.map(t => `
    <div class="alert-item critical">
      <strong>${esc(t.id)}</strong>
      <div class="subtle">${esc(t.zone)} · ${fmt(t.current_volume_hl)} / ${fmt(t.capacity_hl)} hL</div>
      <div>Cette cuve est bloquante tant qu'elle n'est pas marquée comme dérougie.</div>
      <div class="actions-row"><button data-clear-status="${t.id}">Marquer dérougie</button><button class="secondary" data-open-tank="${t.id}">Ouvrir</button></div>
    </div>
  `).join('') || '<div class="subtle">Aucune cuve à dérougir.</div>';

  el('#alertsNettoyer').innerHTML = net.map(t => `
    <div class="alert-item warning">
      <strong>${esc(t.id)}</strong>
      <div class="subtle">${esc(t.zone)} · ${fmt(t.current_volume_hl)} / ${fmt(t.capacity_hl)} hL</div>
      <div>Information non bloquante. La cuve peut être marquée comme nettoyée.</div>
      <div class="actions-row"><button data-clear-status="${t.id}">Marquer nettoyée</button><button class="secondary" data-open-tank="${t.id}">Ouvrir</button></div>
    </div>
  `).join('') || '<div class="subtle">Aucune cuve à nettoyer.</div>';

  el('#alertsSystem').innerHTML = systemAlerts.map(a => `
    <div class="alert-item ${a.level}">
      <strong>${esc(a.title)}</strong>
      <div>${esc(a.text)}</div>
    </div>
  `).join('') || '<div class="subtle">Aucune alerte système.</div>';

  el('#alertsLateEvents').innerHTML = lateEvents.map(ev => `
    <div class="alert-item warning">
      <strong>${esc(ev.title)}</strong>
      <div class="subtle">${dateFmt(ev.starts_at)} · ${esc(ev.event_type || '')}</div>
      <div class="subtle">Cuve : ${esc(ev.tank_id || '—')} · Lot : ${esc(ev.lot_code || '—')}</div>
      <div class="actions-row"><button class="secondary" data-edit-event="${ev.id}">Modifier</button></div>
    </div>
  `).join('') || '<div class="subtle">Aucun événement en retard.</div>';

  bindOpenTankButtons();
  bindClearStatusButtons();
  els('[data-edit-event]').forEach(b => b.onclick = () => openEventForm(state.events.find(e => String(e.id) === String(b.dataset.editEvent))));
}

function bindOpenTankButtons(){
  els('[data-tank],[data-open-tank]').forEach(b => b.onclick = () => openTank(b.dataset.tank || b.dataset.openTank));
}
function bindClearStatusButtons(){
  els('[data-clear-status]').forEach(b => b.onclick = async () => {
    try {
      await api(`/api/tanks/${b.dataset.clearStatus}/status`, {method:'POST', body:{manual_status:null}});
      await refreshDataOnly();
    } catch(err){ alert(err.message); }
  });
}

function openTank(id){
  const t = state.tanks.find(x => x.id === id);
  if (!t) return;
  modal(`
    <h3>Cuve ${esc(t.id)}</h3>
    <div class="form-grid">
      <div class="two"><div><strong>Zone</strong><div>${esc(t.zone)}</div></div><div><strong>Statut</strong><div>${esc(STATUS_LABELS[t.display_status] || t.display_status)}</div></div></div>
      <div class="two"><div><strong>Capacité</strong><div>${fmt(t.capacity_hl)} hL</div></div><div><strong>Volume actuel</strong><div>${fmt(t.current_volume_hl)} hL (${fmt(t.fill_pct)} %)</div></div></div>
      <div><strong>Lot</strong><div>${t.current_lot ? esc(t.current_lot.code) : '—'}</div></div>
      <div><strong>Dernière mise à jour</strong><div>${t.updated_at ? dateFmt(t.updated_at) : '—'}</div></div>
      <div><strong>Commentaire</strong><div>${esc(t.comment || '') || '—'}</div></div>
    </div>
    <div class="actions-row">
      ${state.editable ? `<button id="setStatusBtn" class="secondary">Statut manuel</button><button id="resetTankBtn" class="secondary">Remise à zéro</button>` : ''}
      ${t.display_status === 'nettoyage' ? `<button id="markCleanBtn">Marquer nettoyée</button>` : ''}
      ${t.display_status === 'a_derougir' ? `<button id="markDerougieBtn">Marquer dérougie</button>` : ''}
      <button id="moveFromTankBtn">Nouveau mouvement</button>
      <button class="secondary" onclick="document.getElementById('modal').classList.add('hidden')">Fermer</button>
    </div>
  `);
  if (state.editable) {
    const s = el('#setStatusBtn'); if (s) s.onclick = () => openStatusForm(t);
    const r = el('#resetTankBtn'); if (r) r.onclick = () => openResetForm(t);
  }
  const markClean = el('#markCleanBtn');
  if (markClean) markClean.onclick = async () => { await api(`/api/tanks/${t.id}/status`, {method:'POST', body:{manual_status:null}}); closeModal(); await refreshDataOnly(); };
  const markDer = el('#markDerougieBtn');
  if (markDer) markDer.onclick = async () => { await api(`/api/tanks/${t.id}/status`, {method:'POST', body:{manual_status:null}}); closeModal(); await refreshDataOnly(); };
  el('#moveFromTankBtn').onclick = () => openMovementForm(t);
}

function openStatusForm(tank){
  modal(`
    <h3>Statut manuel — ${esc(tank.id)}</h3>
    <div class="form-grid">
      <label>Statut
        <select id="manualStatus">
          <option value="">Automatique</option>
          <option value="fermentation">Fermentation</option>
          <option value="elevage">Élevage</option>
          <option value="nettoyage">À nettoyer</option>
          <option value="a_derougir">À dérougir</option>
          <option value="alerte">Alerte</option>
        </select>
      </label>
    </div>
    <div class="actions-row"><button id="saveStatusBtn">Enregistrer</button><button class="secondary" onclick="document.getElementById('modal').classList.add('hidden')">Annuler</button></div>
  `);
  el('#manualStatus').value = tank.manual_status || '';
  el('#saveStatusBtn').onclick = async () => {
    await api(`/api/tanks/${tank.id}/status`, {method:'POST', body:{manual_status: el('#manualStatus').value || null}});
    closeModal();
    await refreshDataOnly();
  };
}
function openResetForm(tank){
  modal(`
    <h3>Remise à zéro — ${esc(tank.id)}</h3>
    <p>Cette action remet le volume à 0, retire le lot courant et supprime le statut manuel.</p>
    <label>Motif<textarea id="resetReason" rows="4" placeholder="Ex: cuve vidée et prête au nettoyage"></textarea></label>
    <div class="actions-row"><button id="confirmResetBtn">Confirmer</button><button class="secondary" onclick="document.getElementById('modal').classList.add('hidden')">Annuler</button></div>
  `);
  el('#confirmResetBtn').onclick = async () => {
    await api(`/api/tanks/${tank.id}/reset`, {method:'POST', body:{reason: el('#resetReason').value}});
    closeModal();
    await refreshDataOnly();
  };
}

function lotOptions(selectedId){
  return `<option value="">Aucun lot</option>` + state.lots.map(l => `<option value="${l.id}" ${String(selectedId)===String(l.id)?'selected':''}>${esc(l.code)}</option>`).join('');
}
function tankOptions(selectedId){
  return `<option value="">—</option>` + state.tanks.map(t => `<option value="${t.id}" ${selectedId===t.id?'selected':''}>${esc(t.id)}</option>`).join('');
}

function openMovementForm(tank=null, forcedType=''){
  modal(`
    <h3>Nouveau mouvement</h3>
    <div class="form-grid">
      <div class="two">
        <label>Type
          <select id="mvType">
            <option value="entree">Entrée</option>
            <option value="transfert">Transfert</option>
            <option value="sortie">Sortie</option>
            <option value="assemblage">Assemblage</option>
            <option value="correction_manuelle">Correction manuelle</option>
            <option value="autre">Autre</option>
          </select>
        </label>
        <label>Lot<select id="mvLot">${lotOptions(tank?.current_lot?.id)}</select></label>
      </div>
      <div class="two">
        <label>Source<select id="mvSource">${tankOptions(tank?.id)}</select></label>
        <label>Destination<select id="mvDest">${tankOptions('')}</select></label>
      </div>
      <div class="two">
        <label>Volume hL<input id="mvVolume" type="number" step="0.01"></label>
        <label>Nouveau volume (correction)<input id="mvNewVolume" type="number" step="0.01"></label>
      </div>
      <div id="entryFields" class="entry-fields hidden">
        <div class="two">
          <label>Poids du raisin (kg)<input id="mvGrapeWeight" type="number" step="0.01"></label>
          <label>Lecture brute du mustimètre<input id="mvMustimeterRaw" type="number" step="0.01" placeholder="ex. 1070 ou 1.070"></label>
        </div>
        <div class="two">
          <label>Température du moût (°C)<input id="mvTemp" type="number" step="0.1"></label>
          <label>M.V. corrigée à 20 °C<input id="mvCorrectedDensity" type="text" disabled placeholder="calcul automatique"></label>
        </div>
        <div class="two">
          <label>Sucres (g/L)<input id="mvSugarGL" type="text" disabled placeholder="calcul automatique"></label>
          <label>TAV probable calculé<input id="mvTav" type="text" disabled placeholder="calcul automatique"></label>
        </div>
        <div class="two">
          <label>Rendement jus (L / kg)<input id="mvYieldLkg" type="text" disabled placeholder="calcul automatique"></label>
          <label>Rendement jus (%)<input id="mvYieldPct" type="text" disabled placeholder="calcul automatique"></label>
        </div>
      </div>
      <label>Nom opération libre<input id="mvOpName" placeholder="Soutirage, ouillage..."></label>
      <label>Commentaire<textarea id="mvComment" rows="3"></textarea></label>
      <label><input id="mvImpact" type="checkbox" checked> Cette opération impacte le volume</label>
    </div>
    <div class="actions-row"><button id="saveMvBtn">Enregistrer</button><button class="secondary" onclick="document.getElementById('modal').classList.add('hidden')">Annuler</button></div>
  `);
  if (forcedType) el('#mvType').value = forcedType;

  function updateEntryPreview(){
    const type = el('#mvType').value;
    const box = el('#entryFields');
    box.classList.toggle('hidden', type !== 'entree');
    if (type !== 'entree') return;
    const corrected = correctedDensity20(el('#mvMustimeterRaw').value, el('#mvTemp').value);
    const rounded = Number.isFinite(corrected) ? Math.round(corrected) : null;
    const sugar = computeSugar(el('#mvMustimeterRaw').value, el('#mvTemp').value);
    const tav = computePotentialAbv(el('#mvMustimeterRaw').value, el('#mvTemp').value);
    const y = computeJuiceYield(el('#mvVolume').value, el('#mvGrapeWeight').value);
    el('#mvCorrectedDensity').value = Number.isFinite(corrected) ? `${corrected.toFixed(2)} (arrondie ${rounded})` : '';
    el('#mvSugarGL').value = Number.isFinite(sugar) ? sugar.toFixed(1) : '';
    el('#mvTav').value = Number.isFinite(tav) ? tav.toFixed(2) + ' % vol' : '';
    el('#mvYieldLkg').value = Number.isFinite(y.lkg) ? y.lkg.toFixed(3) : '';
    el('#mvYieldPct').value = Number.isFinite(y.pct) ? y.pct.toFixed(2) + ' %' : '';
  }
  ['#mvType','#mvVolume','#mvGrapeWeight','#mvMustimeterRaw','#mvTemp'].forEach(sel => el(sel).addEventListener('input', updateEntryPreview));
  el('#mvType').addEventListener('change', updateEntryPreview);
  updateEntryPreview();
  el('#saveMvBtn').onclick = async () => {
    try{
      await api('/api/movements', {method:'POST', body:{
        movement_type: el('#mvType').value,
        lot_id: el('#mvLot').value || null,
        source_tank_id: el('#mvSource').value || null,
        destination_tank_id: el('#mvDest').value || null,
        volume_hl: el('#mvVolume').value || null,
        new_volume_hl: el('#mvNewVolume').value || null,
        grape_weight_kg: el('#mvGrapeWeight').value || null,
        mustimeter_raw: el('#mvMustimeterRaw').value || null,
        must_temperature_c: el('#mvTemp').value || null,
        operation_name: el('#mvOpName').value || null,
        comment: el('#mvComment').value || '',
        impact_volume: el('#mvImpact').checked,
      }});
      closeModal();
      await refreshDataOnly();
    } catch(err){
      alert(err.message);
    }
  };
}

function openLotForm(lot=null){
  if (!state.editable) return;
  modal(`
    <h3>${lot ? 'Modifier' : 'Créer'} un lot</h3>
    <div class="form-grid">
      <label>Code lot<input id="lotCode" value="${esc(lot?.code || '')}"></label>
      <div class="two">
        <label>Millésime<input id="lotVintage" type="number" value="${lot?.vintage ?? ''}"></label>
        <label>Type<input id="lotType" value="${esc(lot?.wine_type || '')}"></label>
      </div>
      <label>Commentaire<textarea id="lotComment" rows="4">${esc(lot?.comment || '')}</textarea></label>
      <label><input id="lotActive" type="checkbox" ${lot?.active !== false ? 'checked' : ''}> Lot actif</label>
    </div>
    <div class="actions-row"><button id="saveLotBtn">Enregistrer</button><button class="secondary" onclick="document.getElementById('modal').classList.add('hidden')">Annuler</button></div>
  `);
  el('#saveLotBtn').onclick = async () => {
    const body = {
      code: el('#lotCode').value,
      vintage: el('#lotVintage').value || null,
      wine_type: el('#lotType').value,
      comment: el('#lotComment').value,
      active: el('#lotActive').checked,
    };
    try{
      if (lot) await api(`/api/lots/${lot.id}`, {method:'PUT', body});
      else await api('/api/lots', {method:'POST', body});
      closeModal();
      await refreshDataOnly();
    } catch(err){ alert(err.message); }
  };
}

function openEventForm(event=null){
  const starts = event?.starts_at ? event.starts_at.slice(0,16) : new Date().toISOString().slice(0,16);
  const ends = event?.ends_at ? event.ends_at.slice(0,16) : '';
  modal(`
    <h3>${event ? 'Modifier' : 'Créer'} un événement</h3>
    <div class="form-grid">
      <label>Titre<input id="evTitle" value="${esc(event?.title || '')}"></label>
      <div class="two">
        <label>Type<input id="evType" value="${esc(event?.event_type || 'operation cave')}"></label>
        <label>Statut<select id="evStatus"><option value="prevu">Prévu</option><option value="fait">Fait</option><option value="annule">Annulé</option></select></label>
      </div>
      <div class="two">
        <label>Début<input id="evStarts" type="datetime-local" value="${starts}"></label>
        <label>Fin<input id="evEnds" type="datetime-local" value="${ends}"></label>
      </div>
      <div class="two">
        <label>Cuve<select id="evTank">${tankOptions(event?.tank_id || '')}</select></label>
        <label>Lot<select id="evLot">${lotOptions(event?.lot_id || '')}</select></label>
      </div>
      <label>Assigné<select id="evUser"><option value="">—</option>${state.users.map(u => `<option value="${u.id}" ${String(event?.assigned_user_id)===String(u.id)?'selected':''}>${esc(u.full_name)}</option>`).join('')}</select></label>
      <label>Commentaire<textarea id="evComment" rows="4">${esc(event?.comment || '')}</textarea></label>
    </div>
    <div class="actions-row"><button id="saveEventBtn">Enregistrer</button><button class="secondary" onclick="document.getElementById('modal').classList.add('hidden')">Annuler</button></div>
  `);
  el('#evStatus').value = event?.status || 'prevu';
  el('#saveEventBtn').onclick = async () => {
    const body = {
      title: el('#evTitle').value,
      event_type: el('#evType').value,
      status: el('#evStatus').value,
      starts_at: el('#evStarts').value,
      ends_at: el('#evEnds').value || null,
      tank_id: el('#evTank').value || null,
      lot_id: el('#evLot').value || null,
      assigned_user_id: el('#evUser').value || null,
      comment: el('#evComment').value,
    };
    try{
      if (event) await api(`/api/events/${event.id}`, {method:'PUT', body});
      else await api('/api/events', {method:'POST', body});
      closeModal();
      await refreshDataOnly();
    } catch(err){ alert(err.message); }
  };
}

function setView(view){
  const titles = {
    dashboard:['Dashboard','Vue d’ensemble de la cave'],
    plan:['Plan de cave','Vue par zones dans l’ordre du fichier Excel'],
    lots:['Lots','Gestion des lots et des volumes associés'],
    calendar:['Calendrier','Vue mensuelle avec filtres'],
    history:['Historique','Traçabilité complète des actions'],
    alerts:['Alertes','Cuves à traiter, alertes système et événements en retard'],
  };
  els('.side-nav button').forEach(b => b.classList.toggle('active', b.dataset.view === view));
  els('.view').forEach(v => v.classList.remove('active'));
  el(`#view-${view}`).classList.add('active');
  el('#pageTitle').textContent = titles[view][0];
  el('#pageSubtitle').textContent = titles[view][1];
}

function bindGlobalEvents(){
  el('#loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try{
      await api('/api/login', {method:'POST', body:fd});
      el('#loginError').textContent = '';
      await refreshAll();
    } catch(err){
      el('#loginError').textContent = err.message;
    }
  });
  el('#logoutBtn').onclick = async () => { await api('/api/logout', {method:'POST'}); showLogin(); };
  els('.side-nav button').forEach(btn => btn.onclick = () => setView(btn.dataset.view));
  els('[data-view-jump]').forEach(btn => btn.onclick = () => setView(btn.dataset.viewJump));
  ['#zoneFilter','#statusFilter'].forEach(s => el(s).addEventListener('change', loadTanks));
  el('#searchInput').addEventListener('input', () => {
    clearTimeout(window.__searchTimer);
    window.__searchTimer = setTimeout(loadTanks, 180);
  });
  el('#refreshBtn').onclick = refreshDataOnly;
  el('#quickEntryBtn').onclick = () => openMovementForm(null, 'entree');
  el('#newMovementBtn').onclick = () => openMovementForm();
  el('#newLotBtn').onclick = () => openLotForm();
  el('#newEventBtn').onclick = () => openEventForm();
  el('#calendarPrevBtn').onclick = () => { state.calendarMonth = new Date(state.calendarMonth.getFullYear(), state.calendarMonth.getMonth()-1, 1); renderEvents(); };
  el('#calendarNextBtn').onclick = () => { state.calendarMonth = new Date(state.calendarMonth.getFullYear(), state.calendarMonth.getMonth()+1, 1); renderEvents(); };
  el('#calendarTodayBtn').onclick = () => { const now = new Date(); state.calendarMonth = new Date(now.getFullYear(), now.getMonth(), 1); state.calendarSelectedDate = now.toISOString().slice(0,10); renderEvents(); };
  ['#calendarTypeFilter','#calendarStatusFilter','#calendarUserFilter','#calendarTankFilter','#calendarLotFilter'].forEach(sel => el(sel).addEventListener('change', renderEvents));
  el('#calendarSearchInput').addEventListener('input', () => {
    clearTimeout(window.__calTimer);
    window.__calTimer = setTimeout(renderEvents, 150);
  });
  el('#modal').addEventListener('click', e => { if (e.target.id === 'modal') closeModal(); });
}

bindGlobalEvents();
refreshAll().catch(() => showLogin());
