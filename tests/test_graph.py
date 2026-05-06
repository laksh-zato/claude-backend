"""Tests for `agent.graph.build_agent`.

API-introspection notes (deepagents 0.5.7):

- `create_deep_agent` returns a `CompiledStateGraph`. It does NOT expose each
  sub-agent as its own top-level tool. Instead, it exposes one `task` tool
  whose description enumerates the available sub-agents (`name` + `description`
  per entry). So we verify the contract "all 6 sub-agents are wired in" by
  checking the `task` tool description, plus the presence of the `task` tool
  itself in `tools_by_name`.
- The compiled graph exposes `.checkpointer` directly.
"""

from langgraph.checkpoint.memory import MemorySaver

from agent.graph import build_agent


EXPECTED_SUBAGENTS = {
    "gl_reconciler",
    "statement_auditor",
    "month_end_closer",
    "earnings_reviewer",
    "model_builder",
    "valuation_reviewer",
}


def _task_tool(agent):
    """Pull the `task` dispatcher tool out of the compiled agent."""
    tools_by_name = agent.nodes["tools"].bound.tools_by_name
    assert "task" in tools_by_name, (
        f"expected `task` tool to be exposed; got {list(tools_by_name)}"
    )
    return tools_by_name["task"]


def test_build_agent_has_six_subagents_registered():
    agent = build_agent()
    description = _task_tool(agent).description
    missing = {n for n in EXPECTED_SUBAGENTS if n not in description}
    assert not missing, (
        f"sub-agents missing from `task` tool description: {missing}\n"
        f"description was:\n{description}"
    )


def test_build_agent_uses_memory_saver_checkpointer():
    agent = build_agent()
    assert isinstance(agent.checkpointer, MemorySaver), (
        f"expected MemorySaver checkpointer, got {type(agent.checkpointer).__name__}"
    )
