import json

from langchain_core.messages import AIMessageChunk

from sse import format_sse, EventTranslator


def test_format_sse_wraps_payload():
    line = format_sse({"type": "model", "model": "anthropic/claude-sonnet-4.6"})
    assert line.startswith("data: ")
    assert line.endswith("\n\n")
    payload = json.loads(line[len("data: "):].strip())
    assert payload["type"] == "model"


def test_translator_emits_tool_start_for_task_invocation_with_web_subagent():
    t = EventTranslator(current_model="anthropic/claude-sonnet-4.6")
    raw = {
        "event": "on_tool_start",
        "name": "task",
        "data": {"input": {"subagent_type": "valuation_reviewer", "description": "..."}},
    }
    out = t.translate(raw)
    assert out == {
        "type": "tool_start",
        "tool": "valuation_reviewer",
        "model": "anthropic/claude-sonnet-4.6:online",
    }


def test_translator_emits_tool_start_for_non_web_subagent_without_online_suffix():
    t = EventTranslator(current_model="anthropic/claude-sonnet-4.6")
    raw = {
        "event": "on_tool_start",
        "name": "task",
        "data": {"input": {"subagent_type": "gl_reconciler", "description": "..."}},
    }
    out = t.translate(raw)
    assert out["tool"] == "gl_reconciler"
    assert out["model"] == "anthropic/claude-sonnet-4.6"  # no :online


def test_translator_emits_tool_end_with_remembered_subagent():
    t = EventTranslator(current_model="anthropic/claude-sonnet-4.6")
    t.translate({
        "event": "on_tool_start",
        "name": "task",
        "data": {"input": {"subagent_type": "earnings_reviewer"}},
    })
    out = t.translate({"event": "on_tool_end", "name": "task", "data": {}})
    assert out == {"type": "tool_end", "tool": "earnings_reviewer"}


def test_translator_skips_non_task_tool_events():
    t = EventTranslator(current_model="x")
    out = t.translate({"event": "on_tool_start", "name": "write_file", "data": {}})
    assert out is None


def test_translator_streams_planner_tokens_as_text_delta():
    # The planner's chat-model node is named "model" in deepagents 0.5.7
    # (verified by inspecting `agent.get_graph().nodes`).
    t = EventTranslator(current_model="x")
    raw = {
        "event": "on_chat_model_stream",
        "data": {"chunk": AIMessageChunk(content="Hello")},
        "metadata": {"langgraph_node": "model"},
    }
    out = t.translate(raw)
    assert out == {"type": "text_delta", "delta": "Hello"}


def test_translator_skips_subagent_internal_tokens():
    # Sub-agent internal tokens come from the sub-agent's own graph nodes,
    # never from the planner's "model" node. Anything else must be skipped.
    t = EventTranslator(current_model="x")
    raw = {
        "event": "on_chat_model_stream",
        "data": {"chunk": AIMessageChunk(content="internal")},
        "metadata": {"langgraph_node": "task:gl_reconciler:agent"},
    }
    out = t.translate(raw)
    assert out is None


def test_translator_returns_none_for_unrelated_events():
    t = EventTranslator(current_model="x")
    assert t.translate({"event": "on_chain_start", "name": "irrelevant"}) is None


def test_translator_tool_end_without_prior_start_returns_none():
    t = EventTranslator(current_model="x")
    out = t.translate({"event": "on_tool_end", "name": "task", "data": {}})
    assert out is None


def test_translator_tool_start_missing_subagent_type_returns_none():
    t = EventTranslator(current_model="x")
    raw = {
        "event": "on_tool_start",
        "name": "task",
        "data": {"input": {"description": "..."}},
    }
    out = t.translate(raw)
    assert out is None


def test_translator_skips_planner_chunk_with_empty_content():
    t = EventTranslator(current_model="x")
    raw = {
        "event": "on_chat_model_stream",
        "data": {"chunk": AIMessageChunk(content="")},
        "metadata": {"langgraph_node": "model"},
    }
    out = t.translate(raw)
    assert out is None
