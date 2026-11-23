import { useState } from 'react';
import { api, saveSession } from './connection/index.js';
import { t } from './strings.js';


function JoinForm({ fixedCode, onJoined }) {
  const [code, setCode] = useState(fixedCode || '');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    const room = code.trim().toUpperCase();
    try {
      const joined = await api.join(room, name);
      const session = { token: joined.token, teamId: joined.team_id, name: joined.name };
      saveSession(room, session);
      onJoined(room, session);
    } catch (err) {
      setError(err.status === 404 ? t('gameNotFound') : err.message);
      setBusy(false);
    }
  };

  return (
    <form className="panel" onSubmit={submit}>
      <h2>{t('joinTitle')}</h2>
      {!fixedCode && (
        <label className="field">
          <span>{t('roomCode')}</span>
          <input value={code} onChange={(e) => setCode(e.target.value.toUpperCase())}
            maxLength={8} autoCapitalize="characters" autoComplete="off" spellCheck={false}
            className="code-input" required />
        </label>
      )}
      <label className="field">
        <span>{t('teamName')}</span>
        <input value={name} onChange={(e) => setName(e.target.value)} maxLength={30}
          autoComplete="off" required />
      </label>
      {error && <p className="error" role="alert">{error}</p>}
      <button className="btn primary" disabled={busy || !name.trim() || !code.trim()}>
        {t('joinGame')}
      </button>
    </form>
  );
}

export default JoinForm;
