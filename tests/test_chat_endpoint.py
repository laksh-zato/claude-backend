import json
import logging

import httpx
import pytest
from openai import AuthenticationError

import app as app_mod
from app import app, file_cache


def _fake_auth_error(message: str) -> AuthenticationError:
    """Construct a real openai.AuthenticationError; the SDK requires a non-None response."""
    req = httpx.Request("POST", "https://openrouter.ai/api/v1/chat")
    resp = httpx.Response(401, request=req)
    return AuthenticationError(message=message, response=resp, body=None)


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

    async def fake_astream_events(*a, **kw):
        # Yield no real events — endpoint should still emit model + done
        if False:
            yield {}
        return

    fake_graph = type("G", (), {"astream_events": fake_astream_events})()
    monkeypatch.setattr(app_mod, "_get_agent_for_model", lambda model_slug: fake_graph)

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


def test_chat_uses_requested_model_for_agent_build(monkeypatch):
    """Verify the user-selected model dropdown reaches build_agent."""
    captured_models: list[str] = []

    def fake_build(model_slug: str):
        captured_models.append(model_slug)
        # Return a fake graph that emits no events
        async def fake_astream_events(*a, **kw):
            if False:
                yield {}
        return type("G", (), {"astream_events": fake_astream_events})()

    monkeypatch.setattr(app_mod, "_get_agent_for_model", fake_build)

    client = app.test_client()
    res = client.post("/chat", json={
        "thread_id": "t1",
        "model": "anthropic/claude-opus-4.7",
        "text": "hi",
        "file_ids": [],
    })
    assert res.status_code == 200
    # Drain the streamed response so the runner thread runs to completion.
    _parse_sse(res.data)
    assert captured_models == ["anthropic/claude-opus-4.7"]


def test_chat_sse_model_event_reflects_requested_model(monkeypatch):

    def fake_build(model_slug: str):
        async def fake_astream_events(*a, **kw):
            if False:
                yield {}
        return type("G", (), {"astream_events": fake_astream_events})()

    monkeypatch.setattr(app_mod, "_get_agent_for_model", fake_build)
    client = app.test_client()
    res = client.post("/chat", json={
        "thread_id": "t1",
        "model": "anthropic/claude-opus-4.6",
        "text": "hi",
        "file_ids": [],
    })
    events = _parse_sse(res.data)
    assert events[0] == {"type": "model", "model": "anthropic/claude-opus-4.6"}


def test_chat_sanitizes_authentication_error(monkeypatch, caplog):
    """Auth errors emit a generic message; the real exception is logged."""

    def fake_build(model_slug: str):
        async def fake_astream_events(*a, **kw):
            # Simulate an auth failure mid-stream
            raise _fake_auth_error("Invalid API key sk-or-leak-1234567890")
            yield  # unreachable
        return type("G", (), {"astream_events": fake_astream_events})()

    monkeypatch.setattr(app_mod, "_get_agent_for_model", fake_build)

    client = app.test_client()
    with caplog.at_level(logging.ERROR, logger="app"):
        res = client.post("/chat", json={
            "thread_id": "t1", "model": "anthropic/claude-sonnet-4.6",
            "text": "hi", "file_ids": [],
        })

    events = _parse_sse(res.data)
    error_events = [e for e in events if e["type"] == "error"]
    assert len(error_events) == 1
    msg = error_events[0]["message"]
    # Sanitized message should NOT contain the API key fragment
    assert "sk-or-leak" not in msg
    assert "misconfigured" in msg.lower() or "auth" in msg.lower()
    # The original exception should appear in the server log
    assert any("sk-or-leak" in r.message or "sk-or-leak" in r.getMessage() for r in caplog.records)


def test_chat_sanitizes_generic_exception(monkeypatch, caplog):
    """Other exceptions emit a generic 'Agent error' without leaking exc text."""

    def fake_build(model_slug: str):
        async def fake_astream_events(*a, **kw):
            raise RuntimeError("Internal trace with /etc/passwd path leak")
            yield
        return type("G", (), {"astream_events": fake_astream_events})()

    monkeypatch.setattr(app_mod, "_get_agent_for_model", fake_build)

    client = app.test_client()
    with caplog.at_level(logging.ERROR, logger="app"):
        res = client.post("/chat", json={
            "thread_id": "t1", "model": "anthropic/claude-sonnet-4.6",
            "text": "hi", "file_ids": [],
        })

    events = _parse_sse(res.data)
    error_events = [e for e in events if e["type"] == "error"]
    assert len(error_events) == 1
    # Should not leak internal trace
    assert "/etc/passwd" not in error_events[0]["message"]
    # Server log MUST have the full exception
    assert any("/etc/passwd" in r.getMessage() for r in caplog.records)
