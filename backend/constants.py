"""Names shared across the backend. Use these instead of bare strings."""
from enum import StrEnum


class Phase(StrEnum):
    LOBBY = "LOBBY"
    TURN = "TURN"
    RESULTS = "RESULTS"
    FINISHED = "FINISHED"


class ErrorCode(StrEnum):
    GAME_NOT_FOUND = "game_not_found"
    UNAUTHORIZED = "unauthorized"
    GAME_STARTED = "game_started"
    LOBBY_FULL = "lobby_full"
    NAME_TAKEN = "name_taken"
    READY_IS_FINAL = "ready_is_final"
    WRONG_PHASE = "wrong_phase"
    ALREADY_READY = "already_ready"
    STARTUP_NOT_FOUND = "startup_not_found"
    STARTUP_CLOSED = "startup_closed"
    PRICE_ZERO = "price_zero"
    NOT_ENOUGH_CASH = "not_enough_cash"
    NOT_ENOUGH_SHARES = "not_enough_shares"
    NO_INSIDERS_LEFT = "no_insiders_left"
    NOT_ENOUGH_STARTUPS = "not_enough_startups"
    STARTUP_IN_USE = "startup_in_use"
    RATE_LIMITED = "rate_limited"
    ADMIN_DISABLED = "admin_disabled"
    FORBIDDEN = "forbidden"
    INVALID_PACK = "invalid_pack"
    INTERNAL = "internal"
