'use strict';

// ── Config ────────────────────────────────────────────────────────────────────

const SYDNEY = [-33.8688, 151.2093];
const REFRESH_MS = 30_000;

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

// ── State ─────────────────────────────────────────────────────────────────────

let map, markersLayer;
let currentTransport = 'metro';
let refreshTimer = null;

// ── Map ───────────────────────────────────────────────────────────────────────

function initMap() {
  map = L.map('map', {
    center: SYDNEY,
    zoom: 11,
    zoomControl: true,
  });

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19,
  }).addTo(map);

  markersLayer = L.layerGroup().addTo(map);
}

// ── Vehicle markers ───────────────────────────────────────────────────────────

function makeIcon(bearing, color) {
  // Rotate whole marker so the pip at top points in direction of travel.
  const rotation = bearing != null ? bearing : 0;
  const pip = bearing != null
    ? `<div class="v-pip"></div>`
    : '';
  return L.divIcon({
    className: '',
    html: `<div class="v-marker" style="background:${color};transform:rotate(${rotation}deg)">${pip}</div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
    popupAnchor: [0, -14],
  });
}

function makePopup(p) {
  const color = COLORS[p.transport_type] || '#6366f1';
  const status = STATUS_LABELS[p.status] || p.status || '—';
  const occupancy = OCCUPANCY_LABELS[p.occupancy] || p.occupancy || null;

  const rows = [
    ['Vehicle',  p.vehicle_id],
    ['Status',   status],
    p.at_stop       ? ['At stop',   p.at_stop]                    : null,
    p.speed_kmh     ? ['Speed',     `${p.speed_kmh} km/h`]        : null,
    occupancy       ? ['Occupancy', occupancy]                     : null,
    p.bearing != null ? ['Bearing', `${Math.round(p.bearing)}°`]  : null,
    ['Updated',  p.as_of || '—'],
  ]
    .filter(Boolean)
    .map(([label, value]) =>
      `<div class="popup-row"><span class="label">${label}</span><span class="value">${value}</span></div>`
    )
    .join('');

  return `
    <div class="popup-route">${p.route}</div>
    <span class="popup-badge" style="background:${color}22;color:${color}">${p.transport_type}</span>
    ${rows}
  `;
}

// ── Data fetching ─────────────────────────────────────────────────────────────

async function refreshVehicles() {
  const btn = document.getElementById('refresh-btn');
  btn.classList.add('spinning');

  try {
    const res = await fetch(`/api/vehicles?transport_type=${currentTransport}`);
    if (!res.ok) throw new Error(res.statusText);
    const geojson = await res.json();

    markersLayer.clearLayers();

    const color = COLORS[currentTransport] || '#6366f1';
    const count = geojson.features.length;

    geojson.features.forEach(f => {
      const [lon, lat] = f.geometry.coordinates;
      const marker = L.marker([lat, lon], {
        icon: makeIcon(f.properties.bearing, color),
      });
      marker.bindPopup(makePopup(f.properties), { maxWidth: 240, minWidth: 200 });
      markersLayer.addLayer(marker);
    });

    document.getElementById('vehicle-count').textContent = count;
    document.getElementById('last-updated').textContent = new Date().toLocaleTimeString();

    // Show/hide "no vehicles" overlay
    const noV = document.getElementById('no-vehicles');
    noV.classList.toggle('hidden', count > 0);

    // Update legend visibility
    document.getElementById('legend-metro').style.display =
      currentTransport === 'metro' ? '' : 'none';
    document.getElementById('legend-sydneytrains').style.display =
      currentTransport === 'sydneytrains' ? '' : 'none';

  } catch (err) {
    console.error('Vehicle refresh failed:', err);
  } finally {
    btn.classList.remove('spinning');
  }
}

async function refreshAlerts() {
  try {
    const res = await fetch(`/api/alerts?transport_type=${currentTransport}`);
    if (!res.ok) return;
    const alerts = await res.json();

    const bar    = document.getElementById('alerts-bar');
    const summary = document.getElementById('alerts-summary');
    const detail = document.getElementById('alerts-detail');

    if (!alerts.length) {
      bar.classList.add('hidden');
      return;
    }

    bar.classList.remove('hidden');
    summary.textContent = `${alerts.length} active alert${alerts.length !== 1 ? 's' : ''}`;
    detail.innerHTML = alerts.map(a => `
      <div class="alert-item">
        <strong>${a.header || 'Service Alert'}</strong>
        ${a.description ? `<br><span>${a.description}</span>` : ''}
        ${a.routes?.length ? `<br><span>Routes: ${a.routes.join(', ')}</span>` : ''}
      </div>
    `).join('');
  } catch (err) {
    console.error('Alerts refresh failed:', err);
  }
}

async function refreshAll() {
  await Promise.all([refreshVehicles(), refreshAlerts()]);
}

// ── Auto-refresh ──────────────────────────────────────────────────────────────

function startAutoRefresh() {
  clearInterval(refreshTimer);
  refreshTimer = setInterval(refreshAll, REFRESH_MS);
}

// ── Transport type switch ─────────────────────────────────────────────────────

function onTransportChange() {
  currentTransport = document.getElementById('transport-select').value;
  markersLayer.clearLayers();
  document.getElementById('vehicle-count').textContent = '—';
  refreshAll();
}

// ── Toggle alert detail ───────────────────────────────────────────────────────

function toggleAlerts() {
  const detail = document.getElementById('alerts-detail');
  const btn = document.querySelector('.alerts-toggle');
  const hidden = detail.classList.toggle('hidden');
  btn.textContent = hidden ? 'Details ▾' : 'Hide ▴';
}

// ── Chat ──────────────────────────────────────────────────────────────────────

function appendMsg(text, role) {
  const messages = document.getElementById('messages');

  const div = document.createElement('div');
  div.className = `msg ${role}`;

  if (role !== 'user') {
    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = '🤖';
    div.appendChild(avatar);
  }

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  div.appendChild(bubble);

  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return div;
}

async function sendMessage() {
  const input = document.getElementById('chat-input');
  const btn   = document.getElementById('send-btn');
  const question = input.value.trim();
  if (!question) return;

  input.value = '';
  input.disabled = true;
  btn.disabled = true;

  appendMsg(question, 'user');
  const thinking = appendMsg('Thinking…', 'agent thinking');

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();
    thinking.remove();
    appendMsg(data.answer || data.detail || 'No response.', 'agent');
  } catch {
    thinking.remove();
    appendMsg('Could not reach the agent. Is the server running?', 'agent');
  } finally {
    input.disabled = false;
    btn.disabled = false;
    input.focus();
  }
}

// ── Boot ──────────────────────────────────────────────────────────────────────

initMap();
refreshAll();
startAutoRefresh();
