import { useEffect, useState } from 'react';
import { api } from './endpoints.js';

/** The address players should open. The server knows it (start.py finds the computer's
 *  network address and passes it as PUBLIC_URL); until it answers, or if it does not
 *  know, this page's own address is used. */
export function useServerAddress() {
  const [base, setBase] = useState(() => window.location.origin);
  useEffect(() => {
    let cancelled = false;
    api.config()
      .then((config) => { if (!cancelled && config?.public_url) setBase(config.public_url); })
      .catch(() => { /* keep the page's own address */ });
    return () => { cancelled = true; };
  }, []);
  return base;
}

/** The link that opens the player screen for a room (what the QR code holds). */
export const playerUrl = (base, code) => `${base}/play/${encodeURIComponent(code)}`;

/** The address without "http://", for people to read and type. */
export const displayAddress = (base) => base.replace(/^https?:\/\//, '');

/** True when the address only works on this computer, so phones could not use it. */
export const isLocalOnly = (base) => /^https?:\/\/(localhost|127\.|\[::1\])/i.test(base);
