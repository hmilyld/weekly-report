import threading


class KeyCache:
    def __init__(self) -> None:
        self._store: dict[int, bytes] = {}
        self._lock = threading.Lock()

    def set(self, user_id: int, key: bytes) -> None:
        with self._lock:
            self._store[user_id] = key

    def get(self, user_id: int) -> bytes | None:
        with self._lock:
            return self._store.get(user_id)

    def remove(self, user_id: int) -> None:
        with self._lock:
            self._store.pop(user_id, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


key_cache = KeyCache()
