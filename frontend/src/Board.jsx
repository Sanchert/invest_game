import { api } from './api.js';
import Chart from './Chart.jsx';
import { formatClock, startupColor, useCountdown, usePoll } from './hooks.js';
import { t } from './strings.js';

export default function Board({ code }) {
  const [board, , error] = usePoll(() => api.board(code), 1500, [code]);

  if (!board) {
    const message = error?.status === 404 ? t('gameNotFound')
      : error ? t('connectionLost') : t('loading');
    return <div className="board board-center"><p className="board-message">{message}</p></div>;
  }
  return (
    <div className="board">
      {error && <div className="banner" role="status">{t('connectionLost')}</div>}
      {board.phase === 'LOBBY' && <Lobby board={board} />}
      {board.phase === 'TURN' && <TurnView board={board} />}
      {board.phase === 'RESULTS' && <ResultsView board={board} />}
      {board.phase === 'FINISHED' && <FinalView board={board} />}
    </div>
  );
}

function TeamStrip({ teams }) {
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
  const left = useCountdown(board.countdown_ends_at, board.server_time);
  const counting = board.countdown_ends_at && left !== null;
  let status = t('waitingReady');
  if (board.teams.length < board.min_teams) status = t('needTeams', { n: board.min_teams });
  return (
    <>
      <main className="lobby">
        <div>
          <p className="lobby-join">{t('joinAt')} <strong>{window.location.host}</strong> {t('withCode')}</p>
          <p className="room-code">{board.room_code}</p>
          <p className="lobby-status">{counting ? t('startingIn', { n: left }) : status}</p>
        </div>
        <div className="lobby-teams">
          <h2>{t('teamsJoined')}</h2>
          {board.teams.length === 0
            ? <p className="muted">{t('noTeamsYet')}</p>
            : <TeamStrip teams={board.teams} />}
        </div>
      </main>
    </>
  );
}

function StartupPanel({ startup, index, turnNo }) {
  const body = turnNo === 1 ? startup.description : (startup.news ?? startup.description);
  return (
    <article className={`startup-panel ${startup.open ? '' : 'is-closed'}`}
      style={{ '--accent': startupColor(index) }}>
      <h2>{startup.name}</h2>
      {startup.open
        ? <p className="startup-body">{body}</p>
        : <p className="startup-body muted">{t('closedText')}</p>}
      {startup.profits.length > 0 && (
        <ul className="chips" aria-label={t('profitHistory')}>
          {startup.profits.map((p) => (
            <li key={p.turn}><small>{t('turnShort', { n: p.turn })}</small> +{p.profit}</li>
          ))}
        </ul>
      )}
    </article>
  );
}

function TurnView({ board }) {
  const left = useCountdown(board.phase_ends_at, board.server_time);
  const pct = left === null ? 0 : Math.min(100, (left / board.turn_seconds) * 100);
  const done = board.teams.filter((x) => x.ready).length;
  const urgent = left !== null && left <= 10;
  return (
    <>
      <header className="board-top">
        <p className="turn-label">{t('turnOf', { n: board.turn_no, total: board.turns_total })}</p>
        <p className={`clock ${urgent ? 'urgent' : ''}`} aria-label={t('timeLeft')}>{formatClock(left)}</p>
        <p className="room-small">{board.room_code}</p>
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
  const left = useCountdown(board.phase_ends_at, board.server_time);
  return (
    <>
      <header className="board-top">
        <p className="turn-label">{t('resultsTitle', { n: board.turn_no })}</p>
        <p className="clock small" aria-live="off">{t('nextTurnIn', { n: left ?? '–' })}</p>
        <p className="room-small">{board.room_code}</p>
      </header>
      <main className="results-grid">
        <section>
          <h2>{t('profitPerShare')}</h2>
          <ul className="profit-list">
            {board.startups.map((s, i) => {
              const point = s.profits.find((p) => p.turn === board.turn_no);
              return (
                <li key={s.id} style={{ '--accent': startupColor(i) }}>
                  <span className="profit-name">{s.name}</span>
                  {point ? <span className="profit-value">+{point.profit}</span>
                    : <span className="profit-value muted">{t('closed')}</span>}
                </li>
              );
            })}
          </ul>
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
  return (
    <>
      <header className="board-top">
        <p className="turn-label">{t('gameOver')}</p>
        <p className="clock small">{t('finalStandings')}</p>
        <p className="room-small">{board.room_code}</p>
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
      </main>
    </>
  );
}
