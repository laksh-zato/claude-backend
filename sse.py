"""SSE event helpers and a translator from LangGraph `astream_events` to the
structured SSE payloads our frontend understands.

Frontend SSE event shapes:
    {"type": "model", "model": "..."}
    {"type": "tool_start", "tool": "<subagent name>", "model": "...:online"}
    {"type": "tool_end", "tool": "<subagent name>"}
    {"type": "text_delta", "delta": "..."}
    {"type": "done"}
    {"type": "error", "message": "..."}

Adaptation notes (deepagents 0.5.7):
- `deepagents` does NOT register each sub-agent as its own named tool. The
  planner invokes a single `task` tool with `subagent_type=<name>`. We map
  `task` tool starts/ends onto our `tool_start` / `tool_end` SSE events using
  the `subagent_type` from the start event's input.
- `on_tool_end` does not carry the `subagent_type` arg, so this translator is
  stateful (per request): we remember the most recent active subagent so the
  matching end event can be labelled correctly.
- The planner's chat-model node is named `model` in this graph (confirmed by
  inspecting `agent.get_graph().nodes`). Sub-agents run inside the `task` tool
  via `subagent.invoke(...)`, so their internal chat-model events surface
  under the sub-agent's own node tree, never the planner's `model` node.
"""

import json
from typing import Optional

from agent.subagents.registry import WEB_ENABLED_NAMES


def format_sse(payload: dict) -> str:
    """Wrap a payload as a single SSE `data: ...` frame."""
    return f"data: {json.dumps(payload)}\n\n"


# Planner chat-model node name(s). Verified empirically via
# `agent.get_graph().nodes` => ['__start__', 'model', 'tools',
# 'TodoListMiddleware.after_model', 'PatchToolCallsMiddleware.before_agent'].
PLANNER_NODES: set[str] = {"model"}


class EventTranslator:
    """Stateful translator mapping LangGraph events to SSE payloads.

    Stateful because `on_tool_end` events don't carry the `subagent_type` arg
    that was passed to the matching `on_tool_start`. We remember the most
    recent task-tool start so the matching end can be labelled.

    A new instance should be created per HTTP request (see Task 16).
    """

    def __init__(self, current_model: str):
        self.current_model = current_model
        self._active_subagent: Optional[str] = None

    def translate(self, raw: dict) -> Optional[dict]:
        event = raw.get("event")
        name = raw.get("name")

        if event == "on_tool_start" and name == "task":
            inp = (raw.get("data") or {}).get("input") or {}
            sub = inp.get("subagent_type")
            if not sub:
                return None
            self._active_subagent = sub
            model = (
                f"{self.current_model}:online"
                if sub in WEB_ENABLED_NAMES
                else self.current_model
            )
            return {"type": "tool_start", "tool": sub, "model": model}

        if event == "on_tool_end" and name == "task":
            sub = self._active_subagent
            self._active_subagent = None
            if not sub:
                return None
            return {"type": "tool_end", "tool": sub}

        if event == "on_chat_model_stream":
            node = (raw.get("metadata") or {}).get("langgraph_node")
            if node not in PLANNER_NODES:
                return None
            chunk = (raw.get("data") or {}).get("chunk")
            text = getattr(chunk, "content", "") or ""
            if not text:
                return None
            return {"type": "text_delta", "delta": text}

        return None
