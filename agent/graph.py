"""LangGraph deepagent assembly.

This wires the 6 finance sub-agents (from `agent.subagents.registry`) into a
single planner agent built via `deepagents.create_deep_agent`.

Notable adaptations from the original plan vs. the actual `deepagents` 0.5.7
public API:

- `create_deep_agent(...)` takes `system_prompt=` (not `instructions=`) and
  `model=` (not `default_model=`). Our wrapper still names its caller-facing
  parameter `default_model` per the plan.
- The `subagents=` sequence expects entries shaped like the `SubAgent`
  TypedDict, which uses the key `system_prompt` (not `prompt`). We translate
  our internal `SubagentSpec` accordingly.
- `create_deep_agent` already accepts a `checkpointer=` kwarg and returns a
  `CompiledStateGraph`, so no extra `.compile(...)` step is needed.
- `MemorySaver` is now an alias for `InMemorySaver` in current langgraph; we
  import it under the historical name for clarity and forward-compat.
"""

from langgraph.checkpoint.memory import MemorySaver
from deepagents import create_deep_agent, SubAgent

from .llm import make_llm
from .subagents.registry import SUBAGENTS


PLANNER_INSTRUCTIONS = """\
You are a senior finance analyst orchestrator. You have access to specialised \
sub-agents - each one is an expert in a specific finance task. When the user \
asks a question, decide which sub-agent(s) to invoke (you may chain them). \
Always cite which sub-agent produced which finding. If the question is purely \
conversational, answer directly without invoking sub-agents.

Available sub-agents:
{subagent_list}

User-attached files appear in their message as text tables (CSV/XLSX) or as \
file/image content blocks (PDF/PNG/JPG). Reference them by filename when \
discussing findings."""


def _format_subagent_list() -> str:
    return "\n".join(f"- {s['name']}: {s['description']}" for s in SUBAGENTS)


def _build_subagent_specs(model_slug: str) -> list[SubAgent]:
    """Translate our `SubagentSpec` registry into deepagents `SubAgent` dicts.

    Each sub-agent gets its own `ChatOpenAI` (via `make_llm`) so that web-enabled
    skills (`earnings_reviewer`, `model_builder`, `valuation_reviewer`) hit
    OpenRouter with the `:online` plugin while non-web skills don't.
    """
    out: list[SubAgent] = []
    for spec in SUBAGENTS:
        out.append(
            SubAgent(
                name=spec["name"],
                description=spec["description"],
                system_prompt=spec["system_prompt"],
                model=make_llm(model_slug, web=spec["web"]),
            )
        )
    return out


def build_agent(default_model: str = "anthropic/claude-sonnet-4.6"):
    """Build the deepagent graph.

    Args:
        default_model: OpenRouter model slug for the planner and any non-web
            sub-agent. Web-enabled sub-agents get the same slug suffixed with
            `:online` (handled inside `make_llm`).

    Returns:
        A `CompiledStateGraph` ready to be `astream_events`'d. Threads are
        remembered across turns via an in-memory checkpointer.
    """
    instructions = PLANNER_INSTRUCTIONS.format(subagent_list=_format_subagent_list())
    return create_deep_agent(
        model=make_llm(default_model, web=False),
        tools=[],
        system_prompt=instructions,
        subagents=_build_subagent_specs(default_model),
        checkpointer=MemorySaver(),
    )
