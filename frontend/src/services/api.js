const API_BASE = import.meta.env.VITE_API_URL || window.location.origin;

export async function fetchEvents(params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v != null) qs.set(k, v); });
  const resp = await fetch(`${API_BASE}/api/events?${qs}`);
  return resp.json();
}

export async function searchEvents(query) {
  const resp = await fetch(`${API_BASE}/api/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(query),
  });
  return resp.json();
}

export async function getRelationships(eventId, limit = 20) {
  const resp = await fetch(`${API_BASE}/api/relationships/${eventId}?limit=${limit}`);
  return resp.json();
}

export async function getFeedStatuses() {
  const resp = await fetch(`${API_BASE}/api/feeds`);
  return resp.json();
}

export async function refreshFeeds() {
  const resp = await fetch(`${API_BASE}/api/feeds/refresh`, { method: 'POST' });
  return resp.json();
}

export async function getStats() {
  const resp = await fetch(`${API_BASE}/api/stats`);
  return resp.json();
}

export async function searchEntities(q) {
  const resp = await fetch(`${API_BASE}/api/entities?q=${encodeURIComponent(q)}`);
  return resp.json();
}
