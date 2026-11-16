import { t } from './strings.js';
import { STARTUP_COLORS } from './hooks.js';

/** Line chart of every team's total profit after each turn. Plain SVG, no library. */
export default function Chart({ turns, series, highlight }) {
  const W = 800;
  const H = 400;
  const pad = { left: 56, right: 150, top: 20, bottom: 44 };
  const all = series.flatMap((s) => s.scores);
  const lo = Math.min(0, ...all);
  const hi = Math.max(1, ...all);
  const x = (i) => pad.left + (i / Math.max(1, turns.length - 1)) * (W - pad.left - pad.right);
  const y = (v) => pad.top + (1 - (v - lo) / (hi - lo)) * (H - pad.top - pad.bottom);
  const ticks = [lo, lo + (hi - lo) / 2, hi].map(Math.round);

  // End-of-line labels: keep at least 18px between them so equal scores stay readable.
  const labelY = {};
  let previous = -Infinity;
  [...series].sort((a, b) => y(a.scores.at(-1)) - y(b.scores.at(-1))).forEach((s) => {
    previous = Math.max(y(s.scores.at(-1)), previous + 18);
    labelY[s.team] = previous;
  });

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img" aria-label={t('chartTitle')}>
      {ticks.map((v) => (
        <g key={v}>
          <line x1={pad.left} x2={W - pad.right} y1={y(v)} y2={y(v)} className="chart-grid" />
          <text x={pad.left - 8} y={y(v) + 4} textAnchor="end" className="chart-tick">{v}</text>
        </g>
      ))}
      {turns.map((n, i) => (
        <text key={n} x={x(i)} y={H - 14} textAnchor="middle" className="chart-tick">{n}</text>
      ))}
      <text x={(pad.left + W - pad.right) / 2} y={H} textAnchor="middle" className="chart-tick">
        {t('turnAxis')}
      </text>
      {series.map((s, idx) => {
        const color = STARTUP_COLORS[idx % STARTUP_COLORS.length];
        const strong = !highlight || s.team === highlight;
        const points = s.scores.map((v, i) => `${x(i)},${y(v)}`).join(' ');
        const last = s.scores.length - 1;
        return (
          <g key={s.team} opacity={strong ? 1 : 0.35}>
            <polyline points={points} fill="none" stroke={color}
              strokeWidth={strong && highlight ? 5 : 3.5} strokeLinejoin="round" strokeLinecap="round" />
            <circle cx={x(last)} cy={y(s.scores[last])} r="5.5" fill={color} />
            <text x={x(last) + 12} y={labelY[s.team] + 5} className="chart-label" fill={color}>
              {s.team.length > 14 ? `${s.team.slice(0, 13)}…` : s.team}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
