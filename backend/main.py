import asyncio
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Body, Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import game as game_engine
import models  # noqa: F401  (registers the tables)
import rules
from database import Base, engine as db_engine, get_db
from constants import ErrorCode
from game import GameError
from config import public_url
from schemas import (BoardOut, ConfigOut, CreateGameIn, CreateGameOut, InsiderBought, JoinIn,
                     JoinOut, MeOut, TradeIn)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("invest")

ADMIN_KEY = os.environ.get("ADMIN_KEY", "")
PUBLIC_URL = public_url(os.environ)
CONTENT_DIR = Path(__file__).parent / "content"


async def timer_loop() -> None:
    while True:
        try:
            await asyncio.to_thread(game_engine.tick_all)
        except Exception:
            log.exception("timer loop error")
        await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(db_engine)
    game_engine.seed_from_dir(CONTENT_DIR)
    task = asyncio.create_task(timer_loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(title="Invest Game", lifespan=lifespan)


@app.exception_handler(GameError)
async def game_error_handler(_request: Request, exc: GameError):
    return JSONResponse(status_code=exc.status,
                        content={"code": exc.code, "message": exc.message})


# Anyone can create a room, so keep it from being used to flood the database.
_create_hits: dict = {}


def _rate_limit_create(ip: str, limit: int = 10, window: int = 60) -> None:
    now = time.monotonic()
    hits = [h for h in _create_hits.get(ip, []) if now - h < window]
    if len(hits) >= limit:
        raise GameError(ErrorCode.RATE_LIMITED, "Too many games created. Try again in a minute.", 429)
    hits.append(now)
    _create_hits[ip] = hits


TeamToken = Header(default=None, alias="X-Team-Token")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config", response_model=ConfigOut)
def client_config():
    return ConfigOut(public_url=PUBLIC_URL)


@app.post("/api/games", response_model=CreateGameOut)
def create_game(body: CreateGameIn, request: Request, db: Session = Depends(get_db)):
    _rate_limit_create(request.client.host if request.client else "unknown")
    game = game_engine.create_game(db, body.turns, body.turn_seconds, body.startups_count)
    return CreateGameOut(room_code=game.room_code, turns_total=game.turns_total,
                         turn_seconds=game.turn_seconds, startups_count=body.startups_count)


@app.get("/api/games/{code}/board", response_model=BoardOut)
def board(code: str, db: Session = Depends(get_db)):
    game = game_engine.get_game_by_code(db, code)
    return game_engine.build_board(db, game)


@app.post("/api/games/{code}/join", response_model=JoinOut)
def join(code: str, body: JoinIn, db: Session = Depends(get_db)):
    team, token = game_engine.join_game(db, code, body.name)
    return JoinOut(team_id=team.id, name=team.name, token=token)


@app.get("/api/games/{code}/me", response_model=MeOut)
def me(code: str, token: Optional[str] = TeamToken, db: Session = Depends(get_db)):
    game = game_engine.get_game_by_code(db, code)
    team = game_engine.team_by_token(db, game, token)
    game_engine.heartbeat(team.id)
    return game_engine.build_me(db, game, team)


@app.post("/api/games/{code}/ready", status_code=204)
def ready(code: str, token: Optional[str] = TeamToken, db: Session = Depends(get_db)):
    game_engine.set_ready(db, code, token, True)


@app.post("/api/games/{code}/unready", status_code=204)
def unready(code: str, token: Optional[str] = TeamToken, db: Session = Depends(get_db)):
    game_engine.set_ready(db, code, token, False)


@app.post("/api/games/{code}/leave", status_code=204)
def leave(code: str, token: Optional[str] = TeamToken, db: Session = Depends(get_db)):
    game_engine.leave_game(db, code, token)


@app.post("/api/games/{code}/trade", response_model=MeOut)
def trade(code: str, body: TradeIn, token: Optional[str] = TeamToken, db: Session = Depends(get_db)):
    return game_engine.trade(db, code, token, body.startup_id, body.shares)


@app.post("/api/games/{code}/insider", response_model=InsiderBought)
def insider(code: str, token: Optional[str] = TeamToken, db: Session = Depends(get_db)):
    return game_engine.buy_insider(db, code, token)


@app.post("/api/admin/content")
def import_content(payload: dict = Body(...),
                   x_admin_key: str = Header(default="", alias="X-Admin-Key"),
                   db: Session = Depends(get_db)):
    if not ADMIN_KEY:
        raise GameError(ErrorCode.ADMIN_DISABLED, "Set ADMIN_KEY to enable content import.", 503)
    if not secrets.compare_digest(x_admin_key.encode(), ADMIN_KEY.encode()):
        raise GameError(ErrorCode.FORBIDDEN, "Wrong admin key.", 403)
    try:
        startups = rules.validate_pack(payload)
    except ValueError as exc:
        raise GameError(ErrorCode.INVALID_PACK, str(exc), 422)
    return game_engine.import_pack(db, startups)
