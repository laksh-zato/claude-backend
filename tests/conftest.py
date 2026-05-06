import os
import pytest


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("OPENROUTER_HTTP_REFERER", "https://test.example.com")
    monkeypatch.setenv("OPENROUTER_X_TITLE", "Finance Chatbot Test")
