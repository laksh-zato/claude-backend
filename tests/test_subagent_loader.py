from agent.subagents.loader import load_skill_prompt, build_subagent_spec


def test_load_skill_prompt_strips_yaml_frontmatter():
    prompt = load_skill_prompt("gl-reconciler")
    assert "---" not in prompt[:10]  # frontmatter gone
    assert len(prompt) > 100  # body retained


def test_build_subagent_spec_has_required_fields():
    spec = build_subagent_spec(
        name="gl_reconciler",
        skill_dir="gl-reconciler",
        web=False,
        description="Reconciles general ledger to source documents.",
    )
    assert spec["name"] == "gl_reconciler"
    assert spec["description"] == "Reconciles general ledger to source documents."
    assert "system_prompt" in spec
    assert spec["web"] is False


def test_build_subagent_spec_marks_web_enabled():
    spec = build_subagent_spec(
        name="earnings_reviewer",
        skill_dir="earnings-reviewer",
        web=True,
        description="...",
    )
    assert spec["web"] is True
