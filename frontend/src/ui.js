/** Small presentation helpers shared by the board and the player screens. */

export function formatClock(totalSeconds) {
  if (totalSeconds === null || totalSeconds === undefined) return '–:––';
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

export const STARTUP_COLORS = [
  '#4C6FFF', '#00A6A6', '#F25F5C', '#F5B700', '#8E5CF7', '#2FBF71', '#FF8A3D', '#E0529C',
];

export const startupColor = (index) => STARTUP_COLORS[index % STARTUP_COLORS.length];

/** +5, −3, 0 (with a real minus sign). */
export const signed = (n) => `${n > 0 ? '+' : n < 0 ? '−' : ''}${Math.abs(n)}`;
