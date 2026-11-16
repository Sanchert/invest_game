"""Game engine: everything that touches the database.

Locking order is always: game row, then team rows. The timer loop and the player
endpoints both follow it, so they cannot deadlock, and every phase transition is
decided while holding the game row lock, so it can only happen once.
"""
import hashlib
import json
import logging
import random
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import rules
from database import SessionLocal
from models import (Game, GameStartup, Holding, Insider, News, Snapshot, Startup,
                    StartupTurn, Team, TeamInsider, utcnow)
from schemas import (BoardOut, BoardStartup, BoardTeam, Chart, ChartSeries,
                     HoldingOut, InsiderBought, InsiderOut, MeOut, ProfitPoint)

log = logging.getLogger("invest")

COUNTDOWN_SECONDS = 10      # lobby countdown once every joined team is ready
STALE_LOBBY_SECONDS = 60    # a team that stops polling in the lobby is dropped
MAX_TEAMS = 20
CLEANUP_EVERY_SECONDS = 60


class GameError(Exception):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


# ------------------------------------------------------------------ small helpers
def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def iso(dt: Optional[datetime]) -> Optional[str]:
    dt = _aware(dt)
    return dt.astimezone(timezone.utc).isoformat() if dt else None


def load_startups(db: Session, game_id: int) -> dict:
    rows = db.execute(
        select(Startup)
        .join(GameStartup, GameStartup.startup_id == Startup.id)
        .where(GameStartup.game_id == game_id)
        .order_by(Startup.id)
    ).scalars().all()
    info = {s.id: {"startup": s, "last_turn": s.last_turn, "turns": {}} for s in rows}
    if info:
        for t in db.execute(
            select(StartupTurn).where(StartupTurn.startup_id.in_(list(info)))
        ).scalars():
            info[t.startup_id]["turns"][t.turn] = (t.buy_price, t.profit)
    return info


def price_at(info: dict, startup_id: int, turn: Optional[int]) -> Optional[int]:
    """Buy price of a startup in a turn, or None if it is closed (or turn unknown)."""
    if turn is None:
        return None
    entry = info[startup_id]
    if turn > entry["last_turn"] or turn not in entry["turns"]:
        return None
    return entry["turns"][turn][0]


def get_game_by_code(db: Session, code: str, lock: Optional[str] = None) -> Game:
    stmt = select(Game).where(Game.room_code == (code or "").strip().upper())
    if lock == "share":
        stmt = stmt.with_for_update(read=True)
    elif lock == "update":
        stmt = stmt.with_for_update()
    game = db.execute(stmt).scalar_one_or_none()
    if game is None:
        raise GameError("game_not_found", "No game with this room code.", 404)
    return game


def team_by_token(db: Session, game: Game, token: Optional[str], lock: bool = False) -> Team:
    if not token:
        raise GameError("unauthorized", "Missing team token.", 401)
    stmt = select(Team).where(Team.game_id == game.id, Team.token_hash == hash_token(token))
    if lock:
        stmt = stmt.with_for_update()
    team = db.execute(stmt).scalar_one_or_none()
    if team is None:
        raise GameError("unauthorized", "Unknown team token.", 401)
    return team


def _teams(db: Session, game_id: int, lock: bool = False) -> list:
    stmt = select(Team).where(Team.game_id == game_id).order_by(Team.id)
    if lock:
        stmt = stmt.with_for_update()
    return list(db.execute(stmt).scalars())


# ------------------------------------------------------------- the phase machine
def tick(db: Session, game_id: int) -> None:
    """Advance a game if (and only if) something is due. Safe to call at any time,
    from any process, as often as you like."""
    game = db.execute(
        select(Game).where(Game.id == game_id).with_for_update()
    ).scalar_one_or_none()
    if game is None or game.phase == "FINISHED":
        db.rollback()
        return
    t = utcnow()
    if game.phase == "LOBBY":
        _tick_lobby(db, game, t)
    elif game.phase == "TURN":
        ends = _aware(game.phase_ends_at)
        due = ends is not None and t >= ends
        teams = _teams(db, game.id)
        if due or (teams and all(x.ready for x in teams)):
            _end_turn(db, game, t)
    elif game.phase == "RESULTS":
        ends = _aware(game.phase_ends_at)
        if ends is not None and t >= ends:
            _begin_turn(db, game, game.turn_no + 1, t)
    db.commit()


def _tick_lobby(db: Session, game: Game, t: datetime) -> None:
    teams = _teams(db, game.id, lock=True)
    cutoff = t - timedelta(seconds=STALE_LOBBY_SECONDS)
    alive = []
    for team in teams:
        if _aware(team.last_seen) < cutoff:
            db.delete(team)
        else:
            alive.append(team)
    action = rules.lobby_action(
        len(alive),
        bool(alive) and all(x.ready for x in alive),
        game.min_teams,
        _aware(game.countdown_ends_at),
        t,
    )
    if action == "begin_countdown":
        game.countdown_ends_at = t + timedelta(seconds=COUNTDOWN_SECONDS)
    elif action == "cancel_countdown":
        game.countdown_ends_at = None
    elif action == "start":
        game.countdown_ends_at = None
        _begin_turn(db, game, 1, t, alive)


def _begin_turn(db: Session, game: Game, turn_no: int, t: datetime,
                teams: Optional[list] = None) -> None:
    teams = teams if teams is not None else _teams(db, game.id, lock=True)
    game.phase = "TURN"
    game.turn_no = turn_no
    game.phase_ends_at = t + timedelta(seconds=game.turn_seconds)
    game.phase_changed_at = t
    for team in teams:
        team.ready = False
        if turn_no == 1:  # baseline point for the final chart
            db.add(Snapshot(team_id=team.id, turn_no=0, cash=team.cash,
                            shares_value=0, score=0, rank=1))


def _end_turn(db: Session, game: Game, t: datetime) -> None:
    teams = _teams(db, game.id, lock=True)
    holdings_by_team: dict = {}
    if teams:
        for h in db.execute(
            select(Holding).where(Holding.team_id.in_([x.id for x in teams]))
        ).scalars():
            holdings_by_team.setdefault(h.team_id, []).append(h)
    info = load_startups(db, game.id)
    rule_info = {sid: {"last_turn": v["last_turn"], "turns": v["turns"]}
                 for sid, v in info.items()}

    scores, parts = {}, {}
    for team in teams:
        rows = holdings_by_team.get(team.id, [])
        cash, new_holdings, value = rules.resolve_turn(
            team.cash, {h.startup_id: h.shares for h in rows}, game.turn_no, rule_info)
        team.cash = cash
        team.ready = True  # a team that never pressed Ready is confirmed automatically
        for h in rows:
            if h.startup_id in new_holdings:
                h.shares = new_holdings[h.startup_id]
            else:
                db.delete(h)
        scores[team.id] = cash + value - game.starting_capital
        parts[team.id] = (cash, value)

    ranks = rules.rank_scores(scores)
    for team in teams:
        cash, value = parts[team.id]
        db.add(Snapshot(team_id=team.id, turn_no=game.turn_no, cash=cash,
                        shares_value=value, score=scores[team.id], rank=ranks[team.id]))

    game.phase_changed_at = t
    if game.turn_no >= game.turns_total:
        game.phase = "FINISHED"
        game.phase_ends_at = None
    else:
        game.phase = "RESULTS"
        game.phase_ends_at = t + timedelta(seconds=game.results_seconds)


# ------------------------------------------------------------- player operations
def create_game(db: Session, turns: int, turn_seconds: int, startups_count: int) -> Game:
    rng = random.SystemRandom()
    library = db.execute(select(Startup.id, Startup.last_turn)).all()
    if len(library) < startups_count:
        raise GameError("not_enough_startups",
                        f"The library has only {len(library)} startups.", 422)
    chosen = rng.sample(library, startups_count)
    chosen_ids = [row[0] for row in chosen]
    turns_total = rules.effective_turns(turns, [row[1] for row in chosen])
    for _ in range(10):
        game = Game(room_code=rules.make_room_code(rng), turns_total=turns_total,
                    turn_seconds=turn_seconds)
        db.add(game)
        try:
            db.flush()
            break
        except IntegrityError:
            db.rollback()
    else:
        raise GameError("internal", "Could not allocate a room code.", 500)
    for sid in chosen_ids:
        db.add(GameStartup(game_id=game.id, startup_id=sid))
    db.commit()
    return game


def join_game(db: Session, code: str, name: str):
    game = get_game_by_code(db, code, "update")
    if game.phase != "LOBBY":
        raise GameError("game_started", "This game has already started.")
    count = db.scalar(select(func.count()).select_from(Team).where(Team.game_id == game.id))
    if count >= MAX_TEAMS:
        raise GameError("lobby_full", "This game is full.")
    token = secrets.token_urlsafe(24)
    team = Team(game_id=game.id, name=name, token_hash=hash_token(token),
                cash=game.starting_capital, ready=False)
    db.add(team)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise GameError("name_taken", "That team name is already used in this game.")
    db.commit()
    tick(db, game.id)  # a new team cancels a running countdown
    return team, token


def leave_game(db: Session, code: str, token: str) -> None:
    game = get_game_by_code(db, code, "update")
    team = team_by_token(db, game, token, lock=True)
    if game.phase != "LOBBY":
        raise GameError("game_started", "You cannot leave a running game.")
    db.delete(team)
    db.commit()
    tick(db, game.id)


def set_ready(db: Session, code: str, token: str, value: bool) -> None:
    game = get_game_by_code(db, code, "share")
    team = team_by_token(db, game, token, lock=True)
    if game.phase == "LOBBY":
        team.ready = value
    elif game.phase == "TURN":
        if not value:
            raise GameError("ready_is_final", "Ready cannot be undone.")
        team.ready = True
    else:
        raise GameError("wrong_phase", "There is nothing to confirm right now.")
    team.last_seen = utcnow()
    db.commit()
    tick(db, game.id)


def heartbeat(db: Session, team_id: int) -> None:
    db.execute(Team.__table__.update().where(Team.id == team_id).values(last_seen=utcnow()))
    db.commit()


def trade(db: Session, code: str, token: str, startup_id: int, shares: int) -> MeOut:
    game = get_game_by_code(db, code, "share")  # holds off phase changes until we commit
    team = team_by_token(db, game, token, lock=True)
    if game.phase != "TURN":
        raise GameError("wrong_phase", "Trading is only open during a turn.")
    if team.ready:
        raise GameError("already_ready", "You have already confirmed this turn.")
    info = load_startups(db, game.id)
    if startup_id not in info:
        raise GameError("startup_not_found", "Unknown startup.", 404)
    price = price_at(info, startup_id, game.turn_no)
    if price is None:
        raise GameError("startup_closed", "This startup is closed to new trades.")
    holding = db.get(Holding, (team.id, startup_id))
    if shares > 0:
        cost = shares * price
        if cost > team.cash:
            raise GameError("not_enough_cash", "Not enough cash for that purchase.")
        team.cash -= cost
        if holding:
            holding.shares += shares
        else:
            db.add(Holding(team_id=team.id, startup_id=startup_id, shares=shares))
    else:
        sell = -shares
        if holding is None or holding.shares < sell:
            raise GameError("not_enough_shares", "You do not own that many shares.")
        holding.shares -= sell
        team.cash += sell * price
        if holding.shares == 0:
            db.delete(holding)
    team.last_seen = utcnow()
    db.commit()
    return build_me(db, game, team)


def _insider_candidates(db: Session, game: Game, team_id: int) -> list:
    bought = select(TeamInsider.insider_id).where(TeamInsider.team_id == team_id)
    return db.execute(
        select(Insider, Startup)
        .join(Startup, Startup.id == Insider.startup_id)
        .join(GameStartup, GameStartup.startup_id == Startup.id)
        .where(GameStartup.game_id == game.id, Insider.turn == game.turn_no,
               Startup.last_turn >= game.turn_no, Insider.id.not_in(bought))
    ).all()


def buy_insider(db: Session, code: str, token: str) -> InsiderBought:
    game = get_game_by_code(db, code, "share")
    team = team_by_token(db, game, token, lock=True)
    if game.phase != "TURN":
        raise GameError("wrong_phase", "Tips can only be bought during a turn.")
    if game.turn_no < 2:
        raise GameError("no_tips_yet", "Insider tips start in turn 2.")
    if team.ready:
        raise GameError("already_ready", "You have already confirmed this turn.")
    if team.cash < game.insider_cost:
        raise GameError("not_enough_cash", f"A tip costs {game.insider_cost}.")
    candidates = _insider_candidates(db, game, team.id)
    if not candidates:
        raise GameError("no_insiders_left", "No more insider tips are available this turn.")
    insider, startup = random.SystemRandom().choice(candidates)
    db.add(TeamInsider(team_id=team.id, insider_id=insider.id, purchased_turn=game.turn_no))
    team.cash -= game.insider_cost
    team.last_seen = utcnow()
    db.commit()
    return InsiderBought(
        insider=InsiderOut(turn=insider.turn, startup_id=startup.id,
                           startup_name=startup.name, text=insider.text),
        me=build_me(db, game, team),
    )


# ---------------------------------------------------------------- read models
def build_me(db: Session, game: Game, team: Team) -> MeOut:
    info = load_startups(db, game.id)
    rows = db.execute(select(Holding).where(Holding.team_id == team.id)
                      .order_by(Holding.startup_id)).scalars().all()
    val_turn = max(game.turn_no, 1)
    shares_value = 0
    for h in rows:
        price = price_at(info, h.startup_id, val_turn)
        if price is None:
            price = info[h.startup_id]["turns"][info[h.startup_id]["last_turn"]][0]
        shares_value += h.shares * price
    capital = team.cash + shares_value

    tips = db.execute(
        select(Insider, Startup, TeamInsider)
        .join(TeamInsider, TeamInsider.insider_id == Insider.id)
        .join(Startup, Startup.id == Insider.startup_id)
        .where(TeamInsider.team_id == team.id)
        .order_by(TeamInsider.purchased_turn, Insider.id)
    ).all()
    left = 0
    if game.phase == "TURN" and game.turn_no >= 2:
        left = len(_insider_candidates(db, game, team.id))

    rank = score = None
    if game.phase in ("RESULTS", "FINISHED"):
        snap = db.get(Snapshot, (team.id, game.turn_no))
        if snap:
            rank = snap.rank
            if game.phase == "FINISHED":
                score = snap.score
    return MeOut(
        team_id=team.id, name=team.name, ready=team.ready, cash=team.cash, capital=capital,
        holdings=[HoldingOut(startup_id=h.startup_id, shares=h.shares) for h in rows],
        insiders=[InsiderOut(turn=i.turn, startup_id=s.id, startup_name=s.name, text=i.text)
                  for i, s, _ in tips],
        insider_cost=game.insider_cost, insiders_left=left, rank=rank, score=score,
    )


def build_board(db: Session, game: Game) -> BoardOut:
    teams = _teams(db, game.id)
    info = load_startups(db, game.id)
    phase = game.phase
    show_ranks = phase in ("RESULTS", "FINISHED")
    resolved = game.turn_no if show_ranks else max(game.turn_no - 1, 0)
    if phase == "TURN":
        ref_turn = game.turn_no
    elif phase == "RESULTS":
        ref_turn = game.turn_no + 1
    elif phase == "LOBBY":
        ref_turn = 1
    else:
        ref_turn = None

    snaps = {}
    if show_ranks and teams:
        for s in db.execute(select(Snapshot).where(
                Snapshot.team_id.in_([x.id for x in teams]),
                Snapshot.turn_no == game.turn_no)).scalars():
            snaps[s.team_id] = s

    news_by_startup: dict = {}
    if phase == "TURN" and game.turn_no >= 2 and info:
        for n in db.execute(select(News).where(
                News.turn == game.turn_no, News.startup_id.in_(list(info)))
                .order_by(News.id)).scalars():
            news_by_startup.setdefault(n.startup_id, []).append(n.text)

    startups = []
    for sid, entry in info.items():
        s = entry["startup"]
        is_open = ref_turn is not None and ref_turn <= entry["last_turn"]
        startups.append(BoardStartup(
            id=sid, name=s.name, description=s.description, open=is_open,
            last_turn=entry["last_turn"],
            price=price_at(info, sid, ref_turn) if is_open else None,
            news="\n".join(news_by_startup[sid]) if sid in news_by_startup else None,
            profits=[ProfitPoint(turn=n, profit=entry["turns"][n][1])
                     for n in range(1, resolved + 1) if n in entry["turns"]],
        ))

    chart = None
    if phase == "FINISHED" and teams:
        by_team: dict = {x.id: {} for x in teams}
        for s in db.execute(select(Snapshot).where(
                Snapshot.team_id.in_(list(by_team)))).scalars():
            by_team[s.team_id][s.turn_no] = s.score
        order = sorted(teams, key=lambda x: snaps[x.id].rank if x.id in snaps else 99)
        chart = Chart(
            turns=list(range(0, game.turns_total + 1)),
            series=[ChartSeries(team=x.name,
                                scores=[by_team[x.id].get(n, 0)
                                        for n in range(0, game.turns_total + 1)])
                    for x in order],
        )

    return BoardOut(
        room_code=game.room_code, phase=phase, turn_no=game.turn_no,
        turns_total=game.turns_total, turn_seconds=game.turn_seconds,
        min_teams=game.min_teams, server_time=iso(utcnow()),
        phase_ends_at=iso(game.phase_ends_at), countdown_ends_at=iso(game.countdown_ends_at),
        teams=[BoardTeam(
            id=x.id, name=x.name, ready=x.ready,
            rank=snaps[x.id].rank if x.id in snaps else None,
            score=snaps[x.id].score if (phase == "FINISHED" and x.id in snaps) else None,
        ) for x in teams],
        startups=startups, chart=chart,
    )


# --------------------------------------------------------------- content library
def import_pack(db: Session, startups: list) -> dict:
    created = updated = 0
    for s in startups:
        existing = db.execute(select(Startup).where(Startup.slug == s["slug"])).scalar_one_or_none()
        if existing:
            running = db.scalar(
                select(func.count()).select_from(GameStartup)
                .join(Game, Game.id == GameStartup.game_id)
                .where(GameStartup.startup_id == existing.id, Game.phase != "FINISHED"))
            if running:
                raise GameError("startup_in_use",
                                f"{s['slug']!r} is used by a game that has not finished.")
            for model in (StartupTurn, News, Insider):
                db.execute(delete(model).where(model.startup_id == existing.id))
            existing.name, existing.description = s["name"], s["description"]
            existing.last_turn = len(s["turns"])
            startup = existing
            updated += 1
        else:
            startup = Startup(slug=s["slug"], name=s["name"], description=s["description"],
                              last_turn=len(s["turns"]))
            db.add(startup)
            created += 1
        db.flush()
        for t in s["turns"]:
            db.add(StartupTurn(startup_id=startup.id, turn=t["turn"],
                               buy_price=t["buy_price"], profit=t["profit"]))
        for n in s["news"]:
            db.add(News(startup_id=startup.id, turn=n["turn"], text=n["text"]))
        for i in s["insiders"]:
            db.add(Insider(startup_id=startup.id, turn=i["turn"], text=i["text"]))
    db.commit()
    return {"created": created, "updated": updated}


def seed_from_dir(directory: Path) -> None:
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(Startup)):
            return
        for path in sorted(directory.glob("*.json")):
            try:
                pack = rules.validate_pack(json.loads(path.read_text(encoding="utf-8")))
                result = import_pack(db, pack)
                log.info("Seeded %s: %s", path.name, result)
            except Exception:
                db.rollback()
                log.exception("Could not seed %s", path.name)


# ------------------------------------------------------------------ maintenance
_last_cleanup = 0.0


def cleanup(db: Session) -> None:
    t = utcnow()
    db.execute(delete(Game).where(or_(
        and_(Game.phase == "FINISHED", Game.phase_changed_at < t - timedelta(hours=24)),
        and_(Game.phase == "LOBBY", Game.created_at < t - timedelta(hours=2)),
        and_(Game.phase.in_(("TURN", "RESULTS")),
             Game.phase_changed_at < t - timedelta(hours=6)),
    )))
    db.commit()


def tick_all() -> None:
    """Called once a second by the background timer."""
    global _last_cleanup
    with SessionLocal() as db:
        ids = list(db.scalars(select(Game.id).where(Game.phase != "FINISHED")))
    for game_id in ids:
        with SessionLocal() as db:
            try:
                tick(db, game_id)
            except Exception:
                db.rollback()
                log.exception("tick failed for game %s", game_id)
    now_s = datetime.now().timestamp()
    if now_s - _last_cleanup > CLEANUP_EVERY_SECONDS:
        _last_cleanup = now_s
        with SessionLocal() as db:
            try:
                cleanup(db)
            except Exception:
                db.rollback()
                log.exception("cleanup failed")
