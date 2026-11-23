import { useEffect, useRef, useState } from 'react';

/** Whole seconds left until `endsAt`, on the server's clock.
 *
 *  The offset between the server's clock and this device is measured when a poll
 *  arrives (and smoothed, so network latency does not make the digits wobble). Between
 *  polls the countdown runs on the local clock, so it ticks evenly. */
export function useCountdown(endsAt, serverTime) {
  const clock = useRef({ offset: 0, seen: null });

  const compute = () =>
    endsAt ? Math.max(0, Math.ceil((Date.parse(endsAt) - (Date.now() + clock.current.offset)) / 1000)) : null;

  const [seconds, setSeconds] = useState(null);

  useEffect(() => {
    if (serverTime && clock.current.seen !== serverTime) {
      const sample = Date.parse(serverTime) - Date.now();
      clock.current.offset = clock.current.seen === null
        ? sample
        : clock.current.offset * 0.8 + sample * 0.2;
      clock.current.seen = serverTime;
    }
    setSeconds(compute());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endsAt, serverTime]);

  useEffect(() => {
    const id = setInterval(() => setSeconds(compute()), 250);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endsAt]);

  return seconds;
}
