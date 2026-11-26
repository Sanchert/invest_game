import Chart from './Chart.jsx';
import PriceChart from './PriceChart.jsx';
import { PHASE } from './constants.js';
import PriceList from './PriceList.jsx';
import QrCode from './QrCode.jsx';
import {
  api, displayAddress, isLocalOnly, playerUrl, useCountdown, usePoll, useServerAddress,
} from './connection/index.js';
import { formatClock, startupColor } from './ui.js';
import { useT } from './strings.js';

function LeaveBoard({ phase }) {
  const t = useT();
  const leave = () => {
    const running = phase === PHASE.TURN || phase === PHASE.RESULTS;
    if (running && !window.confirm(t('leaveBoardConfirm'))) return;
    window.location.assign('/');
  };
  return <button className="leave-board" onClick={leave}>{t('leaveBoard')}</button>;
}

export default function Board({ code }) {
  const t = useT();
  const [board, , error] = usePoll(() => api.board(code), 1500, [code]);

  if (!board) {
    const message = error?.status === 404 ? t('gameNotFound')
      : error ? t('connectionLost') : t('loading');
    return (
      <div className="board board-center">
        <p className="board-message">{message}</p>
        <LeaveBoard phase={PHASE.LOBBY} />
      </div>
    );
  }
  return (
    <div className="board">
      <LeaveBoard phase={board.phase} />
      {error && <div className="banner" role="status">{t('connectionLost')}</div>}
      {board.phase === PHASE.LOBBY && <Lobby board={board} />}
      {board.phase === PHASE.TURN && <TurnView board={board} />}
      {board.phase === PHASE.RESULTS && <ResultsView board={board} />}
      {board.phase === PHASE.FINISHED && <FinalView board={board} />}
    </div>
  );
}

function TeamStrip({ teams }) {
  const t = useT();
  return (
    <ul className="team-strip">
      {teams.map((team) => (
        <li key={team.id} className={team.ready ? 'is-ready' : ''}>
          <span className="dot" aria-hidden="true" />
          {team.name}
          <span className="sr-only">{team.ready ? t('ready') : t('waiting')}</span>
        </li>
      ))}
    </ul>
  );
}

function Lobby({ board }) {
  const t = useT();
  const left = useCountdown(board.countdown_ends_at, board.server_time);
  const base = useServerAddress();
  const counting = board.countdown_ends_at && left !== null;
  let status = t('waitingReady');
  if (board.teams.length < board.min_teams) status = t('needTeams', { n: board.min_teams });
  return (
    <main className="lobby">
      <div className="lobby-main">
        <div className="join-row">
          <figure className="qr-figure">
            <figcaption className="qr-caption">{t('scanToJoin')}</figcaption>
            <div className="qr-tile">
              <QrCode text={playerUrl(base, board.room_code)} label={t('scanToJoin')} />
            </div>
          </figure>
          <div className="join-text">
            <p className="lobby-join">{t('orOpen', { address: displayAddress(base) })}</p>
            {/* <p className="lobby-join">{t('roomCode')}</p> */}
            <p className="room-code">{board.room_code}</p>
          </div>
        </div>
        {isLocalOnly(base) && <p className="banner" role="status">{t('localOnlyHint')}</p>}
        <p className="lobby-status">{counting ? t('startingIn', { n: left }) : status}</p>
      </div>
      <div className="lobby-teams">
        <h2>{t('teamsJoined')}</h2>
        {board.teams.length === 0
          ? <p className="muted">{t('noTeamsYet')}</p>
          : <TeamStrip teams={board.teams} />}
      </div>
    </main>
  );
}

function StartupPanel({ startup, index, turnNo }) {
  const t = useT();
  const body = turnNo === 1 ? startup.description : (startup.news ?? startup.description);
  return (
    <article className={`startup-panel ${startup.open ? '' : 'is-closed'}`}
      style={{ '--accent': startupColor(index) }}>
      <header className="startup-head">
        <h2>{startup.name}</h2>
        {startup.price != null && (
          <p className="price-tag">
            <span>{t('priceShort')}</span>
            <strong className="tnum">{startup.price}</strong>
          </p>
        )}
      </header>
      {startup.open
        ? <p className="startup-body">{body}</p>
        : <p className="startup-body muted">{t('closedText')}</p>}
    </article>
  );
}

function TurnView({ board }) {
  const t = useT();
  const left = useCountdown(board.phase_ends_at, board.server_time);
  const pct = left === null ? 0 : Math.min(100, (left / board.turn_seconds) * 100);
  const done = board.teams.filter((x) => x.ready).length;
  const urgent = left !== null && left <= 10;
  return (
    <>
      <header className="board-top">
        <p className="turn-label">{t('turnOf', { n: board.turn_no, total: board.turns_total })}</p>
        <p className={`clock ${urgent ? 'urgent' : ''}`} aria-label={t('timeLeft')}>{formatClock(left)}</p>
      </header>
      <div className="timebar"><i className={urgent ? 'urgent' : ''} style={{ width: `${pct}%` }} /></div>
      <main className="startup-row">
        {board.startups.map((s, i) => (
          <StartupPanel key={s.id} startup={s} index={i} turnNo={board.turn_no} />
        ))}
      </main>
      <footer className="board-foot">
        <TeamStrip teams={board.teams} />
        <p className="foot-count">{t('teamsDone', { n: done, total: board.teams.length })}</p>
      </footer>
    </>
  );
}

function sortedByRank(teams) {
  return [...teams].sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99) || a.name.localeCompare(b.name));
}

function RankList({ teams, showScore }) {
  return (
    <ol className="rank-list">
      {sortedByRank(teams).map((team) => (
        <li key={team.id} className={team.rank === 1 ? 'is-first' : ''}>
          <span className="rank-no">{team.rank}</span>
          <span className="rank-name">{team.name}</span>
          {showScore && <span className="rank-score">{team.score >= 0 ? '+' : ''}{team.score}</span>}
        </li>
      ))}
    </ol>
  );
}

function ResultsView({ board }) {
  const t = useT();
  const left = useCountdown(board.phase_ends_at, board.server_time);
  return (
    <>
      <header className="board-top">
        <p className="turn-label">{t('resultsTitle', { n: board.turn_no })}</p>
        <p className="clock small" aria-live="off">{t('nextTurnIn', { n: left ?? '–' })}</p>
      </header>
      <main className="results-grid">
        <section>
          <h2>{t('newPrices')}</h2>
          <PriceList startups={board.startups} />
        </section>
        <section>
          <h2>{t('ranking')}</h2>
          <RankList teams={board.teams} />
        </section>
      </main>
    </>
  );
}

function FinalView({ board }) {
  const t = useT();
  return (
    <>
      <header className="board-top">
        <p className="turn-label">{t('gameOver')}</p>
        <p className="clock small">{t('finalStandings')}</p>
      </header>
      <main className="results-grid">
        <section>
          <h2>{t('profit')}</h2>
          <RankList teams={board.teams} showScore />
        </section>
        <section>
          <h2>{t('chartTitle')}</h2>
          {board.chart && <Chart turns={board.chart.turns} series={board.chart.series} />}
        </section>
        {board.chart && board.chart.price_turns && (
          <section>
            <h2>{t('priceChartTitle')}</h2>
            <PriceChart startups={board.chart.startups}
              price_turns={board.chart.price_turns} />
          </section>
        )}
      </main>
      <section className="final-prices">
        <h2>{t('finalPrices')}</h2>
        <PriceList startups={board.startups} variant="strip" />
      </section>
    </>
  );
}
