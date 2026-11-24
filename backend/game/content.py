"""The startup library: import from a validated pack, seed from files."""
import json
import logging
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

import rules
from constants import ErrorCode, Phase
from database import SessionLocal
from game.errors import GameError
from models import Game, GameStartup, Insider, News, Startup, StartupPrice

log = logging.getLogger("invest")


def library_stats(db: Session) -> dict:
    """How many startups there are and how many turns the longest one lasts."""
    count, longest = db.execute(select(func.count(Startup.id), func.max(Startup.last_turn))).one()
    return {"startups_available": count or 0, "turns_available": longest or 0}


def import_pack(db: Session, startups: list) -> dict:
    created = updated = 0
    for s in startups:
        existing = db.execute(select(Startup).where(Startup.slug == s["slug"])).scalar_one_or_none()
        if existing:
            running = db.scalar(
                select(func.count()).select_from(GameStartup)
                .join(Game, Game.id == GameStartup.game_id)
                .where(GameStartup.startup_id == existing.id, Game.phase != Phase.FINISHED))
            if running:
                raise GameError(ErrorCode.STARTUP_IN_USE,
                                f"{s['slug']!r} is used by a game that has not finished.")
            for model in (StartupPrice, News, Insider):
                db.execute(delete(model).where(model.startup_id == existing.id))
            existing.name, existing.description = s["name"], s["description"]
            existing.last_turn = len(s["prices"]) - 1
            startup = existing
            updated += 1
        else:
            startup = Startup(slug=s["slug"], name=s["name"], description=s["description"],
                              last_turn=len(s["prices"]) - 1)
            db.add(startup)
            created += 1
        db.flush()
        for step, price in enumerate(s["prices"], start=1):
            db.add(StartupPrice(startup_id=startup.id, step=step, price=price))
        for n in s["news"]:
            db.add(News(startup_id=startup.id, turn=n["turn"], text=n["text"]))
        for i in s["insiders"]:
            db.add(Insider(startup_id=startup.id, turn=i["turn"], text=i["text"]))
    db.commit()
    return {"created": created, "updated": updated}


def seed_from_dir(directory: Path) -> None:
    """On first start, load content/*.json if the library is empty."""
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(Startup)):
            return
        for path in sorted(directory.glob("*.json")):
            try:
                pack = rules.validate_pack(json.loads(path.read_text(encoding="utf-8")))
                log.info("Seeded %s: %s", path.name, import_pack(db, pack))
            except Exception:
                db.rollback()
                log.exception("Could not seed %s", path.name)
