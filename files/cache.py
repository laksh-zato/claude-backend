import uuid
from typing import Optional

from cachetools import TTLCache


class FileCache:
    """In-memory TTL cache keyed by UUID. One per Flask process."""

    def __init__(self, ttl_seconds: int, maxsize: int):
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl_seconds)

    def put(self, payload: dict) -> str:
        file_id = str(uuid.uuid4())
        self._cache[file_id] = payload
        return file_id

    def get(self, file_id: str) -> Optional[dict]:
        return self._cache.get(file_id)

    def delete(self, file_id: str) -> None:
        self._cache.pop(file_id, None)
