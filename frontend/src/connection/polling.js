import { useCallback, useEffect, useRef, useState } from 'react';

/** Polls `fetcher` every `interval` ms. Returns [data, setData, error].
 *  A value set by hand (for example from a trade response) is not overwritten by a
 *  poll that was already in flight when it was set. While `pausedRef.current` is true
 *  (the screen shows changes the server has not confirmed yet) poll results are dropped. */
export function usePoll(fetcher, interval, deps = [], pausedRef = null) {
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
        if (!cancelled && started >= stamp.current && !pausedRef?.current) {
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
