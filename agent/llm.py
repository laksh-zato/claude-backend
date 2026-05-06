import os
from langchain_openai import ChatOpenAI


OPENROUTER_BASE = "https://openrouter.ai/api/v1"


def make_llm(model_slug: str, web: bool = False, temperature: float = 0.2) -> ChatOpenAI:
    """Build a ChatOpenAI pointed at OpenRouter.

    Args:
        model_slug: e.g. "anthropic/claude-sonnet-4.6"
        web: if True, append ":online" to enable OpenRouter web plugin
        temperature: sampling temperature
    """
    slug = f"{model_slug}:online" if web else model_slug
    return ChatOpenAI(
        model=slug,
        openai_api_key=os.environ["OPENROUTER_API_KEY"],
        openai_api_base=OPENROUTER_BASE,
        default_headers={
            "HTTP-Referer": os.environ["OPENROUTER_HTTP_REFERER"],
            "X-Title": os.environ["OPENROUTER_X_TITLE"],
        },
        temperature=temperature,
        streaming=True,
    )
