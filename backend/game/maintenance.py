"""Housekeeping done by the background timer."""
import logging
from datetime import datetime, timedelta

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.orm import Session

import settings
from constants import Phase
from database import SessionLocal
from game.phases import tick
from models import Game, utcnow

log = logging.getLogger("invest")
_last_cleanup = 0.0


def cleanup(db: Session) -> None:
    """Delete old games (their teams, holdings and snapshots go with them)."""
    now = utcnow()
    db.execute(delete(Game).where(or_(
        and_(Game.phase == Phase.FINISHED, Game.phase_changed_at < now - timedelta(hours=24)),
        and_(Game.phase == Phase.LOBBY, Game.created_at < now - timedelta(hours=2)),
        and_(Game.phase.in_((Phase.TURN.value, Phase.RESULTS.value)),
             Game.phase_changed_at < now - timedelta(hours=6)),
    )))
    db.commit()


def tick_all() -> None:
    """Called once a second by the background timer."""
    global _last_cleanup
    with SessionLocal() as db:
        ids = list(db.scalars(select(Game.id).where(Game.phase != Phase.FINISHED)))
    for game_id in ids:
        with SessionLocal() as db:
            try:
                tick(db, game_id)
            except Exception:
                db.rollback()
                log.exception("tick failed for game %s", game_id)
    now = datetime.now().timestamp()
    if now - _last_cleanup > settings.CLEANUP_EVERY_SECONDS:
        _last_cleanup = now
        with SessionLocal() as db:
            try:
                cleanup(db)
            except Exception:
                db.rollback()
                log.exception("cleanup failed")
