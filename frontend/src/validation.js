/** Checks for the forms, run while the person types. Pure functions: they return error
 *  descriptions `{ key, vars }` (the screen turns them into text), never messages. */

export const LIMITS = {
  turns: { min: 1, max: 20 },
  minutes: { min: 0, max: 60 },
  seconds: { min: 0, max: 59 },
  turnSeconds: { min: 10, max: 3600 },
  startups: { min: 1, max: 12 },
  nameLength: 30,
};

export const RESULTS_SECONDS = 15; // the pause between turns (the server's setting)
export const ROOM_CODE = /^[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{5}$/;

const WHOLE = /^\d+$/;

function whole(value, { min, max }) {
  const text = String(value ?? '').trim();
  if (text === '') return { error: { key: 'errRequired' } };
  if (!WHOLE.test(text)) return { error: { key: 'errWhole' } };
  const n = Number(text);
  if (n < min || n > max) return { error: { key: 'errRange', vars: { min, max } } };
  return { n };
}

/** values: { turns, minutes, seconds, startups } as typed (strings).
 *  library: { turnsAvailable, startupsAvailable } as reported by the server (may be empty).
 *  Returns { errors, valid, turnSeconds, totalSeconds }. */
export function validateGameForm(values, library = {}) {
  const errors = {};

  const turns = whole(values.turns, LIMITS.turns);
  if (turns.error) errors.turns = turns.error;
  else if (library.turnsAvailable && turns.n > library.turnsAvailable) {
    errors.turns = { key: 'errTurnsLibrary', vars: { n: library.turnsAvailable } };
  }

  const minutes = whole(values.minutes, LIMITS.minutes);
  if (minutes.error) errors.minutes = minutes.error;
  const seconds = whole(values.seconds, LIMITS.seconds);
  if (seconds.error) errors.seconds = seconds.error;

  let turnSeconds = null;
  if (!errors.minutes && !errors.seconds) {
    turnSeconds = minutes.n * 60 + seconds.n;
    if (turnSeconds < LIMITS.turnSeconds.min) errors.duration = { key: 'errTurnShort', vars: { n: LIMITS.turnSeconds.min } };
    else if (turnSeconds > LIMITS.turnSeconds.max) errors.duration = { key: 'errTurnLong' };
  }

  const startups = whole(values.startups, LIMITS.startups);
  if (startups.error) errors.startups = startups.error;
  else if (library.startupsAvailable && startups.n > library.startupsAvailable) {
    errors.startups = { key: 'errStartupsLibrary', vars: { n: library.startupsAvailable } };
  }

  const valid = Object.keys(errors).length === 0;
  const totalSeconds = valid
    ? turns.n * turnSeconds + (turns.n - 1) * RESULTS_SECONDS
    : null;
  return { errors, valid, turnSeconds: errors.duration ? null : turnSeconds, totalSeconds };
}

export const cleanName = (name) => String(name ?? '').split(/\s+/).filter(Boolean).join(' ');

/** values: { code, name }. `code` is ignored when the room is already known (fixedCode). */
export function validateJoin({ code, name }, { needCode = true, takenNames = [] } = {}) {
  const errors = {};
  if (needCode) {
    const text = String(code ?? '').trim().toUpperCase();
    if (text === '') errors.code = { key: 'errRequired' };
    else if (!ROOM_CODE.test(text)) errors.code = { key: 'errCode' };
  }
  const clean = cleanName(name);
  if (clean === '') errors.name = { key: 'errRequired' };
  else if (clean.length > LIMITS.nameLength) errors.name = { key: 'errName', vars: { max: LIMITS.nameLength } };
  else if (takenNames.includes(clean)) errors.name = { key: 'errNameTaken' };
  return { errors, valid: Object.keys(errors).length === 0 };
}
