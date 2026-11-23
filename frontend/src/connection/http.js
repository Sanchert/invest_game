/** The only place in the client that talks to the network. */

export const API_BASE = '/api';

/** `ApiError.code` when the server could not be reached at all. */
export const NETWORK_ERROR = 'network';

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export async function request(path, { method = 'GET', token, body } = {}) {
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (token) headers['X-Team-Token'] = token;
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, NETWORK_ERROR, NETWORK_ERROR);
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
