# Invest Game

A classroom investing game. One computer shows the **board** on a projector; each team
plays from a phone.

## Run

```
cp .env.example .env      # then edit the passwords
docker compose up --build
```

- Open http://localhost:8080 : "Open a board" creates a game, "Join as a team" joins one.
- Board: `/board/<ROOM>`, players: `/play/<ROOM>`. Add `?lang=en` or `?lang=ru` to force a language.
- The API docs are at http://localhost:3000/docs.
- Schema changes: tables are created on startup (`create_all`). After changing
  `models.py`, run `docker compose down -v` to reset the database.

## How a game runs

1. Teams join and press **Ready**. With at least 2 teams and everyone ready, a 10-second
   countdown starts; a new team or an un-ready cancels it. A team that stops polling for
   60 s in the lobby is dropped.
2. **Turn** (length set at creation). Turn 1: read the startups, buy shares. From turn 2:
   news, insider tips (30 each, one random tip per purchase, each tip once per team),
   buy and sell shares at the buy price (10). **Ready** is final; when the timer ends,
   teams that have not pressed it are confirmed automatically.
3. **Results** (15 s): the turn's profit per share is paid into cash and ranks are
   computed. A startup's shares are redeemed at the buy price when its story ends.
4. After the last turn: final standings, exact totals and the profit chart.

Score = capital - starting capital (cash + shares at the buy price - 600).

## Content

Startups live in the database. On first start the files in `backend/content/*.json` are
loaded if the library is empty (`sample_pack.json` is placeholder content).
To add or replace startups while the server runs (set `ADMIN_KEY` first):

```
curl -X POST localhost:3000/api/admin/content \
  -H "X-Admin-Key: $ADMIN_KEY" -H "Content-Type: application/json" \
  --data @my_pack.json
```

Pack format: see `backend/content/sample_pack.json`. Per startup: `turns` (1..N, each with
`profit`, optional `buy_price`, default 10), `news` and `insiders` for turns 2..N.
A startup is open until its last turn; a game is never longer than its longest startup.

## Tests

```
cd backend && python3 -m unittest discover -s tests -v   # rules only, no dependencies
```
