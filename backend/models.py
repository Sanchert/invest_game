from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (Boolean, DateTime, ForeignKey, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _cascade(table: str) -> ForeignKey:
    return ForeignKey(f"{table}.id", ondelete="CASCADE")


# ---------------------------------------------------------------- content library
class Startup(Base):
    __tablename__ = "startups"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    last_turn: Mapped[int] = mapped_column(Integer)  # last turn the startup is open


class StartupTurn(Base):
    """Fixed, predetermined numbers for one startup in one turn."""
    __tablename__ = "startup_turns"
    startup_id: Mapped[int] = mapped_column(_cascade("startups"), primary_key=True)
    turn: Mapped[int] = mapped_column(Integer, primary_key=True)
    buy_price: Mapped[int] = mapped_column(Integer, default=10)
    profit: Mapped[int] = mapped_column(Integer)  # profit per share, paid at turn end


class News(Base):
    __tablename__ = "news"
    id: Mapped[int] = mapped_column(primary_key=True)
    startup_id: Mapped[int] = mapped_column(_cascade("startups"), index=True)
    turn: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)


class Insider(Base):
    __tablename__ = "insiders"
    id: Mapped[int] = mapped_column(primary_key=True)
    startup_id: Mapped[int] = mapped_column(_cascade("startups"), index=True)
    turn: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)


# ---------------------------------------------------------------- game instance
class Game(Base):
    __tablename__ = "games"
    id: Mapped[int] = mapped_column(primary_key=True)
    room_code: Mapped[str] = mapped_column(String(8), unique=True)
    phase: Mapped[str] = mapped_column(String(12), default="LOBBY")  # LOBBY|TURN|RESULTS|FINISHED
    turn_no: Mapped[int] = mapped_column(Integer, default=0)
    turns_total: Mapped[int] = mapped_column(Integer)
    turn_seconds: Mapped[int] = mapped_column(Integer)
    results_seconds: Mapped[int] = mapped_column(Integer, default=15)
    starting_capital: Mapped[int] = mapped_column(Integer, default=600)
    insider_cost: Mapped[int] = mapped_column(Integer, default=30)
    min_teams: Mapped[int] = mapped_column(Integer, default=2)
    phase_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    countdown_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    phase_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GameStartup(Base):
    __tablename__ = "game_startups"
    game_id: Mapped[int] = mapped_column(_cascade("games"), primary_key=True)
    startup_id: Mapped[int] = mapped_column(_cascade("startups"), primary_key=True)


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("game_id", "name", name="uq_team_name_per_game"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(_cascade("games"), index=True)
    name: Mapped[str] = mapped_column(String(30))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)  # sha256 of the token
    cash: Mapped[int] = mapped_column(Integer)
    ready: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Holding(Base):
    __tablename__ = "holdings"
    team_id: Mapped[int] = mapped_column(_cascade("teams"), primary_key=True)
    startup_id: Mapped[int] = mapped_column(_cascade("startups"), primary_key=True)
    shares: Mapped[int] = mapped_column(Integer, default=0)


class TeamInsider(Base):
    """An insider tip a team has bought. The primary key makes each tip one-per-team."""
    __tablename__ = "team_insiders"
    team_id: Mapped[int] = mapped_column(_cascade("teams"), primary_key=True)
    insider_id: Mapped[int] = mapped_column(_cascade("insiders"), primary_key=True)
    purchased_turn: Mapped[int] = mapped_column(Integer)


class Snapshot(Base):
    """A team's position after a turn is resolved (turn 0 = the starting position)."""
    __tablename__ = "snapshots"
    team_id: Mapped[int] = mapped_column(_cascade("teams"), primary_key=True)
    turn_no: Mapped[int] = mapped_column(Integer, primary_key=True)
    cash: Mapped[int] = mapped_column(Integer)
    shares_value: Mapped[int] = mapped_column(Integer)
    score: Mapped[int] = mapped_column(Integer)  # capital minus starting capital
    rank: Mapped[int] = mapped_column(Integer)
