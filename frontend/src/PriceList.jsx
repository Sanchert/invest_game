import { startupColor } from './ui.js';
import { useT } from './strings.js';

/** The price of every startup after a turn: old -> new, and the change.
 *  variant "list" is a column, "strip" a row of chips. */
export default function PriceList({ startups, variant = 'list' }) {
  const t = useT();
  return (
    <ul className={`price-list ${variant}`}>
      {startups.map((s, i) => {
        const known = s.price != null && s.prev_price != null;
        const delta = known ? s.price - s.prev_price : 0;
        const sign = delta >= 0 ? '+' : '−';
        return (
          <li key={s.id} style={{ '--accent': startupColor(i) }}>
            <span className="price-name">{s.name}</span>
            {known ? (
              <span className="price-move">
                <span className="price-old tnum">{s.prev_price}</span>
                <span className="price-arrow" aria-hidden="true">→</span>
                <strong className="price-new tnum">{s.price}</strong>
                <span className={`price-delta tnum ${delta > 0 ? 'up' : delta < 0 ? 'down' : ''}`}>
                  {sign}{Math.abs(delta)}
                </span>
              </span>
            ) : (
              <span className="price-move muted">{s.price != null ? s.price : t('closed')}</span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
