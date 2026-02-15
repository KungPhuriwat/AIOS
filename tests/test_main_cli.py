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


def test_run_single_command_queue_and_show_job(tmp_path: Path) -> None:
    app = AIOSOrchestrator(tmp_path)
    submitted = run_single_command(
        app, "queue train python 2", interactive_ops_confirm=False
    )
    assert submitted["ok"]
    app.jobs.wait(submitted["job_id"], timeout_sec=3)
    row = run_single_command(
        app, f"show job {submitted['job_id']}", interactive_ops_confirm=False
    )
    assert row["ok"]


def test_run_single_command_show_jobs_stats(tmp_path: Path) -> None:
    app = AIOSOrchestrator(tmp_path)
    out = run_single_command(app, "show jobs stats", interactive_ops_confirm=False)
    assert out["ok"]
    assert "total" in out["stats"]


def test_run_single_command_cancel_job(tmp_path: Path) -> None:
    app = AIOSOrchestrator(tmp_path)
    submitted = run_single_command(
        app,
        "queue train python 8",
        interactive_ops_confirm=False,
    )
    out = run_single_command(
        app,
        f"cancel job {submitted['job_id']}",
        interactive_ops_confirm=False,
    )
    assert out["ok"] in {True, False}


def test_run_single_command_cleanup_jobs(tmp_path: Path) -> None:
    app = AIOSOrchestrator(tmp_path)
    out = run_single_command(app, "cleanup jobs 0", interactive_ops_confirm=False)
    assert out["ok"]
    assert "removed" in out


def test_run_single_command_cleanup_jobs_invalid_retention(tmp_path: Path) -> None:
    app = AIOSOrchestrator(tmp_path)
    out = run_single_command(
        app,
        "cleanup jobs invalid",
        interactive_ops_confirm=False,
    )
    assert out["ok"] is False
    assert out["error"] == "invalid_retention_days"


def test_run_single_command_retry_job(tmp_path: Path) -> None:
    app = AIOSOrchestrator(tmp_path)
    submitted = run_single_command(
        app,
        "queue benchmark python",
        interactive_ops_confirm=False,
    )
    _ = app.jobs.wait(submitted["job_id"], timeout_sec=3)
    out = run_single_command(
        app,
        f"retry job {submitted['job_id']}",
        interactive_ops_confirm=False,
    )
    assert out["ok"] is True
    assert out["new_job_id"] != submitted["job_id"]
