from src.ai_os.agents.coding_agent import CodingAgent


def test_coding_agent_fallback_for_unknown_language(monkeypatch) -> None:
    monkeypatch.delenv("AIOS_LLM_PROVIDER", raising=False)
    agent = CodingAgent()
    result = agent.run("build parser", "elixir")
    assert result.ok
    assert result.inferred
    assert "fallback-policy" in result.evidence


def test_coding_agent_openai_without_key_falls_back(monkeypatch) -> None:
    monkeypatch.setenv("AIOS_LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    agent = CodingAgent()
    result = agent.run("hello", "python")
    assert result.ok
    assert "fallback-policy" in result.evidence


def test_coding_agent_opencode_selected_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("AIOS_LLM_PROVIDER", "opencode")
    monkeypatch.setenv("OPENCODE_API_KEY", "test-key")
    monkeypatch.setenv("OPENCODE_MODEL", "opencode/coder")
    agent = CodingAgent()
    status = agent.provider_status()
    assert status["provider"] == "opencode"
    assert status["model"] == "opencode/coder"
