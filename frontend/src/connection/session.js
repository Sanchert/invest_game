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
