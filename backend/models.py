import enum
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    String, Integer, Float, Boolean, ForeignKey, DateTime, Enum as SqlEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class GameStatus(str, enum.Enum):
    LOBBY = "LOBBY"
    INVESTING = "INVESTING"
    SHOW_NEWS = "SHOW_NEWS"
    BUY_INSIDER = "BUY_INSIDER"
    REBALANCING = "REBALANCING"
    FINISHED = "FINISHED"


class   Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    room_code: Mapped[str] = mapped_column(String(6), unique=True, index=True)
    status: Mapped[GameStatus] = mapped_column(
        SqlEnum(GameStatus, native_enum=False, length=20),
        default=GameStatus.LOBBY
    )

    current_round: Mapped[int] = mapped_column(default=0)
    total_rounds: Mapped[int] = mapped_column(default=5)
    round_duration_mins: Mapped[int] = mapped_column(default=10)
    starting_capital: Mapped[int] = mapped_column(default=600)

    state_end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    teams: Mapped[List["Team"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan"
    )
    startups: Mapped[List["Startup"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan"
    )
    news_pool: Mapped[List["News"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan"
    )
    insider_pool: Mapped[List["Insider"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan"
    )


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))
    name: Mapped[str] = mapped_column(String(50))
    cash: Mapped[int]
    is_ready: Mapped[bool] = mapped_column(default=False)
    session_token: Mapped[str] = mapped_column(String(100), unique=True)

    game: Mapped["Game"] = relationship(
        back_populates="teams"
    )
    portfolios: Mapped[List["Portfolio"]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan"
    )
    bought_insiders: Mapped[List["TeamInsider"]] = relationship(     
        back_populates="team",
        cascade="all, delete-orphan"
    )


class Startup(Base):
    __tablename__ = "startups"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String)
    current_price: Mapped[int] = mapped_column(default=10)

    game: Mapped["Game"] = relationship(
        back_populates="startups"
    )
    portfolios: Mapped[List["Portfolio"]] = relationship(
        back_populates="startup",
        cascade="all, delete-orphan"
    )
    news: Mapped[List["News"]] = relationship(
        back_populates="startup",
        cascade="all, delete-orphan"
    )
    insiders: Mapped[List["Insider"]] = relationship(
        back_populates="startup",
        cascade="all, delete-orphan"
    )


class Portfolio(Base):
    """Таблица-связка: сколько акций конкретного стартапа у конкретной команды"""
    __tablename__ = "portfolios"

    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), primary_key=True)
    startup_id: Mapped[int] = mapped_column(ForeignKey("startups.id"), primary_key=True)
    shares: Mapped[int] = mapped_column(default=0)

    team: Mapped["Team"] = relationship(
        back_populates="portfolios"
    )
    startup: Mapped["Startup"] = relationship(
        back_populates="portfolios"
    )


class News(Base):
    __tablename__ = "news_pool"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))
    startup_id: Mapped[int] = mapped_column(ForeignKey("startups.id"))
    text: Mapped[str] = mapped_column(String)
    multiplier: Mapped[float] = mapped_column(Float)
    is_used: Mapped[bool] = mapped_column(default=False)

    game: Mapped["Game"] = relationship(
        back_populates="news_pool"
    )
    startup: Mapped["Startup"] = relationship(
        back_populates="news"
    )


class Insider(Base):
    __tablename__ = "insider_pool"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))
    startup_id: Mapped[int] = mapped_column(ForeignKey("startups.id"))
    text: Mapped[str] = mapped_column(String)

    game: Mapped["Game"] = relationship(
        back_populates="insider_pool"
    )
    startup: Mapped["Startup"] = relationship(
        back_populates="insiders"
    )


class TeamInsider(Base):
    """История, кто какие инсайды купил, чтобы не выдавать дубликаты"""
    __tablename__ = "team_insiders"

    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id"),
        primary_key=True
    )
    insider_id: Mapped[int] = mapped_column(
        ForeignKey("insider_pool.id"),
        primary_key=True
    )

    team: Mapped["Team"] = relationship(
        back_populates="bought_insiders"
    )
