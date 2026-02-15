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


def test_orchestrator_ops_exec_with_approval(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AIOS_OPS_MODE", "admin")
    monkeypatch.setenv("AIOS_ENABLE_OPS_EXEC", "1")
    app = AIOSOrchestrator(tmp_path)
    out = app.handle(
        TaskRequest(task_type="ops", prompt="echo ok"), approved_by_user=True
    )
    assert out["ok"]


def test_orchestrator_benchmark_and_dashboard(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AIOS_LLM_PROVIDER", "fallback")
    app = AIOSOrchestrator(tmp_path)
    bench = app.run_benchmark("python")
    dashboard = app.show_dashboard()
    assert bench["ok"]
    assert "benchmark" in bench
    assert "top_skills" in dashboard


def test_orchestrator_training_cycle(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AIOS_LLM_PROVIDER", "fallback")
    app = AIOSOrchestrator(tmp_path)
    out = app.run_training_cycle("python", rounds=2)
    assert out["ok"]
    assert out["rounds"] == 2
    assert len(out["history"]) == 2
