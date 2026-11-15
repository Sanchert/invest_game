from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class TeamBase(BaseModel):
    name: str


class TeamCreate(TeamBase):
    pass

class LeaderboardEntry(BaseModel):
    team_id: int
    name: str
    cash: int
    portfolio_value: int
    total_wealth: int
    
    class Config:
            from_attributes = True

class StartupBasicResponse(BaseModel):
    id: int
    name: str
    description: str
    current_price: int
    class Config:
        from_attributes = True

class TeamResponse(TeamBase):
    id: int
    cash: int
    is_ready: bool

    class Config:
        from_attributes = True


class GameCreate(BaseModel):
    total_rounds: int = 5
    round_duration_mins: int = 10
    starting_capital: int = 600


class GameResponse(BaseModel):
    id: int
    room_code: str
    status: str
    current_round: int

    class Config:
        from_attributes = True


class TeamResponse(BaseModel):
    id: int
    name: str
    cash: int
    session_token: str

    class Config:
        from_attributes = True


class GameStatusResponse(BaseModel):
    id: int
    room_code: str
    status: str
    teams: List[TeamResponse]

    class Config:
        from_attributes = True


class GameStartResponse(BaseModel):
    status: str
    message: str
    state_end_time: Optional[datetime]


class InvestmentAction(BaseModel):
    startup_id: int
    shares_to_buy: int


class NewsResponse(BaseModel):
    text: str
    multiplier: float

    class Config:
        from_attributes = True


class StartupWithNewsResponse(BaseModel):
    id: int
    name: str
    description: str
    current_price: int
    current_news: Optional[NewsResponse] = None

    class Config:
        from_attributes = True


class StartupImport(BaseModel):
    name: str
    description: str
    base_price: int
    news: List[Dict[str, Any]] = [] # Список новостей вида {"text": "...", "multiplier": 1.5}

class GameImport(BaseModel):
    startups: List[StartupImport]
