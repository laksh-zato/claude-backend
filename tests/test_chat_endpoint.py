import json

import pytest

from app import app, file_cache


@pytest.fixture(autouse=True)
def clear_cache():
    file_cache._cache.clear()
    yield


def _parse_sse(body: bytes) -> list[dict]:
    out = []
    for line in body.decode().splitlines():
        if line.startswith("data: "):
            out.append(json.loads(line[len("data: "):]))
    return out


def test_chat_with_unknown_file_id_emits_error_event():
    client = app.test_client()
    res = client.post("/chat", json={
        "thread_id": "t1",
        "model": "anthropic/claude-sonnet-4.6",
        "text": "hi",
        "file_ids": ["nonexistent"],
    })
    assert res.status_code == 200
    events = _parse_sse(res.data)
    assert any(e["type"] == "error" and "expired" in e["message"].lower() for e in events)


def test_chat_streams_model_then_done(monkeypatch):
    """End-to-end with a stubbed graph that yields zero LangGraph events."""
    import app as app_mod

    async def fake_astream_events(*a, **kw):
        # Yield no real events — endpoint should still emit model + done
        if False:
            yield {}
        return

    fake_graph = type("G", (), {"astream_events": fake_astream_events})()
    # Pre-set the singleton's `agent` attribute so `.get()` returns the fake.
    app_mod._build_agent_holder.agent = fake_graph

    client = app.test_client()
    res = client.post("/chat", json={
        "thread_id": "t1",
        "model": "anthropic/claude-sonnet-4.6",
        "text": "hi",
        "file_ids": [],
    })
    events = _parse_sse(res.data)
    assert events[0] == {"type": "model", "model": "anthropic/claude-sonnet-4.6"}
    assert events[-1] == {"type": "done"}
