import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

const SEND_DELAY_MS = 300;

/** Lets a team tap + and - freely.
 *
 *  The screen changes at once (`view`), taps made in quick succession are sent as one
 *  request per startup, and requests for the same startup go out one after another.
 *  The server's answer always has the last word: if it refuses, the screen goes back to
 *  what the server says. While anything is unconfirmed `pausedRef` is true, so a poll that
 *  arrives in between cannot make the numbers jump.
 *
 *  me      the team's state as last confirmed by the server
 *  prices  {startupId: price} for this turn (null or 0 = cannot be bought)
 *  send    (startupId, shares) => Promise<me | null>   (null = refused, already reported)
 *  setMe   store a confirmed `me`
 *  refresh () => Promise<void>   reload `me` from the server after a refusal
 */
export function useTrader({ me, prices, send, setMe, refresh, pausedRef }) {
  const [unsettled, setUnsettled] = useState({}); // shown on screen, not yet confirmed
  const unsent = useRef({});                      // waiting for the timer
  const timers = useRef({});
  const chains = useRef({});                      // last request per startup
  const inFlight = useRef(0);

  const updatePaused = () => {
    pausedRef.current = inFlight.current > 0 || Object.values(unsent.current).some((v) => v !== 0);
  };

  const view = useMemo(() => {
    let cash = me.cash;
    const owned = Object.fromEntries(me.holdings.map((h) => [h.startup_id, h.shares]));
    for (const [id, delta] of Object.entries(unsettled)) {
      if (!delta) continue;
      cash -= delta * (prices[id] ?? 0);
      owned[id] = (owned[id] || 0) + delta;
    }
    return { ...me, cash, owned };
  }, [me, unsettled, prices]);

  const flush = useCallback((id) => {
    clearTimeout(timers.current[id]);
    delete timers.current[id];
    const delta = unsent.current[id] || 0;
    unsent.current[id] = 0;
    if (delta === 0) {
      updatePaused();
      return Promise.resolve();
    }
    inFlight.current += 1;
    updatePaused();
    const job = (chains.current[id] || Promise.resolve()).then(async () => {
      try {
        const confirmed = await send(Number(id), delta);
        if (confirmed) setMe(confirmed);
        else await refresh();
      } finally {
        setUnsettled((u) => ({ ...u, [id]: (u[id] || 0) - delta }));
        inFlight.current -= 1;
        updatePaused();
      }
    });
    chains.current[id] = job;
    return job;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [send, setMe, refresh]);

  /** A tap on + (shares > 0) or - (shares < 0). */
  const tap = (id, shares) => {
    const price = prices[id];
    if (shares > 0 && (!price || view.cash < shares * price)) return;
    if (shares < 0 && (view.owned[id] || 0) < -shares) return;
    setUnsettled((u) => ({ ...u, [id]: (u[id] || 0) + shares }));
    unsent.current[id] = (unsent.current[id] || 0) + shares;
    updatePaused();
    clearTimeout(timers.current[id]);
    timers.current[id] = setTimeout(() => flush(id), SEND_DELAY_MS);
  };

  /** Send everything now and wait until the server has answered. */
  const flushAll = async () => {
    await Promise.all(Object.keys(timers.current).map((id) => flush(id)));
    await Promise.all(Object.values(chains.current));
  };

  useEffect(() => () => Object.values(timers.current).forEach(clearTimeout), []);

  return { view, tap, flushAll };
}
