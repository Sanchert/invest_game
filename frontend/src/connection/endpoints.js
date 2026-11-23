import { request } from './http.js';

const room = (code) => `/games/${encodeURIComponent(code)}`;

export const api = {
  config: () => request('/config'),
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
