"""What players do: create and join a game, get ready, trade, buy insider tips."""
import random
import secrets

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import rules
import settings
from constants import ErrorCode, Phase
from game.common import (get_game_by_code, hash_token, insider_candidates, load_startups,
                         team_by_token, trading_price)
from game.errors import GameError
from game.phases import tick
from game.views import build_me
from models import Game, GameStartup, Holding, Startup, Team, TeamInsider
from presence import presence
from schemas import InsiderBought, InsiderOut


def create_game(db: Session, turns: int, turn_seconds: int, startups_count: int) -> Game:
    rng = random.SystemRandom()
    library = db.execute(select(Startup.id, Startup.last_turn)).all()
    if len(library) < startups_count:
        raise GameError(ErrorCode.NOT_ENOUGH_STARTUPS,
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
        raise GameError(ErrorCode.INTERNAL, "Could not allocate a room code.", 500)
    for sid in chosen_ids:
        db.add(GameStartup(game_id=game.id, startup_id=sid))
    db.commit()
    return game


def join_game(db: Session, code: str, name: str):
    game = get_game_by_code(db, code, "update")
    if game.phase != Phase.LOBBY:
        raise GameError(ErrorCode.GAME_STARTED, "This game has already started.")
    count = db.scalar(select(func.count()).select_from(Team).where(Team.game_id == game.id))
    if count >= settings.MAX_TEAMS:
        raise GameError(ErrorCode.LOBBY_FULL, "This game is full.")
    token = secrets.token_urlsafe(24)
    team = Team(game_id=game.id, name=name, token_hash=hash_token(token),
                cash=settings.STARTING_CAPITAL, ready=False)
    db.add(team)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise GameError(ErrorCode.NAME_TAKEN, "That team name is already used in this game.")
    db.commit()
    presence.touch(team.id)
    tick(db, game.id)  # a new team cancels a running countdown
    return team, token


def leave_game(db: Session, code: str, token: str) -> None:
    game = get_game_by_code(db, code, "update")
    team = team_by_token(db, game, token, lock=True)
    if game.phase != Phase.LOBBY:
        raise GameError(ErrorCode.GAME_STARTED, "You cannot leave a running game.")
    db.delete(team)
    db.commit()
    presence.forget(team.id)
    tick(db, game.id)


def set_ready(db: Session, code: str, token: str, value: bool) -> None:
    game = get_game_by_code(db, code, "share")
    team = team_by_token(db, game, token, lock=True)
    if game.phase == Phase.LOBBY:
        team.ready = value
    elif game.phase == Phase.TURN:
        if not value:
            raise GameError(ErrorCode.READY_IS_FINAL, "Ready cannot be undone.")
        team.ready = True
    else:
        raise GameError(ErrorCode.WRONG_PHASE, "There is nothing to confirm right now.")
    presence.touch(team.id)
    db.commit()
    tick(db, game.id)


def heartbeat(team_id: int) -> None:
    presence.touch(team_id)


def trade(db: Session, code: str, token: str, startup_id: int, shares: int):
    game = get_game_by_code(db, code, "share")  # holds off phase changes until we commit
    team = team_by_token(db, game, token, lock=True)
    if game.phase != Phase.TURN:
        raise GameError(ErrorCode.WRONG_PHASE, "Trading is only open during a turn.")
    if team.ready:
        raise GameError(ErrorCode.ALREADY_READY, "You have already confirmed this turn.")
    info = load_startups(db, game.id)
    if startup_id not in info:
        raise GameError(ErrorCode.STARTUP_NOT_FOUND, "Unknown startup.", 404)
    price = trading_price(info, startup_id, game.turn_no)
    if price is None:
        raise GameError(ErrorCode.STARTUP_CLOSED, "This startup is closed to new trades.")
    holding = db.get(Holding, (team.id, startup_id))
    if shares > 0:
        if price <= 0:
            raise GameError(ErrorCode.PRICE_ZERO, "This startup is worthless: shares cannot be bought.")
        cost = shares * price
        if cost > team.cash:
            raise GameError(ErrorCode.NOT_ENOUGH_CASH, "Not enough cash for that purchase.")
        team.cash -= cost
        if holding:
            holding.shares += shares
        else:
            db.add(Holding(team_id=team.id, startup_id=startup_id, shares=shares))
    else:
        sell = -shares
        if holding is None or holding.shares < sell:
            raise GameError(ErrorCode.NOT_ENOUGH_SHARES, "You do not own that many shares.")
        holding.shares -= sell
        team.cash += sell * price
        if holding.shares == 0:
            db.delete(holding)
    presence.touch(team.id)
    db.commit()
    return build_me(db, game, team)


def buy_insider(db: Session, code: str, token: str) -> InsiderBought:
    game = get_game_by_code(db, code, "share")
    team = team_by_token(db, game, token, lock=True)
    if game.phase != Phase.TURN:
        raise GameError(ErrorCode.WRONG_PHASE, "Tips can only be bought during a turn.")
    if game.turn_no < 2:
        raise GameError(ErrorCode.WRONG_PHASE, "Tips can only be bought from turn 2.")
    if team.ready:
        raise GameError(ErrorCode.ALREADY_READY, "You have already confirmed this turn.")
    cost = rules.insider_cost(game.turn_no, settings.INSIDER_COSTS)
    if team.cash < cost:
        raise GameError(ErrorCode.NOT_ENOUGH_CASH, f"A tip costs {cost}.")
    candidates = insider_candidates(db, game, team.id)
    if not candidates:
        raise GameError(ErrorCode.NO_INSIDERS_LEFT, "No more insider tips are available this turn.")
    insider, startup = random.SystemRandom().choice(candidates)
    db.add(TeamInsider(team_id=team.id, insider_id=insider.id))
    team.cash -= cost
    presence.touch(team.id)
    db.commit()
    return InsiderBought(
        insider=InsiderOut(turn=insider.turn, startup_id=startup.id,
                           startup_name=startup.name, text=insider.text),
        me=build_me(db, game, team),
    )
