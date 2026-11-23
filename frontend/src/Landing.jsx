import { useState } from 'react';
import CopyButton from './CopyButton.jsx';
import { api, isLocalOnly, useServerAddress } from './connection/index.js';
import JoinForm from './JoinForm.jsx';
import { t } from './strings.js';

function HostForm() {
  const [turns, setTurns] = useState(3);
  const [minutes, setMinutes] = useState(10);
  const [seconds, setSeconds] = useState(0);
  const [startups, setStartups] = useState(5);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    const turnSeconds = Number(minutes) * 60 + Number(seconds);
    if (turnSeconds < 10) {
      setError(t('turnTooShort'));
      return;
    }
    setBusy(true);
    setError('');
    try {
      const game = await api.createGame({
        turns: Number(turns),
        turn_seconds: turnSeconds,
        startups_count: Number(startups),
      });
      window.location.assign(`/board/${game.room_code}`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <form className="panel" onSubmit={submit}>
      <h2>{t('hostTitle')}</h2>
      <p className="muted">{t('hostText')}</p>
      <label className="field">
        <span>{t('turns')}</span>
        <input type="number" min="1" max="20" value={turns}
          onChange={(e) => setTurns(e.target.value)} required />
      </label>
      <fieldset className="field">
        <legend>{t('turnLength')}</legend>
        <div className="inline">
          <label>
            <input type="number" min="0" max="60" value={minutes}
              onChange={(e) => setMinutes(e.target.value)} aria-label={t('minutes')} />
            <small>{t('minutes')}</small>
          </label>
          <label>
            <input type="number" min="0" max="59" value={seconds}
              onChange={(e) => setSeconds(e.target.value)} aria-label={t('seconds')} />
            <small>{t('seconds')}</small>
          </label>
        </div>
      </fieldset>
      <label className="field">
        <span>{t('startupCount')}</span>
        <input type="number" min="1" max="12" value={startups}
          onChange={(e) => setStartups(e.target.value)} required />
      </label>
      {error && <p className="error" role="alert">{error}</p>}
      <button className="btn primary" disabled={busy}>{t('createGame')}</button>
    </form>
  );
}

function AddressBar() {
  const base = useServerAddress();
  return (
    <section className="panel address-bar">
      <div>
        <p className="muted">{t('playersJoinAt')}</p>
        <p className="address-text">{base}</p>
        {isLocalOnly(base) && <p className="error">{t('localOnlyHint')}</p>}
      </div>
      <CopyButton text={base} />
    </section>
  );
}

export default function Landing() {
  return (
    <div className="landing">
      <h1>{t('appName')}</h1>
      <AddressBar />
      <div className="landing-grid">
        <JoinForm onJoined={(room) => window.location.assign(`/play/${room}`)} />
        <HostForm />
      </div>
    </div>
  );
}
