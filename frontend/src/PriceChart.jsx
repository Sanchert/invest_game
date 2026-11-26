import { useMemo } from 'react';
import { useT } from './strings.js';
import { STARTUP_COLORS } from './ui.js';

/** Grouped bar chart: each turn is a column, each startup is a colored bar inside the column. */
export default function PriceChart({ startups, price_turns, highlight }) {
  const t = useT();
  const W = 800;
  const H = 400;
  const pad = { left: 56, right: 20, top: 20, bottom: 44 };
  const turns = price_turns;
  const nTurns = turns.length;
  const nStartups = startups.length;

  // Compute bar geometry
  const chartW = W - pad.left - pad.right;
  const chartH = H - pad.top - pad.bottom;
  const colWidth = chartW / nTurns;
  const barGap = Math.max(1, colWidth * 0.08);
  const barWidth = nStartups > 1
    ? (colWidth - barGap) / nStartups - barGap
    : (colWidth - barGap) * 0.7;
  const totalBarsWidth = barWidth * nStartups + barGap * (nStartups - 1);
  const offsetX = (colWidth - totalBarsWidth) / 2;

  // Y scale: all prices across all turns
  const allPrices = useMemo(() => {
    const vals = [];
    for (const s of startups) {
      for (const p of s.scores) {
        if (p != null) vals.push(p);
      }
    }
    return vals;
  }, [startups]);

  const maxPrice = useMemo(() => Math.max(1, ...allPrices), [allPrices]);
  const minPrice = useMemo(() => Math.min(0, ...allPrices), [allPrices]);

  const y = (v) => pad.top + (1 - (v - minPrice) / (maxPrice - minPrice)) * chartH;
  const barY = (v) => y(v);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="price-chart" role="img"
      aria-label={t('priceChartTitle')}>
      {/* Y axis grid + ticks */}
      {(() => {
        const nTicks = Math.min(6, Math.max(3, Math.ceil(nTurns / 2)));
        const step = Math.max(1, Math.ceil((maxPrice - minPrice) / nTicks / 10) * 10);
        const ticks = [];
        for (let v = Math.ceil(minPrice / step) * step; v <= maxPrice; v += step) {
          ticks.push(v);
        }
        return ticks.map((v) => (
          <g key={v}>
            <line x1={pad.left} x2={W - pad.right} y1={barY(v)} y2={barY(v)}
              className="chart-grid" />
            <text x={pad.left - 8} y={barY(v) + 5} textAnchor="end"
              className="chart-tick" fontSize="14">{v}</text>
          </g>
        ));
      })()}

      {/* X axis label */}
      <text x={(pad.left + W - pad.right) / 2} y={H} textAnchor="middle"
        className="chart-tick">{t('turnAxis')}</text>

      {/* Bars */}
      {turns.map((turn, ti) => {
        const cx = pad.left + ti * colWidth + colWidth / 2;
        return (
          <g key={ti}>
            {/* Turn label */}
            <text x={cx} y={H - 10} textAnchor="middle" className="chart-tick"
              fontSize="14">{turn.turn}</text>
            {/* Bars for this turn */}
            {startups.map((s, si) => {
              const price = turn.prices[si];
              if (price == null) return null;
              const strong = !highlight || highlight === s.id;
              const color = STARTUP_COLORS[si % STARTUP_COLORS.length];
              const bx = pad.left + ti * colWidth + offsetX + si * (barWidth + barGap);
              const by = barY(price);
              const bh = barY(minPrice) - by;
              return (
                <g key={si} opacity={strong ? 1 : 0.25}>
                  <rect x={bx} y={by} width={barWidth} height={Math.max(0, bh)}
                    fill={color} rx="2" />
                  {strong && bh > 18 && (
                    <text x={bx + barWidth / 2} y={by + 13} textAnchor="middle"
                      fill="#fff" fontSize="14" fontWeight="700"
                      style={{ textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}>
                      {price}
                    </text>
                  )}
                </g>
              );
            })}
          </g>
        );
      })}

    </svg>
  );
}
