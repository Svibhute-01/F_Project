import sys
import types

import pytest

import app.llm as llm_module


def _fake_module(name, class_name, cls):
    module = types.ModuleType(name)
    setattr(module, class_name, cls)
    return module


def test_groq_is_the_default_provider(monkeypatch):
    monkeypatch.setattr(llm_module, "LLM_PROVIDER", "groq")
    monkeypatch.setattr(llm_module, "GROQ_API_KEY", "test-key")

    class FakeGroq:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setitem(sys.modules, "langchain_groq", _fake_module("langchain_groq", "ChatGroq", FakeGroq))
    model = llm_module.get_llm(temperature=0.15, model="test-groq-model")
    assert model.kwargs["model"] == "test-groq-model"
    assert model.kwargs["api_key"] == "test-key"
    assert model.kwargs["temperature"] == 0.15


def test_provider_can_be_overridden(monkeypatch):
    monkeypatch.setattr(llm_module, "GOOGLE_API_KEY", "google")

    class FakeGemini:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setitem(sys.modules, "langchain_google_genai", _fake_module("langchain_google_genai", "ChatGoogleGenerativeAI", FakeGemini))
    model = llm_module.get_llm(provider="gemini", model="gemini-test")
    assert model.kwargs["model"] == "gemini-test"
    assert model.kwargs["google_api_key"] == "google"


def test_unknown_provider_is_rejected():
    with pytest.raises(ValueError, match="provider must"):
        llm_module.get_llm(provider="unknown")


def test_structured_output_method_is_provider_aware(monkeypatch):
    monkeypatch.setattr(llm_module, "LLM_PROVIDER", "groq")
    assert llm_module.structured_output_method() == "json_schema"
    monkeypatch.setattr(llm_module, "LLM_PROVIDER", "gemini")
    assert llm_module.structured_output_method() == "json_schema"
