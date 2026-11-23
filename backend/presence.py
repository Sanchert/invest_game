"""Who is still connected. Kept in memory: it is short-lived, changes every couple of
seconds and does not need to survive a restart (so it never touches the database)."""
import threading
import time


class Presence:
    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._seen = {}
        self._lock = threading.Lock()

    def touch(self, key) -> None:
        with self._lock:
            self._seen[key] = self._clock()

    def idle_seconds(self, key) -> float:
        """Seconds since `key` was last seen. An unknown key counts as just seen,
        so a server restart does not drop everyone from the lobby."""
        with self._lock:
            now = self._clock()
            if key not in self._seen:
                self._seen[key] = now
            return now - self._seen[key]

    def forget(self, key) -> None:
        with self._lock:
            self._seen.pop(key, None)


presence = Presence()
