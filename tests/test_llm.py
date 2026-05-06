from agent.llm import make_llm


def test_make_llm_uses_openrouter_base_url():
    llm = make_llm("anthropic/claude-sonnet-4.6")
    assert llm.openai_api_base == "https://openrouter.ai/api/v1"
    assert llm.model_name == "anthropic/claude-sonnet-4.6"


def test_make_llm_appends_online_for_web():
    llm = make_llm("anthropic/claude-sonnet-4.6", web=True)
    assert llm.model_name == "anthropic/claude-sonnet-4.6:online"


def test_make_llm_sets_required_headers():
    llm = make_llm("anthropic/claude-sonnet-4.6")
    headers = llm.default_headers
    assert headers["HTTP-Referer"] == "https://test.example.com"
    assert headers["X-Title"] == "Finance Chatbot Test"
