import { useEffect, useRef, useState } from 'react';
import { api, clearSession, loadSession } from './api.js';
import Chart from './Chart.jsx';
import { formatClock, startupColor, useCountdown, usePoll } from './hooks.js';
import JoinForm from './JoinForm.jsx';
import { t } from './strings.js';

export default function Player({ code }) {
  const [session, setSession] = useState(() => loadSession(code));
  if (!session) {
    return (
      <div className="phone">
        <div className="phone-pad">
          <h1 className="phone-title">{t('appName')}</h1>
          <JoinForm fixedCode={code} onJoined={(_room, s) => setSession(s)} />
        </div>
      </div>
    );
  }
  return <Game code={code} token={session.token}
    onLost={() => { clearSession(code); setSession(null); }} />;
}

function Game({ code, token, onLost }) {
  const [board, , boardError] = usePoll(() => api.board(code), 2000, [code]);
  const [me, setMe, meError] = usePoll(() => api.me(code, token), 2000, [code, token]);
  const [toast, setToast] = useState('');
  const toastTimer = useRef();

  useEffect(() => {
    if (meError && (meError.status === 401 || meError.status === 404)) onLost();
  }, [meError, onLost]);

  const flash = (message) => {
    setToast(message);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(''), 4000);
  };

  /** Runs a player action; shows the server's message if it is refused. */
  const run = async (action) => {
    try {
      return await action();
    } catch (err) {
      if (err.status === 401 || err.status === 404) onLost();
      else if (err.code === 'network') flash(t('connectionLost'));
      else flash(err.message);
      return null;
    }
  };

  const refreshMe = async () => {
    const fresh = await run(() => api.me(code, token));
    if (fresh) setMe(fresh);
  };

  if (!board || !me) {
    return (
      <div className="phone"><div className="phone-pad">
        <p className="muted">{boardError ? t('connectionLost') : t('loading')}</p>
      </div></div>
    );
  }

  const ctx = { code, token, board, me, setMe, run, flash, refreshMe, onLost };
  return (
    <div className="phone">
      <PhoneHeader board={board} me={me} />
      <div className="phone-pad">
        {boardError && <p className="notice" role="status">{t('connectionLost')}</p>}
        {board.phase === 'LOBBY' && <LobbyView {...ctx} />}
        {board.phase === 'TURN' && <TurnView {...ctx} />}
        {board.phase === 'RESULTS' && <ResultsView {...ctx} />}
        {board.phase === 'FINISHED' && <FinalView {...ctx} />}
      </div>
      {toast && <div className="toast" role="alert">{toast}</div>}
    </div>
  );
}

function PhoneHeader({ board, me }) {
  const left = useCountdown(board.phase_ends_at, board.server_time);
  const timed = board.phase === 'TURN' || board.phase === 'RESULTS';
  const pct = timed && left !== null
    ? Math.min(100, (left / (board.phase === 'TURN' ? board.turn_seconds : 15)) * 100) : 0;
  const urgent = board.phase === 'TURN' && left !== null && left <= 10;
  let label = t('appName');
  if (board.phase === 'TURN') label = t('turnOf', { n: board.turn_no, total: board.turns_total });
  if (board.phase === 'RESULTS') label = t('resultsTitle', { n: board.turn_no });
  if (board.phase === 'FINISHED') label = t('gameOver');
  return (
    <header className="p-head">
      <div className="p-head-row">
        <div>
          <p className="p-team">{me.name}</p>
          <p className="p-phase">
            {label}{timed && left !== null && <> · <span className="tnum">{formatClock(left)}</span></>}
          </p>
        </div>
        <div className="p-cash">
          <span className="tnum p-cash-value">{me.cash}</span>
          <span className="p-cash-label">{t('cash')} · {t('capital')} <span className="tnum">{me.capital}</span></span>
        </div>
      </div>
      {timed && <div className="timebar"><i className={urgent ? 'urgent' : ''} style={{ width: `${pct}%` }} /></div>}
    </header>
  );
}

function LobbyView({ code, token, board, me, run, refreshMe, onLost }) {
  const left = useCountdown(board.countdown_ends_at, board.server_time);
  const toggle = async () => {
    await run(() => (me.ready ? api.unready(code, token) : api.ready(code, token)));
    await refreshMe();
  };
  const leave = async () => {
    const done = await run(async () => { await api.leave(code, token); return true; });
    if (done) onLost();
  };
  let status = t('waitingReady');
  if (board.teams.length < board.min_teams) status = t('needTeams', { n: board.min_teams });
  return (
    <section className="stack">
      <div className="panel">
        <p className="room-code-small">{board.room_code}</p>
        <p className="muted">{board.countdown_ends_at && left !== null ? t('startingIn', { n: left }) : status}</p>
      </div>
      <div className="panel">
        <h2>{t('teamsJoined')}</h2>
        <ul className="team-list">
          {board.teams.map((team) => (
            <li key={team.id} className={team.ready ? 'is-ready' : ''}>
              <span>{team.name}</span>
              <span className="tag">{team.ready ? t('ready') : t('waiting')}</span>
            </li>
          ))}
        </ul>
      </div>
      <button className={`btn ${me.ready ? 'ghost' : 'primary'}`} onClick={toggle}>
        {me.ready ? t('notReady') : t('imReady')}
      </button>
      <button className="btn link" onClick={leave}>{t('leaveGame')}</button>
    </section>
  );
}

function ProfitChips({ profits }) {
  if (!profits.length) return null;
  return (
    <ul className="chips" aria-label={t('profitHistory')}>
      {profits.map((p) => (
        <li key={p.turn}><small>{t('turnShort', { n: p.turn })}</small> +{p.profit}</li>
      ))}
    </ul>
  );
}

function StartupCard({ startup, index, shares, cash, turnNo, locked, busy, onTrade }) {
  const price = startup.price;
  const canBuy = (n) => !locked && !busy && startup.open && price != null && cash >= n * price;
  const canSell = (n) => !locked && !busy && startup.open && shares >= n;
  const body = turnNo === 1 ? startup.description : (startup.news ?? startup.description);
  return (
    <article className={`ticket ${startup.open ? '' : 'is-closed'}`}
      style={{ '--accent': startupColor(index) }}>
      <div className="ticket-head">
        <h3>{startup.name}</h3>
        {!startup.open && <span className="tag">{t('closed')}</span>}
      </div>
      {startup.open
        ? <p className="ticket-body">{body}</p>
        : <p className="ticket-body muted">{t('closedText')}</p>}
      {turnNo > 1 && startup.open && startup.news && (
        <details className="about"><summary>{t('about')}</summary><p>{startup.description}</p></details>
      )}
      <ProfitChips profits={startup.profits} />
      {startup.open && (
        <div className="trade">
          <div className="trade-info">
            <span className="tnum trade-shares">{shares}</span>
            <span className="muted">{t('shares')} · {t('price')} <span className="tnum">{price}</span></span>
          </div>
          <div className="stepper" role="group" aria-label={startup.name}>
            <button className="step" disabled={!canSell(5)} onClick={() => onTrade(startup.id, -5)}>−5</button>
            <button className="step" disabled={!canSell(1)} onClick={() => onTrade(startup.id, -1)} aria-label={t('sell')}>−1</button>
            <button className="step" disabled={!canBuy(1)} onClick={() => onTrade(startup.id, 1)} aria-label={t('buy')}>+1</button>
            <button className="step" disabled={!canBuy(5)} onClick={() => onTrade(startup.id, 5)}>+5</button>
          </div>
        </div>
      )}
    </article>
  );
}

function TipCard({ tip, color }) {
  return (
    <li className="tip" style={{ '--accent': color }}>
      <strong>{tip.startup_name}</strong>
      <span>{tip.text}</span>
    </li>
  );
}

function TurnView({ code, token, board, me, setMe, run, refreshMe }) {
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const confirmTimer = useRef();
  const locked = me.ready;
  const holdings = Object.fromEntries(me.holdings.map((h) => [h.startup_id, h.shares]));
  const colorOf = (startupId) => startupColor(board.startups.findIndex((s) => s.id === startupId));
  const thisTurn = me.insiders.filter((i) => i.turn === board.turn_no);
  const earlier = me.insiders.filter((i) => i.turn < board.turn_no);
  const done = board.teams.filter((x) => x.ready).length;

  const trade = async (startupId, shares) => {
    setBusy(true);
    const updated = await run(() => api.trade(code, token, startupId, shares));
    if (updated) setMe(updated);
    setBusy(false);
  };

  const buyTip = async () => {
    setBusy(true);
    const result = await run(() => api.insider(code, token));
    if (result) setMe(result.me);
    else await refreshMe();
    setBusy(false);
  };

  const confirm = async () => {
    if (!confirming) {
      setConfirming(true);
      clearTimeout(confirmTimer.current);
      confirmTimer.current = setTimeout(() => setConfirming(false), 4000);
      return;
    }
    setBusy(true);
    await run(() => api.ready(code, token));
    await refreshMe();
    setConfirming(false);
    setBusy(false);
  };

  return (
    <>
      <section className="stack">
        {board.turn_no === 1 && <p className="notice">{t('introTurn')}</p>}

        <div className="panel tips">
          <h2>{t('tips')}</h2>
          {board.turn_no < 2 ? <p className="muted">{t('noTipsYet')}</p> : (
            <>
              <p className="muted">{t('tipsHelp')}</p>
              <button className="btn coral" onClick={buyTip}
                disabled={busy || locked || me.cash < me.insider_cost || me.insiders_left === 0}>
                {t('buyTip', { cost: me.insider_cost })}
              </button>
              {me.insiders_left === 0 && <p className="muted" role="status">{t('noTipsLeft')}</p>}
              {thisTurn.length > 0 && (
                <ul className="tip-list" aria-label={t('yourTips')}>
                  {thisTurn.map((tip, i) => <TipCard key={`${tip.startup_id}-${i}`} tip={tip} color={colorOf(tip.startup_id)} />)}
                </ul>
              )}
              {earlier.length > 0 && (
                <details className="about">
                  <summary>{t('earlierTips')}</summary>
                  <ul className="tip-list">
                    {earlier.map((tip, i) => <TipCard key={`${tip.turn}-${i}`} tip={tip} color={colorOf(tip.startup_id)} />)}
                  </ul>
                </details>
              )}
            </>
          )}
        </div>

        {board.startups.map((s, i) => (
          <StartupCard key={s.id} startup={s} index={i} shares={holdings[s.id] || 0}
            cash={me.cash} turnNo={board.turn_no} locked={locked} busy={busy} onTrade={trade} />
        ))}
      </section>

      <div className="ready-bar">
        {locked ? (
          <p className="waiting" role="status">
            {t('waitingOthers')} · {t('teamsDone', { n: done, total: board.teams.length })}
          </p>
        ) : (
          <>
            {confirming && <p className="confirm-hint" role="status">{t('confirmAgain')}</p>}
            <button className={`btn ${confirming ? 'coral' : 'primary'}`} onClick={confirm} disabled={busy}>
              {t('confirmDone')}
            </button>
          </>
        )}
      </div>
    </>
  );
}

function ResultsView({ board, me }) {
  const left = useCountdown(board.phase_ends_at, board.server_time);
  return (
    <section className="stack">
      <div className="panel center">
        <p className="muted">{t('yourPlace')}</p>
        <p className="big-rank tnum">{me.rank ?? '–'}</p>
        <p className="muted">{t('nextTurnIn', { n: left ?? '–' })}</p>
      </div>
      <div className="panel">
        <h2>{t('profitPerShare')}</h2>
        <ul className="profit-list">
          {board.startups.map((s, i) => {
            const point = s.profits.find((p) => p.turn === board.turn_no);
            return (
              <li key={s.id} style={{ '--accent': startupColor(i) }}>
                <span className="profit-name">{s.name}</span>
                {point ? <span className="profit-value tnum">+{point.profit}</span>
                  : <span className="profit-value muted">{t('closed')}</span>}
              </li>
            );
          })}
        </ul>
      </div>
      <div className="panel">
        <h2>{t('ranking')}</h2>
        <ol className="rank-list">
          {[...board.teams].sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99) || a.name.localeCompare(b.name))
            .map((team) => (
              <li key={team.id} className={team.name === me.name ? 'is-me' : ''}>
                <span className="rank-no">{team.rank}</span>
                <span className="rank-name">{team.name}</span>
              </li>
            ))}
        </ol>
      </div>
    </section>
  );
}

function FinalView({ board, me }) {
  return (
    <section className="stack">
      <div className="panel center">
        <p className="muted">{t('yourPlace')}</p>
        <p className="big-rank tnum">{me.rank ?? '–'}</p>
        <p className="muted">{t('profit')}</p>
        <p className="big-score tnum">{me.score >= 0 ? '+' : ''}{me.score}</p>
      </div>
      <div className="panel">
        <h2>{t('finalStandings')}</h2>
        <ol className="rank-list">
          {[...board.teams].sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99) || a.name.localeCompare(b.name))
            .map((team) => (
              <li key={team.id} className={team.name === me.name ? 'is-me' : ''}>
                <span className="rank-no">{team.rank}</span>
                <span className="rank-name">{team.name}</span>
                <span className="rank-score tnum">{team.score >= 0 ? '+' : ''}{team.score}</span>
              </li>
            ))}
        </ol>
      </div>
      {board.chart && (
        <div className="panel">
          <h2>{t('chartTitle')}</h2>
          <Chart turns={board.chart.turns} series={board.chart.series} highlight={me.name} />
        </div>
      )}
      <button className="btn ghost" onClick={() => window.location.assign('/')}>{t('startOver')}</button>
    </section>
  );
}
