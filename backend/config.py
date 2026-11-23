"""Settings read from the environment. Pure standard library, so it can be unit-tested."""
from typing import Optional
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


def describe_env(env) -> str:
    """A secret-free summary of what the container sees, for error messages."""
    def state(name):
        value = _clean(env.get(name))
        return f"set ({len(value)} characters)" if value else "MISSING or empty"
    lines = [f"  {name}: {state(name)}" for name in
             ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "DATABASE_URL")]
    return "\n".join(lines)


def public_url(env) -> Optional[str]:
    """The address players type on their phones, e.g. http://192.168.0.10:8080.

    Set by start.py (it finds the laptop's address) or by hand in .env as PUBLIC_URL.
    A missing scheme is added; anything that is not http(s) is ignored."""
    raw = _clean(env.get("PUBLIC_URL"))
    if not raw:
        return None
    if "://" not in raw:
        raw = "http://" + raw
    raw = raw.rstrip("/")
    return raw if raw.lower().startswith(("http://", "https://")) and len(raw) > 8 else None
