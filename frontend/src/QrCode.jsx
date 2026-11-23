import { useMemo } from 'react';
import { encodeQr } from './qr.js';

/** A QR code as an SVG: dark modules on a white square with the required quiet zone. */
export default function QrCode({ text, label }) {
  const modules = useMemo(() => {
    try {
      return encodeQr(text, 'M');
    } catch {
      return null; // text too long: show nothing rather than a wrong code
    }
  }, [text]);
  if (!modules) return null;

  const QUIET = 4;
  const n = modules.length;
  const total = n + 2 * QUIET;
  let path = '';
  modules.forEach((row, y) => {
    for (let x = 0; x < n;) {
      if (!row[x]) { x += 1; continue; }
      let run = 1;
      while (x + run < n && row[x + run]) run += 1;
      path += `M${x + QUIET} ${y + QUIET}h${run}v1h-${run}z`;
      x += run;
    }
  });
  return (
    <svg className="qr" viewBox={`0 0 ${total} ${total}`} role="img" aria-label={label}
      shapeRendering="crispEdges">
      <rect width={total} height={total} fill="#fff" />
      <path d={path} fill="#111" />
    </svg>
  );
}
