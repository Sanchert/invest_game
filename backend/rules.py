"""Pure game rules (the Excel model). No database, no framework: everything here can be
unit-tested with the standard library only (see tests/).

Prices: every startup has prices P1..P(L+1), where L is the last turn it is open.
In turn t players trade at P(t). When turn t ends, P(t+1) is revealed and every share is
worth that much. After the last turn the shares are worth the final price."""
import random
import re
from datetime import datetime
from typing import Optional

ROOM_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I/L
ROOM_CODE_LENGTH = 5


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


def insider_cost(turn: int, costs: tuple) -> int:
    """Price of an insider tip in a turn; the last listed price repeats."""
    return costs[min(max(turn, 1), len(costs)) - 1]


def price_at(info: dict, step: Optional[int]) -> Optional[int]:
    """Price of one startup at a step (1..L+1), or None."""
    if step is None:
        return None
    return info["prices"].get(step)


def trading_price(info: dict, turn: int) -> Optional[int]:
    """The price at which the startup can be traded in `turn`; None once it is closed."""
    if turn > info["last_turn"]:
        return None
    return info["prices"].get(turn)


def holdings_value(holdings: dict, startups: dict, step: int) -> int:
    """Shares valued at the prices of `step`. A startup with no price at that step
    (it closed earlier) is valued at its final price."""
    total = 0
    for sid, shares in holdings.items():
        info = startups[sid]
        price = info["prices"].get(step, info["prices"][info["last_turn"] + 1])
        total += shares * price
    return total


def resolve_turn(cash: int, holdings: dict, turn: int, startups: dict):
    """Close `turn`: shares of startups whose story ends are sold at their final price,
    the rest are valued at the newly revealed price P(turn+1).

    startups: {startup_id: {"last_turn": L, "prices": {step: price}}}
    Returns (new_cash, new_holdings, shares_value).
    """
    new_holdings = {}
    for sid, shares in holdings.items():
        if shares <= 0:
            continue
        info = startups[sid]
        if turn >= info["last_turn"]:
            cash += shares * info["prices"][info["last_turn"] + 1]
        else:
            new_holdings[sid] = shares
    return cash, new_holdings, holdings_value(new_holdings, startups, turn + 1)


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


def _whole(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_pack(pack) -> list:
    """Validate a content pack and return the list of startup dicts.

    {"startups": [{"slug", "name", "description",
                   "prices": [10, 41, 86, 9],            # P1..P(L+1), whole numbers
                   "news":     [{"turn": 2, "text": "..."}],   # turns 2..L
                   "insiders": [{"turn": 1, "text": "..."}]}]} # turns 1..L
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
        prices = s.get("prices")
        if not isinstance(prices, list) or len(prices) < 2:
            raise ValueError(f"{where}: prices needs at least 2 values (start and end price)")
        for n, price in enumerate(prices, start=1):
            if not _whole(price) or price < 0:
                raise ValueError(f"{where}, price {n}: must be a whole number >= 0")
        if prices[0] < 1:
            raise ValueError(f"{where}: the first price must be at least 1")
        last_turn = len(prices) - 1
        for kind, first in (("news", 2), ("insiders", 1)):
            for item in s.get(kind, []):
                if (not isinstance(item, dict) or not isinstance(item.get("text"), str)
                        or not item["text"].strip()):
                    raise ValueError(f"{where}: every {kind} item needs text")
                turn = item.get("turn")
                if not _whole(turn) or not first <= turn <= last_turn:
                    raise ValueError(
                        f"{where}: {kind} turn must be between {first} and {last_turn}")
        out.append({
            "slug": slug,
            "name": s["name"].strip(),
            "description": s["description"].strip(),
            "prices": list(prices),
            "news": [{"turn": n["turn"], "text": n["text"].strip()} for n in s.get("news", [])],
            "insiders": [{"turn": n["turn"], "text": n["text"].strip()}
                         for n in s.get("insiders", [])],
        })
    return out
