"""Small helpers shared by the rest of the package."""
import hashlib
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

import rules
from constants import ErrorCode
from game.errors import GameError
from models import Game, GameStartup, Insider, Startup, StartupPrice, Team, TeamInsider


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def iso(dt: Optional[datetime]) -> Optional[str]:
    dt = aware(dt)
    return dt.astimezone(timezone.utc).isoformat() if dt else None


def load_startups(db: Session, game_id: int) -> dict:
    """{startup_id: {"startup": Startup, "last_turn": L, "prices": {step: price}}}"""
    rows = db.execute(
        select(Startup)
        .join(GameStartup, GameStartup.startup_id == Startup.id)
        .where(GameStartup.game_id == game_id)
        .order_by(Startup.id)
    ).scalars().all()
    info = {s.id: {"startup": s, "last_turn": s.last_turn, "prices": {}} for s in rows}
    if info:
        for p in db.execute(
            select(StartupPrice).where(StartupPrice.startup_id.in_(list(info)))
        ).scalars():
            info[p.startup_id]["prices"][p.step] = p.price
    return info


def rule_info(info: dict) -> dict:
    """The part of `load_startups` the pure rules need."""
    return {sid: {"last_turn": v["last_turn"], "prices": v["prices"]} for sid, v in info.items()}


def trading_price(info: dict, startup_id: int, turn: int) -> Optional[int]:
    return rules.trading_price(info[startup_id], turn)


def get_game_by_code(db: Session, code: str, lock: Optional[str] = None) -> Game:
    stmt = select(Game).where(Game.room_code == (code or "").strip().upper())
    if lock == "share":
        stmt = stmt.with_for_update(read=True)
    elif lock == "update":
        stmt = stmt.with_for_update()
    game = db.execute(stmt).scalar_one_or_none()
    if game is None:
        raise GameError(ErrorCode.GAME_NOT_FOUND, "No game with this room code.", 404)
    return game


def team_by_token(db: Session, game: Game, token: Optional[str], lock: bool = False) -> Team:
    if not token:
        raise GameError(ErrorCode.UNAUTHORIZED, "Missing team token.", 401)
    stmt = select(Team).where(Team.game_id == game.id, Team.token_hash == hash_token(token))
    if lock:
        stmt = stmt.with_for_update()
    team = db.execute(stmt).scalar_one_or_none()
    if team is None:
        raise GameError(ErrorCode.UNAUTHORIZED, "Unknown team token.", 401)
    return team


def list_teams(db: Session, game_id: int, lock: bool = False) -> list:
    stmt = select(Team).where(Team.game_id == game_id).order_by(Team.id)
    if lock:
        stmt = stmt.with_for_update()
    return list(db.execute(stmt).scalars())


def insider_candidates(db: Session, game: Game, team_id: int) -> list:
    """Tips of the current turn that this team has not bought yet: [(Insider, Startup)]."""
    bought = select(TeamInsider.insider_id).where(TeamInsider.team_id == team_id)
    return db.execute(
        select(Insider, Startup)
        .join(Startup, Startup.id == Insider.startup_id)
        .join(GameStartup, GameStartup.startup_id == Startup.id)
        .where(GameStartup.game_id == game.id, Insider.turn == game.turn_no,
               Startup.last_turn >= game.turn_no, Insider.id.not_in(bought))
    ).all()
