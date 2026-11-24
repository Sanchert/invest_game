"""Plays a whole game over HTTP against a running server (standard library only).

    docker compose up -d
    python3 backend/smoke_test.py                 # default http://localhost:3000
    python3 backend/smoke_test.py http://192.168.0.10:8080

Takes about a minute: the lobby countdown (10 s) plus two 15 s results screens.
"""
import json
import sys
import time
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3000").rstrip("/")


def call(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{BASE}/api{path}", data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("X-Team-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            text = res.read().decode()
            return res.status, (json.loads(text) if text else None)
    except urllib.error.HTTPError as err:
        text = err.read().decode()
        return err.code, (json.loads(text) if text else None)


failures = []


def check(label, condition, detail=""):
    print(("PASS  " if condition else "FAIL  ") + label + (f"   {detail}" if detail and not condition else ""))
    if not condition:
        failures.append(label)


def wait_for(room, phase, turn=None, timeout=40):
    end = time.time() + timeout
    while time.time() < end:
        _, board = call("GET", f"/games/{room}/board")
        if board["phase"] == phase and (turn is None or board["turn_no"] == turn):
            return board
        time.sleep(1)
    raise SystemExit(f"timed out waiting for {phase} {turn or ''}")


status, game = call("POST", "/games", body={"turns": 3, "turn_seconds": 60, "startups_count": 5})
check("create game", status == 200, status)
room = game["room_code"]
check("three turns", game["turns_total"] == 3, game)

_, a = call("POST", f"/games/{room}/join", body={"name": "Alpha"})
_, b = call("POST", f"/games/{room}/join", body={"name": "Beta"})
check("duplicate team name refused", call("POST", f"/games/{room}/join", body={"name": "Alpha"})[0] == 409)
check("wrong token refused", call("GET", f"/games/{room}/me", token="nope")[0] == 401)
board = call("GET", f"/games/{room}/board")[1]
check("board is public and has no tokens", "token" not in json.dumps(board))
check("trading is closed in the lobby", call("POST", f"/games/{room}/trade", a["token"], {"startup_id": board["startups"][0]["id"], "shares": 1})[0] == 409)

call("POST", f"/games/{room}/ready", a["token"])
call("POST", f"/games/{room}/ready", b["token"])
board = wait_for(room, "TURN", 1)
check("game started after the countdown", board["turn_no"] == 1)
startup = board["startups"][0]
price1 = startup["price"]

st, me = call("POST", f"/games/{room}/trade", a["token"], {"startup_id": startup["id"], "shares": 20})
check("buy 20 shares", st == 200 and me["cash"] == 600 - 20 * price1, (st, me))
check("cannot sell more than owned", call("POST", f"/games/{room}/trade", a["token"], {"startup_id": startup["id"], "shares": -21})[0] == 409)
check("cannot buy beyond cash", call("POST", f"/games/{room}/trade", a["token"], {"startup_id": startup["id"], "shares": 1000})[0] == 409)
check("zero shares rejected", call("POST", f"/games/{room}/trade", a["token"], {"startup_id": startup["id"], "shares": 0})[0] == 422)
st, tip = call("POST", f"/games/{room}/insider", a["token"])
check("tip in turn 1 costs 5", st == 200 and tip["me"]["cash"] == me["cash"] - 5, (st, tip))
check("ranks hidden during a turn", all(t["rank"] is None for t in call("GET", f"/games/{room}/board")[1]["teams"]))

call("POST", f"/games/{room}/ready", a["token"])
check("ready cannot be undone", call("POST", f"/games/{room}/unready", a["token"])[0] == 409)
check("no trades after ready", call("POST", f"/games/{room}/trade", a["token"], {"startup_id": startup["id"], "shares": -1})[0] == 409)
call("POST", f"/games/{room}/ready", b["token"])
board = wait_for(room, "RESULTS", 1, timeout=10)
check("turn ends when every team is ready", board["phase"] == "RESULTS")
new_price = next(s for s in board["startups"] if s["id"] == startup["id"])
check("new price revealed", new_price["prev_price"] == price1 and new_price["price"] is not None, new_price)
ranks = {t["name"]: t["rank"] for t in board["teams"]}
check("ranks shown, scores hidden", set(ranks) == {"Alpha", "Beta"} and all(t["score"] is None for t in board["teams"]), board["teams"])
_, me_a = call("GET", f"/games/{room}/me", a["token"])
expected_capital = me_a["cash"] + 20 * new_price["price"]
check("capital uses the new price", me_a["capital"] == expected_capital, (me_a, expected_capital))

gains = {g["startup_id"]: g for g in me_a["turn_gains"]}
check("turn gain = shares x price change", startup["id"] in gains
      and gains[startup["id"]]["gain"] == 20 * (new_price["price"] - price1), me_a["turn_gains"])
check("total turn gain is the sum", me_a["turn_gain"] == sum(g["gain"] for g in me_a["turn_gains"]), me_a)
check("config tells the form what the library allows", call("GET", "/config")[1]["startups_available"] >= 5)

wait_for(room, "TURN", 2, timeout=25)
st, me_a = call("POST", f"/games/{room}/trade", a["token"], {"startup_id": startup["id"], "shares": -5})
check("sell at the turn-2 price", st == 200, (st, me_a))
call("POST", f"/games/{room}/ready", a["token"])
call("POST", f"/games/{room}/ready", b["token"])
wait_for(room, "TURN", 3, timeout=30)
call("POST", f"/games/{room}/ready", a["token"])
call("POST", f"/games/{room}/ready", b["token"])
board = wait_for(room, "FINISHED", timeout=10)
check("game finished after the last turn", board["phase"] == "FINISHED")
check("final scores shown", all(t["score"] is not None for t in board["teams"]), board["teams"])
check("chart has a point per turn plus the start", board["chart"] and board["chart"]["turns"] == [0, 1, 2, 3], board["chart"])
_, me_a = call("GET", f"/games/{room}/me", a["token"])
check("score is capital minus 600", me_a["score"] == me_a["capital"] - 600, me_a)

print("\nALL PASSED" if not failures else f"\n{len(failures)} FAILED: {failures}")
sys.exit(1 if failures else 0)
