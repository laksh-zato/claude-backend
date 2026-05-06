import pytest
from files.cache import FileCache


def test_put_returns_uuid_and_get_round_trips():
    cache = FileCache(ttl_seconds=60, maxsize=10)
    payload = {"kind": "text", "filename": "x.csv", "mime": "text/csv", "text": "..."}
    file_id = cache.put(payload)
    assert isinstance(file_id, str)
    assert cache.get(file_id) == payload


def test_get_missing_returns_none():
    cache = FileCache(ttl_seconds=60, maxsize=10)
    assert cache.get("nonexistent-id") is None


def test_delete_removes_entry():
    cache = FileCache(ttl_seconds=60, maxsize=10)
    file_id = cache.put({"kind": "text"})
    cache.delete(file_id)
    assert cache.get(file_id) is None


def test_delete_unknown_is_noop():
    cache = FileCache(ttl_seconds=60, maxsize=10)
    cache.delete("nonexistent")  # must not raise
