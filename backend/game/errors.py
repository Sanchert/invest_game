from constants import ErrorCode


class GameError(Exception):
    """A refusal the player should see: carries an HTTP status, a code and a message."""

    def __init__(self, code: ErrorCode, message: str, status: int = 409):
        super().__init__(message)
        self.code = code.value
        self.message = message
        self.status = status
