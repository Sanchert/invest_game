import os

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import database_url, describe_env

# No built-in credentials: everything comes from the environment (.env).
_url = database_url(os.environ)
try:
    make_url(_url)
except ArgumentError:
    raise RuntimeError(
        "The database URL is not valid. Variables visible inside the backend container:\n"
        + describe_env(os.environ)
        + "\nIf POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB are MISSING, "
        "docker-compose.yml is not passing them to the backend "
        "(see backend.environment in the current docker-compose.yml). "
        "If DATABASE_URL is the only one set, its password probably contains "
        "special characters (@ # / $ %): set the POSTGRES_* variables instead."
    ) from None

engine = create_engine(database_url(os.environ), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
