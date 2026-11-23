import { useEffect, useMemo, useRef, useState } from 'react';
import Chart from './Chart.jsx';
import {
  api, clearSession, loadSession, NETWORK_ERROR, useCountdown, usePoll,
} from './connection/index.js';
import { PHASE } from './constants.js';
import JoinForm from './JoinForm.jsx';
import PriceList from './PriceList.jsx';
import { t } from './strings.js';
import { formatClock, startupColor } from './ui.js';
import { useTrader } from './useTrader.js';

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
  const pausedRef = useRef(false); // true while the screen shows unconfirmed trades
  const [board, , boardError] = usePoll(() => api.board(code), 2000, [code]);
  const [me, setMe, meError] = usePoll(() => api.me(code, token), 2000, [code, token], pausedRef);
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

  /** Runs a player action; shows the server's message if it is refused (and returns null). */
  const run = async (action) => {
    try {
      return await action();
    } catch (err) {
      if (err.status === 401 || err.status === 404) onLost();
      else if (err.code === NETWORK_ERROR) flash(t('connectionLost'));
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
  return (
    <>
      <GameBody {...{ code, token, board, me, setMe, run, refreshMe, pausedRef, boardError }} />
      {toast && <div className="toast" role="alert">{toast}</div>}
    </>
  );
}

function GameBody({ code, token, board, me, setMe, run, refreshMe, pausedRef, boardError }) {
  // Prices at which this turn's trades happen (null when a startup cannot be traded).
  const prices = useMemo(() => Object.fromEntries(board.startups.map((s) => [
    s.id, board.phase === PHASE.TURN && s.open ? s.price : null,
  ])), [board]);
  const trader = useTrader({
    me, prices, setMe, refresh: refreshMe, pausedRef,
    send: (startupId, shares) => run(() => api.trade(code, token, startupId, shares)),
  });
  const shown = trader.view;
  const ctx = { code, token, board, me: shown, setMe, run, refreshMe, trader };
  return (
    <div className="phone">
      <PhoneHeader board={board} me={shown} />
      <div className="phone-pad">
        {boardError && <p className="notice" role="status">{t('connectionLost')}</p>}
        {board.phase === PHASE.LOBBY && <LobbyView {...ctx} />}
        {board.phase === PHASE.TURN && <TurnView {...ctx} />}
        {board.phase === PHASE.RESULTS && <ResultsView {...ctx} />}
        {board.phase === PHASE.FINISHED && <FinalView {...ctx} />}
      </div>
    </div>
  );
}

function PhoneHeader({ board, me }) {
  const left = useCountdown(board.phase_ends_at, board.server_time);
  const timed = board.phase === PHASE.TURN || board.phase === PHASE.RESULTS;
  const pct = timed && left !== null
    ? Math.min(100, (left / (board.phase === PHASE.TURN ? board.turn_seconds : 15)) * 100) : 0;
  const urgent = board.phase === PHASE.TURN && left !== null && left <= 10;
  let label = t('appName');
  if (board.phase === PHASE.TURN) label = t('turnOf', { n: board.turn_no, total: board.turns_total });
  if (board.phase === PHASE.RESULTS) label = t('resultsTitle', { n: board.turn_no });
  if (board.phase === PHASE.FINISHED) label = t('gameOver');
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

function LobbyView({ code, token, board, me, run, refreshMe }) {
  const left = useCountdown(board.countdown_ends_at, board.server_time);
  const toggle = async () => {
    await run(() => (me.ready ? api.unready(code, token) : api.ready(code, token)));
    await refreshMe();
  };
  const leave = async () => {
    const done = await run(async () => { await api.leave(code, token); return true; });
    if (done) { clearSession(code); window.location.reload(); }
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

function StartupCard({ startup, index, shares, cash, turnNo, locked, onTap }) {
  const price = startup.price;
  const tradable = startup.open && !locked;
  const canBuy = (n) => tradable && price > 0 && cash >= n * price;
  const canSell = (n) => tradable && shares >= n;
  const body = turnNo === 1 ? startup.description : (startup.news ?? startup.description);
  return (
    <article className={`ticket ${startup.open ? '' : 'is-closed'}`}
      style={{ '--accent': startupColor(index) }}>
      <div className="ticket-head">
        <h3>{startup.name}</h3>
        {!startup.open
          ? <span className="tag">{t('closed')}</span>
          : <p className="price-tag"><span>{t('priceShort')}</span><strong className="tnum">{price}</strong></p>}
      </div>
      {startup.open
        ? <p className="ticket-body">{body}</p>
        : <p className="ticket-body muted">{t('closedText')}</p>}
      {turnNo > 1 && startup.open && startup.news && (
        <details className="about"><summary>{t('about')}</summary><p>{startup.description}</p></details>
      )}
      {startup.open && (
        <div className="trade">
          <div className="trade-info">
            <span className="tnum trade-shares">{shares}</span>
            <span className="muted">{price === 0 ? t('worthless') : t('shares')}</span>
          </div>
          <div className="stepper" role="group" aria-label={startup.name}>
            <button className="step" disabled={!canSell(5)} onClick={() => onTap(startup.id, -5)}>−5</button>
            <button className="step" disabled={!canSell(1)} onClick={() => onTap(startup.id, -1)} aria-label={t('sell')}>−1</button>
            <button className="step" disabled={!canBuy(1)} onClick={() => onTap(startup.id, 1)} aria-label={t('buy')}>+1</button>
            <button className="step" disabled={!canBuy(5)} onClick={() => onTap(startup.id, 5)}>+5</button>
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

function TurnView({ code, token, board, me, setMe, run, refreshMe, trader }) {
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const confirmTimer = useRef();
  const locked = me.ready;
  const colorOf = (startupId) => startupColor(board.startups.findIndex((s) => s.id === startupId));
  const thisTurn = me.insiders.filter((i) => i.turn === board.turn_no);
  const earlier = me.insiders.filter((i) => i.turn < board.turn_no);
  const done = board.teams.filter((x) => x.ready).length;

  const buyTip = async () => {
    setBusy(true);
    await trader.flushAll(); // the server must know about every trade before it checks the cash
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
    await trader.flushAll();
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
        </div>

        {board.startups.map((s, i) => (
          <StartupCard key={s.id} startup={s} index={i} shares={me.owned[s.id] || 0}
            cash={me.cash} turnNo={board.turn_no} locked={locked} onTap={trader.tap} />
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

const byRank = (a, b) => (a.rank ?? 99) - (b.rank ?? 99) || a.name.localeCompare(b.name);

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
        <h2>{t('newPrices')}</h2>
        <PriceList startups={board.startups} />
      </div>
      <div className="panel">
        <h2>{t('ranking')}</h2>
        <ol className="rank-list">
          {[...board.teams].sort(byRank).map((team) => (
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
          {[...board.teams].sort(byRank).map((team) => (
            <li key={team.id} className={team.name === me.name ? 'is-me' : ''}>
              <span className="rank-no">{team.rank}</span>
              <span className="rank-name">{team.name}</span>
              <span className="rank-score tnum">{team.score >= 0 ? '+' : ''}{team.score}</span>
            </li>
          ))}
        </ol>
      </div>
      <div className="panel">
        <h2>{t('finalPrices')}</h2>
        <PriceList startups={board.startups} />
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
