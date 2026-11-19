"""Central LLM factory shared by Developer generation and QA planning."""
from functools import lru_cache

import os

from app.config import LLM_PROVIDER, GROQ_API_KEY, GROQ_MODEL, GOOGLE_API_KEY, GEMINI_MODEL


def _max_output_tokens() -> int:
    """Upper limit for one model reply (GROQ_MAX_TOKENS, default 32768, minimum 1024).

    Without an explicit limit a long multi-file answer was cut off mid-string by the provider, which
    surfaced as "json_validate_failed: Failed to generate JSON".
    """
    try:
        return max(1024, int(os.getenv("GROQ_MAX_TOKENS", "32768")))
    except ValueError:
        return 32768


@lru_cache(maxsize=4)
def _provider_model(provider: str, model: str, temperature: float):
    if provider == "groq":
        try:
            from langchain_groq import ChatGroq
        except ImportError as exc:
            raise RuntimeError("Groq is selected but langchain-groq is not installed. Install Developer_Agent requirements.") from exc
        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is required when LLM_PROVIDER=groq.")
        return ChatGroq(model=model, api_key=GROQ_API_KEY, temperature=temperature, max_tokens=_max_output_tokens())

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError as exc:
        raise RuntimeError("Gemini is selected but langchain-google-genai is not installed.") from exc
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is required when LLM_PROVIDER=gemini.")
    return ChatGoogleGenerativeAI(model=model, google_api_key=GOOGLE_API_KEY, temperature=temperature)


def get_llm(temperature: float = 0.2, *, provider: str | None = None, model: str | None = None):
    """Return the configured chat model. Pass provider/model to override per call."""
    selected = (provider or LLM_PROVIDER).strip().lower()
    if selected not in {"groq", "gemini"}:
        raise ValueError("provider must be 'groq' or 'gemini'")
    selected_model = model or (GROQ_MODEL if selected == "groq" else GEMINI_MODEL)
    return _provider_model(selected, selected_model, float(temperature))


def structured_output_method() -> str:
    """Use provider-native JSON Schema output for both supported providers.

    Groq's function-calling path sends generated source code as tool arguments. Large
    multi-file responses can fail while decoding those arguments. The configured
    GPT-OSS Groq models support JSON Schema structured output, which avoids that
    tool-argument serialization path and lets LangChain validate the Pydantic schema.
    """
    return "json_schema"
