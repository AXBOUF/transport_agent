'use strict';

// ── Config ─────────────────────────────────────────────────────────────────────

const SYDNEY     = [-33.8688, 151.2093];
const REFRESH_MS = 5_000;

const COLORS = {
  metro:        '#009FDB',
  sydneytrains: '#F5A623',
};

const STATUS_LABELS = {
  IN_TRANSIT_TO: 'In transit',
  STOPPED_AT:    'Stopped at stop',
  INCOMING_AT:   'Arriving',
};

const OCCUPANCY_LABELS = {
  EMPTY:                       'Empty',
  MANY_SEATS_AVAILABLE:        'Many seats',
  FEW_SEATS_AVAILABLE:         'Few seats',
  STANDING_ROOM_ONLY:          'Standing only',
  CRUSHED_STANDING_ROOM_ONLY:  'Very crowded',
  FULL:                        'Full',
  NOT_ACCEPTING_PASSENGERS:    'Not boarding',
};

// Map occupancy strings to 0-8 fill level — matches frontend OccupancyBars component
const OCC_LEVEL = {
  EMPTY:                      0,
  MANY_SEATS_AVAILABLE:       2,
  FEW_SEATS_AVAILABLE:        4,
  STANDING_ROOM_ONLY:         6,
  CRUSHED_STANDING_ROOM_ONLY: 7,
  FULL:                       8,
  NOT_ACCEPTING_PASSENGERS:   8,
};

// ── Themes ─────────────────────────────────────────────────────────────────────
// Tile URLs swap on theme change via tileLayer.setUrl() — no layer destroy/recreate.
// CSS data-theme attribute drives all UI colour variables.

const MAP_THEMES = {
  dark: {
    label:  'Dark',
    tile:   'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    css:    'dark',
    swatch: 'linear-gradient(135deg,#0f172a,#1e293b)',
  },
  midnight: {
    label:  'Midnight',
    tile:   'https://{s}.basemaps.cartocdn.com/dark_matter/{z}/{x}/{y}{r}.png',
    css:    'midnight',
    swatch: 'linear-gradient(135deg,#060e1a,#0a1628)',
  },
  cyberpunk: {
    label:  'Cyberpunk',
    tile:   'https://{s}.basemaps.cartocdn.com/dark_matter/{z}/{x}/{y}{r}.png',
    css:    'cyberpunk',
    swatch: 'linear-gradient(135deg,#080810,#0d0d1a)',
  },
  noir: {
    label:  'Noir',
    tile:   'https://{s}.basemaps.cartocdn.com/dark_matter_no_labels/{z}/{x}/{y}{r}.png',
    css:    'noir',
    swatch: 'linear-gradient(135deg,#000,#111)',
  },
  blueprint: {
    label:  'Blueprint',
    tile:   'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
    css:    'blueprint',
    swatch: 'linear-gradient(135deg,#0f2840,#1a3a5c)',
  },
  emerald: {
    label:  'Emerald',
    tile:   'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    css:    'emerald',
    swatch: 'linear-gradient(135deg,#031a11,#062c22)',
  },
};

let tileLayer    = null;
let currentTheme = localStorage.getItem('map-theme') || 'dark';

// ── State ─────────────────────────────────────────────────────────────────────

let map, markersLayer;
let stopsLayer      = null;
let stopsVisible    = false;
let routeLayers     = {};       // route name → L.LayerGroup of polylines
let highlightedRoute= null;     // route name currently highlighted (string)
let routesPanelOpen = true;
let currentTransport= 'metro';
let refreshTimer    = null;
let themePikerOpen  = false;

// ── Vehicle animation engine ──────────────────────────────────────────────────
// One rAF loop smoothly interpolates all markers between 5-second API polls.

const vehicleRegistry = new Map(); // vehicle_id → { marker, prevLat, prevLon, lat, lon, startTime, props }
let   animRafHandle   = null;

function startVehicleAnimLoop() {
  if (animRafHandle) return;
  const tick = (now) => {
    vehicleRegistry.forEach((v) => {
      if (v.prevLat === null) return;
      const t    = Math.min(1, (now - v.startTime) / REFRESH_MS);
      const ease = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t; // ease-in-out
      v.marker.setLatLng([
        v.prevLat + (v.lat - v.prevLat) * ease,
        v.prevLon + (v.lon - v.prevLon) * ease,
      ]);
    });
    animRafHandle = requestAnimationFrame(tick);
  };
  animRafHandle = requestAnimationFrame(tick);
}

// ── Map ───────────────────────────────────────────────────────────────────────

function initMap() {
  map = L.map('map', { center: SYDNEY, zoom: 11, zoomControl: true });

  const t = MAP_THEMES[currentTheme] || MAP_THEMES.dark;
  tileLayer = L.tileLayer(t.tile, {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19,
  }).addTo(map);

  markersLayer = L.layerGroup().addTo(map);
  startVehicleAnimLoop();

  map.on('click', () => closeTripPanel());
}

// ── Theme switching ───────────────────────────────────────────────────────────

function buildThemePicker() {
  const container = document.getElementById('theme-swatches');
  Object.entries(MAP_THEMES).forEach(([key, t]) => {
    const btn = document.createElement('button');
    btn.className     = 'theme-swatch' + (key === currentTheme ? ' active' : '');
    btn.dataset.theme = key;
    btn.title         = t.label;
    btn.innerHTML     = `<div class="theme-swatch-dot" style="background:${t.swatch}"></div>
                         <div class="theme-swatch-name">${t.label}</div>`;
    btn.onclick = () => applyTheme(key);
    container.appendChild(btn);
  });
}

function applyTheme(name) {
  const t = MAP_THEMES[name] || MAP_THEMES.dark;
  currentTheme = name;
  document.documentElement.setAttribute('data-theme', t.css);

  // Swap tile URL in-place — no layer destroy/recreate, no z-index flicker
  if (tileLayer) tileLayer.setUrl(t.tile);

  document.querySelectorAll('.theme-swatch').forEach(el => {
    el.classList.toggle('active', el.dataset.theme === name);
  });
  localStorage.setItem('map-theme', name);
}

function toggleThemePicker() {
  const picker = document.getElementById('theme-picker');
  themePikerOpen = !themePikerOpen;
  picker.classList.toggle('hidden', !themePikerOpen);
}

document.addEventListener('click', (e) => {
  const btn    = document.getElementById('theme-btn');
  const picker = document.getElementById('theme-picker');
  if (themePikerOpen && !picker.contains(e.target) && e.target !== btn) {
    themePikerOpen = false;
    picker.classList.add('hidden');
  }
});

// ── Delay helpers ─────────────────────────────────────────────────────────────

function delayColor(secs) {
  if (secs == null) return '#475569';
  if (secs <= 60)   return '#22c55e';
  if (secs <= 300)  return '#f97316';
  return '#ef4444';
}

function delayLabel(secs) {
  if (secs == null) return { text: 'No RT data', cls: 'delay-none' };
  if (secs <= 60)   return { text: 'On time',    cls: 'delay-ok'   };
  if (secs <= 300)  return { text: `+${Math.round(secs / 60)} min late`, cls: 'delay-warn' };
  return              { text: `+${Math.round(secs / 60)} min late`, cls: 'delay-bad' };
}

// ── Train-dot marker — exact design from frontend/src/styles.css ──────────────
// .train-dot.train-dot-clickable with --c CSS property; 34×22px pill

function makeTrainIcon(routeName, color) {
  return L.divIcon({
    className: '',
    html: `<div class="train-dot" style="--c:${color}"><span>${escHtml(routeName || '?')}</span></div>`,
    iconSize:   [34, 22],
    iconAnchor: [17, 11],
  });
}

// Tooltip HTML — transparent card matching frontend train-tooltip style
function makeTooltipHtml(routeName, destination, statusKey, delaySecs) {
  const dest   = destination || routeName || '—';
  const status = STATUS_LABELS[statusKey] || 'En route';
  const dl     = delayLabel(delaySecs);
  const dc     = delayColor(delaySecs);
  return `<div class="tt-inner" style="border-left-color:${dc}">
    <div class="tt-route">${escHtml(routeName || '—')} → <strong>${escHtml(dest)}</strong></div>
    <div class="tt-sub">${status} · ${dl.text}</div>
  </div>`;
}

// ── Occupancy bars — 8 blocks, numbered 8→1, matching frontend OccupancyBars ─

function buildOccBars(occupancyStr) {
  const level = OCC_LEVEL[occupancyStr];
  if (level === undefined) return '';
  const color = level <= 3 ? '#22c55e' : level <= 5 ? '#f59e0b' : '#f97316';
  return Array.from({ length: 8 }, (_, i) => {
    const filled = i < level;
    return `<div class="occ-bar${filled ? ' occ-filled' : ''}"${filled ? ` style="background:${color}"` : ''}>${8 - i}</div>`;
  }).join('');
}

// ── Route line highlighting ────────────────────────────────────────────────────
// Uses already-loaded routeLayers — instant, no extra API call.
// Matches frontend GeoJSON onEachFeature click handler (weight 7, opacity 1).

function highlightRouteLine(routeName, color) {
  clearRouteHighlight();
  const lg = routeLayers[routeName];
  if (!lg) return;
  highlightedRoute = routeName;
  lg.eachLayer(layer => {
    if (typeof layer.setStyle === 'function') {
      layer.setStyle({ weight: 7, opacity: 1, color });
      if (typeof layer.bringToFront === 'function') layer.bringToFront();
    }
  });
}

function clearRouteHighlight() {
  if (!highlightedRoute) return;
  const lg = routeLayers[highlightedRoute];
  if (lg) {
    lg.eachLayer(layer => {
      if (typeof layer.setStyle === 'function') {
        layer.setStyle({ weight: 3.5, opacity: 0.75 });
      }
    });
  }
  highlightedRoute = null;
}

// ── Trip side panel ───────────────────────────────────────────────────────────
// Matches LiveMap.tsx selected-train panel: color rail, dot states, occupancy bars.

async function openTripPanel(props, color) {
  const panel  = document.getElementById('trip-panel');
  const chip   = document.getElementById('trip-panel-chip');
  const dest   = document.getElementById('trip-panel-dest');
  const statusEl = document.getElementById('trip-panel-status');
  const body   = document.getElementById('trip-panel-body');

  // CSS variable drives banner border + timeline rail colour
  panel.style.setProperty('--tp-color', color);

  // Route chip
  chip.textContent   = props.route_name || (props.transport_type === 'metro' ? 'M' : '?');
  chip.style.background = color;

  // Destination banner
  dest.textContent = props.destination ? `→ ${props.destination}` : '';

  // Status row
  const dl  = delayLabel(props.delay_seconds);
  const occ = props.occupancy;
  const occBars = occ ? buildOccBars(occ) : '';
  const occLabel = occ ? (OCCUPANCY_LABELS[occ] || '') : '';
  statusEl.innerHTML = `
    <span class="tp-delay ${dl.cls}">${dl.text}</span>
    ${props.next_stop  ? `<span class="tp-meta">Next: <strong>${escHtml(props.next_stop)}</strong></span>` : ''}
    ${props.speed_kmh  ? `<span class="tp-meta">${props.speed_kmh} km/h</span>` : ''}
    ${occBars ? `<div class="tp-occ"><span class="tp-meta-label">${escHtml(occLabel)}</span><div class="occ-bars">${occBars}</div></div>` : ''}
  `;

  // Show panel immediately (slide-in animation from CSS)
  body.innerHTML = '<div class="trip-loading">Loading stops…</div>';
  panel.classList.remove('hidden');

  // Highlight the matching route polyline from already-loaded routeLayers
  highlightRouteLine(props.route_name, color);

  // Fetch live stop timeline
  if (props.trip_id) {
    try {
      const res = await fetch(
        `/api/trip/${encodeURIComponent(props.trip_id)}?transport_type=${props.transport_type || currentTransport}`
      );
      if (res.ok) {
        const data = await res.json();
        renderTripTimeline(data.stops, props.next_stop_seq, color);
      } else {
        body.innerHTML = '<div class="trip-loading">No stop data available.</div>';
      }
    } catch {
      body.innerHTML = '<div class="trip-loading">Could not load stops.</div>';
    }
  } else {
    body.innerHTML = '<div class="trip-loading">No trip ID available.</div>';
  }
}

function closeTripPanel() {
  document.getElementById('trip-panel').classList.add('hidden');
  clearRouteHighlight();
}

// Vertical rail + dot states matching LiveMap.tsx stop timeline.
// departed → filled dot, current → pulsing ring (current-dot), upcoming → hollow.
function renderTripTimeline(stops, nextStopSeq, color) {
  const body = document.getElementById('trip-panel-body');
  if (!stops?.length) {
    body.innerHTML = '<div class="trip-loading">No stop data available.</div>';
    return;
  }

  const items = stops.map((s) => {
    const isCurrent  = nextStopSeq != null && s.seq === nextStopSeq;
    const isDeparted = nextStopSeq != null ? s.seq < nextStopSeq : false;

    let dotHtml;
    if (isCurrent) {
      // Pulsing ring — matches LiveMap.tsx 📡 current stop indicator
      dotHtml = `<div class="tl-dot current-dot"></div>`;
    } else if (isDeparted) {
      dotHtml = `<div class="tl-dot filled"></div>`;
    } else {
      dotHtml = `<div class="tl-dot"></div>`;
    }

    const timeDisplay = s.predicted || s.scheduled || '';
    const delaySecs   = s.delay_secs;
    const delayHtml   = delaySecs != null && delaySecs > 60
      ? `<span class="tl-tag">+${Math.round(delaySecs / 60)}m</span>` : '';

    const rowCls = isCurrent ? 'tl-stop current' : isDeparted ? 'tl-stop departed' : 'tl-stop upcoming';

    return `
      <li class="${rowCls}">
        <div class="tl-dot-col">${dotHtml}</div>
        <div class="tl-info">
          <div class="tl-name">${escHtml(s.name || '')}</div>
          <div class="tl-time">${timeDisplay}${delayHtml}</div>
        </div>
      </li>`;
  }).join('');

  body.innerHTML = `
    <div class="timeline-wrap">
      <ul class="timeline">${items}</ul>
    </div>`;
}

// ── Network route lines ───────────────────────────────────────────────────────

function clearRouteLayers() {
  Object.values(routeLayers).forEach(lg => map.removeLayer(lg));
  routeLayers = {};
  highlightedRoute = null;
  document.getElementById('routes-list').innerHTML = '';
}

async function loadNetworkRoutes() {
  clearRouteLayers();
  try {
    const res  = await fetch(`/api/routes/shapes?transport_type=${currentTransport}`);
    if (!res.ok) return;
    const data = await res.json();

    const list = document.getElementById('routes-list');
    data.routes.forEach(route => {
      const lg = L.layerGroup();
      route.shapes.forEach(coords => {
        L.polyline(coords, {
          color: route.color, weight: 3.5, opacity: 0.75,
          lineJoin: 'round', lineCap: 'round',
        }).addTo(lg);
      });
      lg.addTo(map);
      routeLayers[route.name] = lg;

      const row = document.createElement('label');
      row.className = 'route-row';
      row.innerHTML = `
        <input type="checkbox" checked onchange="toggleRouteLine('${route.name}', this.checked)">
        <span class="route-swatch" style="background:${route.color}"></span>
        <span class="route-row-name">${route.name}</span>
        <span class="route-row-long">${route.long_name}</span>`;
      list.appendChild(row);
    });
  } catch(e) {
    console.warn('Route shapes load failed:', e);
  }
}

function toggleRouteLine(name, visible) {
  const lg = routeLayers[name];
  if (!lg) return;
  if (visible) lg.addTo(map); else map.removeLayer(lg);
}

function toggleRoutesPanel() {
  routesPanelOpen = !routesPanelOpen;
  document.getElementById('routes-list').style.display  = routesPanelOpen ? '' : 'none';
  document.getElementById('routes-chevron').textContent = routesPanelOpen ? '▾' : '▸';
}

// ── Stops layer ───────────────────────────────────────────────────────────────

async function loadStops() {
  if (stopsLayer) { map.removeLayer(stopsLayer); stopsLayer = null; }
  const netColor = COLORS[currentTransport] || '#6366f1';

  try {
    const res  = await fetch(`/api/stops?transport_type=${currentTransport}&platforms=true`);
    if (!res.ok) return;
    const data = await res.json();

    stopsLayer = L.layerGroup();
    data.stops.forEach(s => {
      const isStation = s.type === 1;
      const circle = L.circleMarker([s.lat, s.lon], {
        radius:      isStation ? 7 : 4,
        color:       netColor,
        fillColor:   isStation ? netColor : '#13151f',
        fillOpacity: isStation ? 0.25 : 1,
        weight:      isStation ? 2 : 1.5,
        opacity:     0.8,
      });
      const label = s.platform_code
        ? `<strong>${s.name}</strong><br><span style="color:#64748b">Platform ${s.platform_code}</span>`
        : `<strong>${s.name}</strong>`;
      circle.bindTooltip(label, { direction: 'top', opacity: 0.95 });
      stopsLayer.addLayer(circle);
    });
    stopsLayer.addTo(map);
  } catch(e) {
    console.warn('Stops load failed:', e);
  }
}

function toggleStops() {
  const btn = document.getElementById('stops-toggle');
  if (stopsVisible) {
    if (stopsLayer) { map.removeLayer(stopsLayer); stopsLayer = null; }
    stopsVisible = false;
    btn.textContent = 'Show stops';
    btn.classList.remove('active');
  } else {
    stopsVisible = true;
    btn.textContent = 'Hide stops';
    btn.classList.add('active');
    loadStops();
  }
}

// ── Vehicle refresh — smooth registry ─────────────────────────────────────────
// Existing markers glide to new positions; new ones appear at exact position;
// stale ones are removed. Uses train-dot pill icon matching frontend exactly.

async function refreshVehicles() {
  const btn = document.getElementById('refresh-btn');
  btn.classList.add('spinning');

  try {
    const res = await fetch(`/api/vehicles?transport_type=${currentTransport}`);
    if (!res.ok) throw new Error(res.statusText);
    const geojson = await res.json();

    const fallbackColor = COLORS[currentTransport] || '#6366f1';
    const seen          = new Set();
    const now           = performance.now();

    geojson.features.forEach(f => {
      const p          = f.properties;
      const [lon, lat] = f.geometry.coordinates;
      const id         = p.vehicle_id;
      if (!id) return;

      const color     = p.route_color || fallbackColor;
      const routeName = p.route_name  || (p.transport_type === 'metro' ? 'M1' : '?');
      seen.add(id);

      if (vehicleRegistry.has(id)) {
        // Smoothly glide existing marker to new position
        const v      = vehicleRegistry.get(id);
        const latlng = v.marker.getLatLng();
        v.prevLat    = latlng.lat;
        v.prevLon    = latlng.lng;
        v.lat        = lat;
        v.lon        = lon;
        v.startTime  = now;
        v.props      = p;
        v.marker.setIcon(makeTrainIcon(routeName, color));
        v.marker.setTooltipContent(makeTooltipHtml(routeName, p.destination, p.status, p.delay_seconds));
      } else {
        // Brand-new vehicle: place at exact position
        const marker = L.marker([lat, lon], {
          icon:              makeTrainIcon(routeName, color),
          riseOnHover:       true,
          bubblingMouseEvents: false,
        });

        // Tooltip — transparent card, no Leaflet chrome (train-tooltip class)
        marker.bindTooltip(
          makeTooltipHtml(routeName, p.destination, p.status, p.delay_seconds),
          { direction: 'top', offset: [0, -8], opacity: 1, className: 'train-tooltip' }
        );

        // Click → open trip side panel, matching SimulatedTrains click handler
        marker.on('click', (e) => {
          L.DomEvent.stopPropagation(e);
          openTripPanel(p, color);
        });

        markersLayer.addLayer(marker);
        vehicleRegistry.set(id, {
          marker,
          prevLat: null, prevLon: null,
          lat, lon,
          startTime: now,
          props: p,
          routeName,
          color,
        });
      }
    });

    // Remove vehicles that disappeared from the feed
    vehicleRegistry.forEach((v, id) => {
      if (!seen.has(id)) {
        markersLayer.removeLayer(v.marker);
        vehicleRegistry.delete(id);
      }
    });

    const count = seen.size;
    document.getElementById('vehicle-count').textContent = count;
    document.getElementById('last-updated').textContent  = new Date().toLocaleTimeString();
    document.getElementById('no-vehicles').classList.toggle('hidden', count > 0);
    document.getElementById('legend-metro').style.display        = currentTransport === 'metro' ? '' : 'none';
    document.getElementById('legend-sydneytrains').style.display = currentTransport === 'sydneytrains' ? '' : 'none';

  } catch(err) {
    console.error('Vehicle refresh failed:', err);
  } finally {
    btn.classList.remove('spinning');
  }
}

// ── Alerts ────────────────────────────────────────────────────────────────────

async function refreshAlerts() {
  try {
    const res    = await fetch(`/api/alerts?transport_type=${currentTransport}`);
    if (!res.ok) return;
    const alerts = await res.json();

    const bar    = document.getElementById('alerts-bar');
    const summary= document.getElementById('alerts-summary');
    const detail = document.getElementById('alerts-detail');

    if (!alerts.length) { bar.classList.add('hidden'); return; }

    bar.classList.remove('hidden');
    summary.textContent = `${alerts.length} active alert${alerts.length !== 1 ? 's' : ''}`;
    detail.innerHTML = alerts.map(a => `
      <div class="alert-item">
        <strong>${a.header || 'Service Alert'}</strong>
        ${a.description ? `<br><span>${a.description}</span>` : ''}
        ${a.routes?.length ? `<br><span>Routes: ${a.routes.join(', ')}</span>` : ''}
      </div>`).join('');
  } catch(err) {
    console.error('Alerts refresh failed:', err);
  }
}

async function refreshAll() {
  await Promise.all([refreshVehicles(), refreshAlerts()]);
}

function startAutoRefresh() {
  clearInterval(refreshTimer);
  refreshTimer = setInterval(refreshAll, REFRESH_MS);
}

// ── Transport switch ──────────────────────────────────────────────────────────

function onTransportChange() {
  currentTransport = document.getElementById('transport-select').value;
  vehicleRegistry.forEach(v => markersLayer.removeLayer(v.marker));
  vehicleRegistry.clear();
  closeTripPanel();
  document.getElementById('vehicle-count').textContent = '—';
  loadNetworkRoutes();
  refreshAll();
  if (stopsVisible) loadStops();
}

// ── Alert toggle ──────────────────────────────────────────────────────────────

function toggleAlerts() {
  const detail = document.getElementById('alerts-detail');
  const btn    = document.querySelector('.alerts-toggle');
  const hidden = detail.classList.toggle('hidden');
  btn.textContent = hidden ? 'Details ▾' : 'Hide ▴';
}

// ── Chat ──────────────────────────────────────────────────────────────────────

const NET_COLORS = {
  'sydney trains': '#F5A623',
  'sydneytrains':  '#F5A623',
  'metro':         '#009FDB',
};

function renderMarkdown(text) {
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>');
}

function buildServiceCards(rows) {
  return rows.map(([departs, arrives, destination, fromStop, toStop, network]) => {
    const net   = (network || '').trim();
    const color = NET_COLORS[net.toLowerCase()] || '#6366f1';
    return `
      <div class="svc-card">
        <div class="svc-times">
          <span class="svc-dep">${departs.trim()}</span>
          <span class="svc-arrow">→</span>
          <span class="svc-arr">${arrives.trim()}</span>
          <span class="svc-badge" style="background:${color}22;color:${color}">${net}</span>
        </div>
        <div class="svc-dest">${destination.trim()}</div>
        <div class="svc-stops">${fromStop.trim()} → ${toStop.trim()}</div>
      </div>`;
  }).join('');
}

function parseAndRender(text) {
  const lines   = text.split('\n');
  const svcRows = [];
  const rest    = [];
  for (const line of lines) {
    if (line.startsWith('SVCROW:')) {
      const parts = line.slice(7).split('|');
      if (parts.length >= 5) svcRows.push(parts);
    } else {
      rest.push(line);
    }
  }
  let html = renderMarkdown(rest.join('\n').trim());
  if (svcRows.length) html += `<div class="svc-cards">${buildServiceCards(svcRows)}</div>`;
  return html;
}

function appendMsg(text, role) {
  const messages = document.getElementById('messages');
  const div      = document.createElement('div');
  div.className  = `msg ${role}`;

  if (role !== 'user') {
    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.innerHTML = `<img src="/design/Train_Mode_White_Background_400x400.png" class="avatar-img" alt=""/>`;
    div.appendChild(avatar);
  }

  const bubble     = document.createElement('div');
  bubble.className = 'bubble';
  bubble.innerHTML = (role === 'user') ? escHtml(text) : parseAndRender(text);
  div.appendChild(bubble);
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return div;
}

function escHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ── Chart ─────────────────────────────────────────────────────────────────────

const CHART_PALETTE = [
  '#6366f1','#F5A623','#009FDB','#22c55e','#ef4444',
  '#a855f7','#ec4899','#14b8a6','#f97316','#84cc16',
];

let activeChart = null;

function renderChart(spec) {
  const overlay = document.getElementById('chart-overlay');
  const canvas  = document.getElementById('chart-canvas');
  document.getElementById('chart-title-label').textContent = spec.title || '';

  if (activeChart) { activeChart.destroy(); activeChart = null; }

  const colors = spec.datasets.map((d, i) => d.color || CHART_PALETTE[i % CHART_PALETTE.length]);
  const isPie  = spec.type === 'pie' || spec.type === 'doughnut';

  activeChart = new Chart(canvas, {
    type: spec.type,
    data: {
      labels: spec.labels,
      datasets: spec.datasets.map((d, i) => ({
        label:           d.label,
        data:            d.data,
        backgroundColor: isPie
          ? spec.datasets.map((_, j) => CHART_PALETTE[j % CHART_PALETTE.length])
          : spec.type === 'line' ? `${colors[i]}33` : colors[i],
        borderColor:     colors[i],
        borderWidth:     spec.type === 'line' ? 2 : isPie ? 2 : 0,
        fill:            spec.type === 'line',
        tension:         0.35,
        pointRadius:     spec.type === 'line' ? 3 : 0,
        pointHoverRadius:spec.type === 'line' ? 5 : 0,
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 400 },
      plugins: {
        title:  { display: false },
        legend: {
          display: spec.datasets.length > 1 || isPie,
          labels: { color: '#94a3b8', font: { size: 11, family: 'Roboto' }, boxWidth: 12, padding: 12 },
        },
        tooltip: {
          backgroundColor: '#13151f',
          borderColor: '#2d3555',
          borderWidth: 1,
          titleColor: '#f1f5f9',
          bodyColor:  '#94a3b8',
          titleFont:  { family: 'Roboto', weight: 'bold' },
          bodyFont:   { family: 'Roboto' },
        },
      },
      scales: isPie ? {} : {
        x: {
          ticks: { color: '#64748b', font: { size: 11, family: 'Roboto' } },
          grid:  { color: '#1e2235' },
          title: spec.x_label
            ? { display: true, text: spec.x_label, color: '#64748b', font: { size: 11, family: 'Roboto' } }
            : { display: false },
        },
        y: {
          ticks: { color: '#64748b', font: { size: 11, family: 'Roboto' } },
          grid:  { color: '#1e2235' },
          title: spec.y_label
            ? { display: true, text: spec.y_label, color: '#64748b', font: { size: 11, family: 'Roboto' } }
            : { display: false },
          beginAtZero: true,
        },
      },
    },
  });

  overlay.classList.remove('hidden');
}

function closeChart() {
  document.getElementById('chart-overlay').classList.add('hidden');
  if (activeChart) { activeChart.destroy(); activeChart = null; }
}

// ── Tool badges ───────────────────────────────────────────────────────────────

const TOOL_LABELS = {
  get_next_services:   '📅 timetable',
  get_live_departures: '🔴 live departures',
  get_active_alerts:   '⚠️ alerts',
  get_vehicle_position:'📍 vehicles',
  get_delay_trend:     '📈 delay trend',
  get_worst_delays:    '⏱ worst delays',
  list_tables:         '🗄 tables',
  describe_table:      '📋 schema',
  run_sql:             '🔍 SQL',
  render_chart:        '📊 chart',
};

function appendToolBadges(tools, parentEl) {
  if (!tools?.length) return;
  const row = document.createElement('div');
  row.className = 'tool-badges';
  tools.forEach(t => {
    const b = document.createElement('span');
    b.className   = 'tool-badge';
    b.textContent = TOOL_LABELS[t] || t;
    row.appendChild(b);
  });
  parentEl.querySelector('.bubble').appendChild(row);
}

// ── Send message ──────────────────────────────────────────────────────────────

async function sendMessage() {
  const input    = document.getElementById('chat-input');
  const btn      = document.getElementById('send-btn');
  const question = input.value.trim();
  if (!question) return;

  input.value    = '';
  input.disabled = true;
  btn.disabled   = true;

  appendMsg(question, 'user');
  const thinking = appendMsg('Thinking…', 'agent thinking');

  try {
    const res  = await fetch('/api/chat', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ question }),
    });
    const data = await res.json();
    thinking.remove();
    const msgEl = appendMsg(data.answer || data.detail || 'No response.', 'agent');
    appendToolBadges(data.tools_used, msgEl);
    if (data.chart) renderChart(data.chart);
  } catch {
    thinking.remove();
    appendMsg('Could not reach the agent. Is the server running?', 'agent');
  } finally {
    input.disabled = false;
    btn.disabled   = false;
    input.focus();
  }
}

// ── Boot ──────────────────────────────────────────────────────────────────────

document.documentElement.setAttribute('data-theme',
  (MAP_THEMES[currentTheme] || MAP_THEMES.dark).css);

initMap();
buildThemePicker();
loadNetworkRoutes();
refreshAll();
startAutoRefresh();
