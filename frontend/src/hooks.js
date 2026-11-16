import { useCallback, useEffect, useRef, useState } from 'react';

/** Polls `fetcher` every `interval` ms. Returns [data, setData, error].
 *  A value set by hand (for example from a trade response) is not overwritten by a
 *  poll that was already in flight when it was set. */
export function usePoll(fetcher, interval, deps = []) {
  const [data, setDataState] = useState(null);
  const [error, setError] = useState(null);
  const stamp = useRef(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const setData = useCallback((value) => {
    stamp.current = performance.now();
    setDataState(value);
  }, []);

  useEffect(() => {
    let cancelled = false;
    let timer;
    const run = async () => {
      const started = performance.now();
      try {
        const value = await fetcherRef.current();
        if (!cancelled && started >= stamp.current) {
          setDataState(value);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err);
      }
      if (!cancelled) timer = setTimeout(run, interval);
    };
    run();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interval, ...deps]);

  return [data, setData, error];
}

/** Whole seconds left until `endsAt`, corrected by the server's clock. */
export function useCountdown(endsAt, serverTime) {
  const offset = useRef(0);
  if (serverTime) offset.current = Date.parse(serverTime) - Date.now();
  const compute = () =>
    endsAt ? Math.max(0, Math.ceil((Date.parse(endsAt) - (Date.now() + offset.current)) / 1000)) : null;
  const [seconds, setSeconds] = useState(compute);

  useEffect(() => {
    setSeconds(compute());
    const id = setInterval(() => setSeconds(compute()), 250);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endsAt, serverTime]);

  return seconds;
}

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
