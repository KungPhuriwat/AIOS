from pathlib import Path

from src.ai_os.core.orchestrator import AIOSOrchestrator
from src.ai_os.main import run_single_command


def test_run_single_command_show_policy(tmp_path: Path) -> None:
    app = AIOSOrchestrator(tmp_path)
    out = run_single_command(app, "show policy", interactive_ops_confirm=False)
    assert "ops_mode" in out


def test_run_single_command_benchmark(tmp_path: Path) -> None:
    app = AIOSOrchestrator(tmp_path)
    out = run_single_command(app, "benchmark python", interactive_ops_confirm=False)
    assert out["ok"]
    assert out["language"] == "python"


def test_run_single_command_ops_auto_approved(tmp_path: Path) -> None:
    app = AIOSOrchestrator(tmp_path)
    out = run_single_command(
        app,
        "ops: echo hello",
        auto_approve_ops=True,
        interactive_ops_confirm=False,
    )
    assert isinstance(out["ok"], bool)


def test_run_single_command_train(tmp_path: Path) -> None:
    app = AIOSOrchestrator(tmp_path)
    out = run_single_command(app, "train python 2", interactive_ops_confirm=False)
    assert out["ok"]
    assert out["rounds"] == 2
