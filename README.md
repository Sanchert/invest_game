# Invest Game

A classroom investing game. One computer shows the **board** on a projector; each team
plays from a phone.

## Run

The easiest way (needs Docker Desktop running and Python 3):

```
python start.py          # or double-click start.bat on Windows, ./start.sh on Linux/macOS
```

It finds this computer's network address, starts the game with it, copies the address to
the clipboard and opens the browser. If the computer has several network addresses it lists
them and asks which one the players will use (the computer's own hotspot is suggested first).
Options: `--ip 192.168.0.10` (use this address), `--port 8080`, `--no-open`, `--no-copy`,
`--stop` (stop everything).

1. Open the printed address on the projector computer and press "Create game": the board
   shows a **QR code**, the room code and the address. Players scan the QR (it opens their
   screen for that room) or open the address and type the code.
2. Allow the port (8080) in the firewall for the private network when Windows asks.
3. Board: `/board/<ROOM>`, players: `/play/<ROOM>`. Add `?lang=en` or `?lang=ru` to force a language.
   The API docs are at http://localhost:3000/docs.

Without the launcher: `cp .env.example .env`, set `PUBLIC_URL` (the address players open, for
example `http://192.168.0.10:8080`) and run `docker compose up --build`.

Notes:
- The database URL is built from `POSTGRES_USER`, `POSTGRES_PASSWORD` and `POSTGRES_DB` in `.env`
  (special characters in the password are fine). Postgres reads these only when its volume is
  first created: if you change the password later, run `docker compose down -v` once.
- Tables are created on startup (`create_all`). After changing `models.py`, run
  `docker compose down -v` to reset the database.
- If `PUBLIC_URL` is not set and the board is opened as `localhost`, the board warns that
  phones cannot use that address.

## How a game runs

The rules follow the Excel model the game was played with (`settings.py` holds the numbers).

1. Teams join and press **Ready**. With at least 2 teams and everyone ready, a 10-second
   countdown starts; a new team or an un-ready cancels it. A team that stops polling for
   60 s in the lobby is dropped. Every game uses new teams.
2. **Turn** (length set at creation). In turn *t* teams trade at the price of turn *t*.
   Turn 1: read the startups and buy. From turn 2 there is news too. Insider tips can be
   bought in any turn (5 / 10 / 30 for turns 1 / 2 / 3; one random tip per purchase, each tip
   once per team). **Ready** is final; when the timer ends, teams that have not pressed it
   are confirmed automatically.
3. **Results** (15 s): the new price of every startup is revealed, shares are valued at it
   and ranks are computed. Capital can fall as well as rise.
4. After the last turn the final price applies; final standings, exact totals and the
   capital chart are shown.

Score = capital - 600 (cash + shares at the latest revealed price - starting capital).
A startup with price 0 cannot be bought. A startup whose story ends early is sold
automatically at its final price.

## Content

Each startup has a list of prices `[P1, P2, ..., P(L+1)]` for the L turns it is open
(the Excel model: 10 -> 41 -> 86 -> 9 means three turns). News exist for turns 2..L, insider
tips for turns 1..L. Startups live in the database. On first start the files in
`backend/content/*.json` are loaded if the library is empty; `sample_pack.json` has the
five startups and prices from the Excel model, with **placeholder texts** to replace.
To add or replace startups while the server runs (set `ADMIN_KEY` first):

```
curl -X POST localhost:3000/api/admin/content \
  -H "X-Admin-Key: $ADMIN_KEY" -H "Content-Type: application/json" \
  --data @my_pack.json
```

After upgrading from the earlier (profit-per-share) version run `docker compose down -v`
once: the tables changed.

## Tests

```
cd backend && python3 -m unittest discover -s tests -v   # rules, settings, launcher: no dependencies
cd frontend && node --test                               # QR code generator
python3 backend/smoke_test.py                            # a whole game over HTTP, server must be running
```
