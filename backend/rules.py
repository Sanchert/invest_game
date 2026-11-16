"""Pure game rules. No database, no framework: everything here can be unit-tested
with the standard library only (see tests/test_rules.py)."""
import random
import re
from datetime import datetime

ROOM_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I/L
ROOM_CODE_LENGTH = 5
DEFAULT_BUY_PRICE = 10


def make_room_code(rng: random.Random) -> str:
    return "".join(rng.choice(ROOM_ALPHABET) for _ in range(ROOM_CODE_LENGTH))


def rank_scores(scores: dict) -> dict:
    """Competition ranking: 1, 2, 2, 4. Higher score is better."""
    ranks = {}
    prev_score = None
    prev_rank = 0
    for position, (key, score) in enumerate(
        sorted(scores.items(), key=lambda kv: -kv[1]), start=1
    ):
        if score != prev_score:
            prev_rank = position
            prev_score = score
        ranks[key] = prev_rank
    return ranks


def holdings_value(holdings: dict, prices: dict) -> int:
    return sum(shares * prices.get(sid, 0) for sid, shares in holdings.items())


def resolve_turn(cash: int, holdings: dict, turn: int, startups: dict):
    """Pay out the profit of `turn` and redeem shares of startups that close with it.

    startups: {startup_id: {"last_turn": int, "turns": {turn: (buy_price, profit)}}}
    Returns (new_cash, new_holdings, shares_value) where shares_value is valued at
    this turn's buy prices.
    """
    new_holdings = {}
    prices = {}
    for sid, shares in holdings.items():
        if shares <= 0:
            continue
        info = startups[sid]
        if turn > info["last_turn"]:  # defensive: should not happen
            price, _ = info["turns"][info["last_turn"]]
            cash += shares * price
            continue
        price, profit = info["turns"][turn]
        cash += shares * profit
        if turn == info["last_turn"]:
            cash += shares * price  # the startup is closed: shares are redeemed
        else:
            new_holdings[sid] = shares
            prices[sid] = price
    return cash, new_holdings, holdings_value(new_holdings, prices)


def effective_turns(requested: int, last_turns: list) -> int:
    """A game cannot outlast its longest startup."""
    if not last_turns:
        raise ValueError("no startups selected")
    return max(1, min(requested, max(last_turns)))


def lobby_action(n_teams: int, all_ready: bool, min_teams: int,
                 countdown_ends_at, now: datetime) -> str:
    """What the lobby should do on this tick:
    idle | begin_countdown | cancel_countdown | start"""
    if n_teams >= min_teams and all_ready:
        if countdown_ends_at is None:
            return "begin_countdown"
        if now >= countdown_ends_at:
            return "start"
        return "idle"
    return "cancel_countdown" if countdown_ends_at is not None else "idle"


def pick_insider(candidates: list, rng: random.Random):
    return rng.choice(candidates) if candidates else None


_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


def validate_pack(pack) -> list:
    """Validate a content pack and return the list of startup dicts.

    {"startups": [{"slug", "name", "description",
                   "turns": [{"turn": 1, "profit": 3, "buy_price": 10?}, ...],
                   "news": [{"turn": 2, "text": "..."}],
                   "insiders": [{"turn": 2, "text": "..."}]}]}
    """
    if not isinstance(pack, dict) or not isinstance(pack.get("startups"), list):
        raise ValueError('pack must be {"startups": [...]}')
    if not pack["startups"]:
        raise ValueError("pack has no startups")
    seen = set()
    out = []
    for i, s in enumerate(pack["startups"]):
        where = f"startups[{i}]"
        if not isinstance(s, dict):
            raise ValueError(f"{where}: must be an object")
        slug = s.get("slug")
        if not isinstance(slug, str) or not _SLUG.match(slug):
            raise ValueError(f"{where}: slug must be lowercase letters, digits and dashes")
        if slug in seen:
            raise ValueError(f"{where}: duplicate slug {slug!r}")
        seen.add(slug)
        where = f"startup {slug!r}"
        for field in ("name", "description"):
            if not isinstance(s.get(field), str) or not s[field].strip():
                raise ValueError(f"{where}: {field} is required")
        turns = s.get("turns")
        if not isinstance(turns, list) or not turns:
            raise ValueError(f"{where}: turns must be a non-empty list")
        for n, t in enumerate(turns, start=1):
            if not isinstance(t, dict) or t.get("turn") != n:
                raise ValueError(f"{where}: turns must be numbered 1..N in order")
            profit = t.get("profit")
            price = t.get("buy_price", DEFAULT_BUY_PRICE)
            if not isinstance(profit, int) or isinstance(profit, bool) or profit < 0:
                raise ValueError(f"{where}, turn {n}: profit must be a whole number >= 0")
            if not isinstance(price, int) or isinstance(price, bool) or price <= 0:
                raise ValueError(f"{where}, turn {n}: buy_price must be a whole number > 0")
        last_turn = len(turns)
        for kind in ("news", "insiders"):
            for item in s.get(kind, []):
                if (not isinstance(item, dict) or not isinstance(item.get("text"), str)
                        or not item["text"].strip()):
                    raise ValueError(f"{where}: every {kind} item needs text")
                turn = item.get("turn")
                if not isinstance(turn, int) or not 2 <= turn <= last_turn:
                    raise ValueError(
                        f"{where}: {kind} turn must be between 2 and {last_turn}")
        out.append({
            "slug": slug,
            "name": s["name"].strip(),
            "description": s["description"].strip(),
            "turns": [{"turn": t["turn"], "profit": t["profit"],
                       "buy_price": t.get("buy_price", DEFAULT_BUY_PRICE)} for t in turns],
            "news": [{"turn": n["turn"], "text": n["text"].strip()} for n in s.get("news", [])],
            "insiders": [{"turn": n["turn"], "text": n["text"].strip()}
                         for n in s.get("insiders", [])],
        })
    return out
