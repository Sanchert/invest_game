from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from constants import Phase


class CreateGameIn(BaseModel):
    turns: int = Field(ge=1, le=20)
    turn_seconds: int = Field(ge=10, le=3600)
    startups_count: int = Field(default=5, ge=1, le=12)


class CreateGameOut(BaseModel):
    room_code: str
    turns_total: int
    turn_seconds: int
    startups_count: int


class JoinIn(BaseModel):
    name: str = Field(min_length=1, max_length=30)

    @field_validator("name")
    @classmethod
    def clean(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("name must not be empty")
        return v


class JoinOut(BaseModel):
    team_id: int
    name: str
    token: str


class TradeIn(BaseModel):
    startup_id: int
    shares: int = Field(ge=-1000, le=1000)  # positive = buy, negative = sell

    @field_validator("shares")
    @classmethod
    def nonzero(cls, v: int) -> int:
        if v == 0:
            raise ValueError("shares must not be zero")
        return v


# ----------------------------------------------------------------------- board
class BoardTeam(BaseModel):
    id: int
    name: str
    ready: bool
    rank: Optional[int] = None    # only in RESULTS / FINISHED
    score: Optional[int] = None   # only in FINISHED


class BoardStartup(BaseModel):
    id: int
    name: str
    description: str
    open: bool
    last_turn: int
    price: Optional[int] = None       # trading price (turn) or the newly revealed price (results)
    prev_price: Optional[int] = None  # results only: the price before the turn ended
    news: Optional[str] = None


class ChartSeries(BaseModel):
    team: str
    scores: List[int]


class ChartStartup(BaseModel):
    """Price history of one startup across all turns."""
    id: int
    name: str
    scores: List[Optional[int]]  # index = turn number; None = not yet open


class ChartTurn(BaseModel):
    """One column of the price bar chart: prices of all startups at a given turn."""
    turn: int
    prices: List[Optional[int]]  # aligned with chart.startups


class Chart(BaseModel):
    turns: List[int]
    series: List[ChartSeries]
    startups: List[ChartStartup]
    price_turns: List[ChartTurn]


class BoardOut(BaseModel):
    room_code: str
    phase: Phase
    turn_no: int
    turns_total: int
    turn_seconds: int
    min_teams: int
    server_time: str
    phase_ends_at: Optional[str] = None
    countdown_ends_at: Optional[str] = None
    teams: List[BoardTeam]
    startups: List[BoardStartup]
    chart: Optional[Chart] = None


# ------------------------------------------------------------------------- me
class HoldingOut(BaseModel):
    startup_id: int
    shares: int


class InsiderOut(BaseModel):
    turn: int
    startup_id: int
    startup_name: str
    text: str


class TurnGainOut(BaseModel):
    startup_id: int
    shares: int
    gain: int


class MeOut(BaseModel):
    team_id: int
    name: str
    ready: bool
    cash: int
    capital: int
    holdings: List[HoldingOut]
    insiders: List[InsiderOut]
    insider_cost: int
    insiders_left: int
    rank: Optional[int] = None
    score: Optional[int] = None
    turn_gains: List[TurnGainOut] = []   # results of the last turn: what each startup brought
    turn_gain: Optional[int] = None      # their sum


class InsiderBought(BaseModel):
    insider: InsiderOut
    me: MeOut


class ConfigOut(BaseModel):
    public_url: Optional[str] = None   # where players should go, if the server knows it
    startups_available: int = 0        # startups in the library
    turns_available: int = 0           # the longest game the library allows


class ErrorOut(BaseModel):
    code: str
    message: str
