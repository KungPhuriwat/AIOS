from pathlib import Path

from src.ai_os.core.notifier import Notifier


def test_notifier_logs_locally_without_channels(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("AIOS_DISCORD_WEBHOOK", raising=False)
    monkeypatch.delenv("AIOS_LINE_CHANNEL_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("AIOS_LINE_TO", raising=False)
    monkeypatch.delenv("AIOS_EMAIL_SMTP_HOST", raising=False)
    monkeypatch.delenv("AIOS_EMAIL_USERNAME", raising=False)
    monkeypatch.delenv("AIOS_EMAIL_PASSWORD", raising=False)
    monkeypatch.delenv("AIOS_EMAIL_TO", raising=False)

    notifier = Notifier(tmp_path / "notifications.log")
    result = notifier.notify("skill updated")
    assert "skill updated" in result.local_log
    assert result.sent == []


def test_notifier_records_channel_failure(tmp_path: Path) -> None:
    notifier = Notifier(tmp_path / "notifications.log")

    def fail(_message: str) -> bool:
        raise RuntimeError("boom")

    notifier._send_discord = fail  # type: ignore[method-assign]
    result = notifier.notify("msg")
    assert result.failed


def test_notifier_status_from_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AIOS_DISCORD_WEBHOOK", "https://x")
    monkeypatch.setenv("AIOS_LINE_CHANNEL_ACCESS_TOKEN", "tok")
    monkeypatch.setenv("AIOS_LINE_TO", "uid")
    monkeypatch.setenv("AIOS_EMAIL_SMTP_HOST", "smtp")
    monkeypatch.setenv("AIOS_EMAIL_USERNAME", "u")
    monkeypatch.setenv("AIOS_EMAIL_PASSWORD", "p")
    monkeypatch.setenv("AIOS_EMAIL_TO", "t")
    notifier = Notifier(tmp_path / "notifications.log")
    status = notifier.status()
    assert status["discord"]
    assert status["line"]
    assert status["email"]
