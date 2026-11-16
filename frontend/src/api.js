export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request(path, { method = 'GET', token, body } = {}) {
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (token) headers['X-Team-Token'] = token;
  let res;
  try {
    res = await fetch(`/api${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, 'network', 'network');
  }
  if (res.status === 204) return null;
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* empty or non-JSON body */
  }
  if (!res.ok) {
    const detail = Array.isArray(data?.detail) ? data.detail.map((d) => d.msg).join('; ') : null;
    throw new ApiError(res.status, data?.code || 'error', data?.message || detail || res.statusText);
  }
  return data;
}

const room = (code) => `/games/${encodeURIComponent(code)}`;

export const api = {
  createGame: (body) => request('/games', { method: 'POST', body }),
  board: (code) => request(`${room(code)}/board`),
  join: (code, name) => request(`${room(code)}/join`, { method: 'POST', body: { name } }),
  me: (code, token) => request(`${room(code)}/me`, { token }),
  ready: (code, token) => request(`${room(code)}/ready`, { method: 'POST', token }),
  unready: (code, token) => request(`${room(code)}/unready`, { method: 'POST', token }),
  leave: (code, token) => request(`${room(code)}/leave`, { method: 'POST', token }),
  trade: (code, token, startup_id, shares) =>
    request(`${room(code)}/trade`, { method: 'POST', token, body: { startup_id, shares } }),
  insider: (code, token) => request(`${room(code)}/insider`, { method: 'POST', token }),
};

const key = (code) => `invest:${code.toUpperCase()}`;

export function saveSession(code, session) {
  try {
    localStorage.setItem(key(code), JSON.stringify(session));
  } catch {
    /* storage can be blocked; the player just has to rejoin after a refresh */
  }
}

export function loadSession(code) {
  try {
    return JSON.parse(localStorage.getItem(key(code)) || 'null');
  } catch {
    return null;
  }
}

export function clearSession(code) {
  try {
    localStorage.removeItem(key(code));
  } catch {
    /* ignore */
  }
}
