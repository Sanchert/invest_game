# connection

Everything the browser needs to talk to the game server. Screens import only from
`./connection/index.js`; nothing else in the client calls `fetch` or reads the server's address.

| File | Responsibility |
|---|---|
| `http.js` | `request()` (the only `fetch`), `ApiError`, the `/api` base path |
| `endpoints.js` | `api`: one function per server endpoint |
| `session.js` | the team's token in `localStorage` (`saveSession`, `loadSession`, `clearSession`) |
| `polling.js` | `usePoll()`: keeps a screen in sync by polling an endpoint (can be paused while a screen has unconfirmed changes) |
| `clock.js` | `useCountdown()`: countdown on the server's clock, corrected for the device's offset |
| `lookup.js` | `useRoomStatus()`: checks a room code while it is typed (found / already started / not found) |
| `address.js` | `useServerConfig()` (address and library limits), `useServerAddress()`: the address players open (the server's `PUBLIC_URL`, else this page's own address), `playerUrl()`, `displayAddress()`, `isLocalOnly()` |

To change how the client reaches the server (timeouts, retries, WebSocket, a configured
public address), edit this folder; the screens do not need to change.
