import { useEffect, useState } from 'react';
import { PHASE } from '../constants.js';
import { api } from './endpoints.js';

const DEBOUNCE_MS = 350;

/** Looks a room up while the code is being typed.
 *  status: 'idle' (no code to check) | 'checking' | 'open' (can be joined) |
 *          'started' | 'notfound' | 'offline'.  `teams` are the names already taken. */
export function useRoomStatus(code, enabled = true) {
  const [state, setState] = useState({ code: null, status: 'idle', teams: [] });
  useEffect(() => {
    if (!enabled || !code) return undefined;
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const board = await api.board(code);
        if (cancelled) return;
        setState({
          code,
          status: board.phase === PHASE.LOBBY ? 'open' : 'started',
          teams: board.teams.map((team) => team.name),
        });
      } catch (err) {
        if (!cancelled) setState({ code, status: err.status === 404 ? 'notfound' : 'offline', teams: [] });
      }
    }, DEBOUNCE_MS);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [code, enabled]);

  if (!enabled || !code) return { status: 'idle', teams: [] };
  return state.code === code ? state : { status: 'checking', teams: [] };
}
