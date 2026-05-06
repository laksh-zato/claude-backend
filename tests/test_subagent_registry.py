from agent.subagents.registry import SUBAGENTS, WEB_ENABLED_NAMES


def test_six_subagents_registered():
    assert len(SUBAGENTS) == 6
    names = {s["name"] for s in SUBAGENTS}
    assert names == {
        "gl_reconciler",
        "statement_auditor",
        "month_end_closer",
        "earnings_reviewer",
        "model_builder",
        "valuation_reviewer",
    }


def test_web_enabled_set():
    assert WEB_ENABLED_NAMES == {
        "earnings_reviewer",
        "model_builder",
        "valuation_reviewer",
    }


def test_each_subagent_has_nonempty_prompt():
    for spec in SUBAGENTS:
        assert len(spec["system_prompt"]) > 100, f"{spec['name']} prompt too short"
