from pathlib import Path

from src.ai_os.core.models import TaskRequest
from src.ai_os.core.orchestrator import AIOSOrchestrator


def test_orchestrator_returns_notification_structure(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.delenv("AIOS_LLM_PROVIDER", raising=False)
    app = AIOSOrchestrator(tmp_path)
    payload = app.handle(
        TaskRequest(task_type="code", prompt="เขียนฟังก์ชันรวมเลข", language="python")
    )
    assert payload["ok"]
    assert "notification" in payload
    assert "summary" in payload["notification"]
    assert "sent_channels" in payload["notification"]


def test_orchestrator_health_checks(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AIOS_LLM_PROVIDER", "fallback")
    app = AIOSOrchestrator(tmp_path)
    provider = app.show_provider_status()
    notify = app.show_notify_status()
    audit = app.show_audit_status()
    assert provider["provider"] == "fallback"
    assert isinstance(notify["discord"], bool)
    assert audit["ok"]


def test_orchestrator_test_provider(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AIOS_LLM_PROVIDER", "fallback")
    app = AIOSOrchestrator(tmp_path)
    out = app.test_provider()
    assert isinstance(out["latency_ms"], float)
    assert "provider" in out
    assert "response_preview" in out
