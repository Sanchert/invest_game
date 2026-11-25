import { useEffect, useState } from 'react';
import { api, saveSession, useRoomStatus } from './connection/index.js';
import Field from './Field.jsx';
import { t } from './strings.js';
import { cleanName, LIMITS, ROOM_CODE, validateJoin } from './validation.js';

const STORAGE_CODE = 'join_room_code';
const STORAGE_NAME = 'join_team_name';

/** Team sign-up. `fixedCode` is set when the room code is already in the URL.
 *  The code, the name and the room itself are checked while the person types.
 *  Values are persisted in sessionStorage so they survive page reloads.
 *  They are cleared when the tab is closed or the player leaves the game. */
export default function JoinForm({ fixedCode, onJoined }) {
  const [code, setCode] = useState(() => {
    if (fixedCode) return fixedCode;
    return sessionStorage.getItem(STORAGE_CODE) || '';
  });
  const [name, setName] = useState(() => sessionStorage.getItem(STORAGE_NAME) || '');
  const [touched, setTouched] = useState({});
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  // Persist values across page reloads
  useEffect(() => { sessionStorage.setItem(STORAGE_CODE, code); }, [code]);
  useEffect(() => { sessionStorage.setItem(STORAGE_NAME, name); }, [name]);

  const room = (fixedCode || code).trim().toUpperCase();
  const roomLooksRight = ROOM_CODE.test(room);
  const lookup = useRoomStatus(room, roomLooksRight);
  const { errors, valid } = validateJoin({ code, name }, {
    needCode: !fixedCode,
    takenNames: lookup.teams,
  });

  let roomError = null;
  if (roomLooksRight && lookup.status === 'notfound') roomError = { key: 'errRoomNotFound' };
  if (roomLooksRight && lookup.status === 'started') roomError = { key: 'errRoomStarted' };

  const touch = (field) => () => setTouched((prev) => ({ ...prev, [field]: true }));
  const codeError = roomError
    || (errors.code && (touched.code || code.trim().length >= 5) ? errors.code : null);
  const nameError = errors.name && (touched.name || errors.name.key !== 'errRequired') ? errors.name : null;
  const checking = roomLooksRight && lookup.status === 'checking';
  const canSubmit = valid && !roomError && !checking && !busy;

  const submit = async (event) => {
    event.preventDefault();
    if (!canSubmit) return;
    setBusy(true);
    setError('');
    try {
      const joined = await api.join(room, cleanName(name));
      const session = { token: joined.token, teamId: joined.team_id, name: joined.name };
      saveSession(room, session);
      onJoined(room, session);
    } catch (err) {
      setError(err.status === 404 ? t('gameNotFound') : err.message);
      setBusy(false);
    }
  };

  return (
    <form className="panel" onSubmit={submit} noValidate>
      <h2>{t('joinTitle')}</h2>
      {!fixedCode && (
        <Field id="join-code" label={t('roomCode')} value={code} maxLength={8}
          onChange={(e) => setCode(e.target.value.toUpperCase())} onBlur={touch('code')}
          autoCapitalize="characters" autoComplete="off" spellCheck={false} className="code-input"
          error={codeError}
          hint={checking ? t('checkingRoom') : null}
          ok={roomLooksRight && lookup.status === 'open' ? t('roomFound') : null} />
      )}
      {fixedCode && roomError && <p className="field-error" role="alert">{t(roomError.key)}</p>}
      <Field id="join-name" label={t('teamName')} value={name} maxLength={LIMITS.nameLength}
        onChange={(e) => setName(e.target.value)} onBlur={touch('name')}
        autoComplete="off" error={nameError} />
      {error && <p className="error" role="alert">{error}</p>}
      <button className="btn primary" disabled={!canSubmit}>{t('joinGame')}</button>
    </form>
  );
}
