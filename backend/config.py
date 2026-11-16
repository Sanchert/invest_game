"""Database connection settings. Pure standard library, so it can be unit-tested."""
from urllib.parse import quote


def _clean(value) -> str:
    """Trim whitespace/CR (Windows line endings) and one pair of surrounding quotes."""
    value = (value or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def database_url(env) -> str:
    """Build the SQLAlchemy URL.

    Preferred: POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB (the same variables the
    postgres container uses). They are percent-encoded, so a password such as p@ss#1
    is safe. Fallback: a ready-made DATABASE_URL.
    """
    user = _clean(env.get("POSTGRES_USER"))
    password = _clean(env.get("POSTGRES_PASSWORD"))
    name = _clean(env.get("POSTGRES_DB"))
    if user and password and name:
        host = _clean(env.get("POSTGRES_HOST")) or "db"
        port = _clean(env.get("POSTGRES_PORT")) or "5432"
        return (f"postgresql+psycopg2://{quote(user, safe='')}:{quote(password, safe='')}"
                f"@{host}:{port}/{quote(name, safe='')}")
    url = _clean(env.get("DATABASE_URL"))
    if url:
        return url
    raise RuntimeError(
        "Database is not configured. Set POSTGRES_USER, POSTGRES_PASSWORD and "
        "POSTGRES_DB (or DATABASE_URL) in the .env file next to docker-compose.yml.")
