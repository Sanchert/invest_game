import { useState } from 'react';
import CopyButton from './CopyButton.jsx';
import { api, isLocalOnly, useServerAddress, useServerConfig } from './connection/index.js';
import Field, { message } from './Field.jsx';
import JoinForm from './JoinForm.jsx';
import { t } from './strings.js';
import { validateGameForm } from './validation.js';

function HostForm() {
  const [values, setValues] = useState({ turns: '3', minutes: '10', seconds: '0', startups: '5' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const config = useServerConfig();
  const library = { turnsAvailable: config.turns_available, startupsAvailable: config.startups_available };
  const { errors, valid, turnSeconds, totalSeconds } = validateGameForm(values, library);
  const set = (name) => (event) => setValues((prev) => ({ ...prev, [name]: event.target.value }));

  const submit = async (event) => {
    event.preventDefault();
    if (!valid || busy) return;
    setBusy(true);
    setError('');
    try {
      const game = await api.createGame({
        turns: Number(values.turns),
        turn_seconds: turnSeconds,
        startups_count: Number(values.startups),
      });
      window.location.assign(`/board/${game.room_code}`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  const durationError = errors.duration || errors.minutes || errors.seconds;
  return (
    <form className="panel" onSubmit={submit} noValidate>
      <h2>{t('hostTitle')}</h2>
      <p className="muted">{t('hostText')}</p>
      {library.turnsAvailable > 0 && (
        <p className="field-hint">
          {t('libraryHint', { turns: library.turnsAvailable, startups: library.startupsAvailable })}
        </p>
      )}
      <Field id="host-turns" label={t('turns')} inputMode="numeric" value={values.turns}
        onChange={set('turns')} error={errors.turns} />
      <fieldset className="field">
        <legend>{t('turnLength')}</legend>
        <div className="inline">
          <Field id="host-minutes" label={t('minutes')} inputMode="numeric" value={values.minutes}
            onChange={set('minutes')} error={errors.minutes} />
          <Field id="host-seconds" label={t('seconds')} inputMode="numeric" value={values.seconds}
            onChange={set('seconds')} error={errors.seconds} />
        </div>
        {errors.duration && <p className="field-error" aria-live="polite">{message(durationError)}</p>}
      </fieldset>
      <Field id="host-startups" label={t('startupCount')} inputMode="numeric" value={values.startups}
        onChange={set('startups')} error={errors.startups} />
      {valid && <p className="field-hint">{t('gameLasts', { n: Math.max(1, Math.round(totalSeconds / 60)) })}</p>}
      {error && <p className="error" role="alert">{error}</p>}
      <button className="btn primary" disabled={!valid || busy}>{t('createGame')}</button>
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
