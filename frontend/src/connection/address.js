import { useEffect, useState } from 'react';
import { api } from './endpoints.js';

/** What the server tells the client: the address players should open (start.py finds the
 *  computer's network address and passes it as PUBLIC_URL) and what the startup library
 *  allows. Fields stay empty until the server answers. */
export function useServerConfig() {
  const [config, setConfig] = useState({});
  useEffect(() => {
    let cancelled = false;
    api.config()
      .then((c) => { if (!cancelled && c) setConfig(c); })
      .catch(() => { /* keep the defaults */ });
    return () => { cancelled = true; };
  }, []);
  return config;
}

/** The address players should open: the server's, else this page's own address. */
export function useServerAddress() {
  const { public_url: publicUrl } = useServerConfig();
  return publicUrl || window.location.origin;
}

/** The link that opens the player screen for a room (what the QR code holds). */
export const playerUrl = (base, code) => `${base}/play/${encodeURIComponent(code)}`;

/** The address without "http://", for people to read and type. */
export const displayAddress = (base) => base.replace(/^https?:\/\//, '');

/** True when the address only works on this computer, so phones could not use it. */
export const isLocalOnly = (base) => /^https?:\/\/(localhost|127\.|\[::1\])/i.test(base);
