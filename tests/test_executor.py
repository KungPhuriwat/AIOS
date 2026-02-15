from pathlib import Path

from src.ai_os.core.executor import SystemExecutor


def test_executor_runs_allowlisted_command() -> None:
    ex = SystemExecutor(
        mode="admin", root_dir=Path("."), enable_exec=True, platform="windows"
    )
    out = ex.execute("echo hello", approved_by_user=False)
    assert out.ok
    assert "hello" in out.output.lower()


def test_executor_blocks_non_allowlisted_without_approval() -> None:
    ex = SystemExecutor(
        mode="admin", root_dir=Path("."), enable_exec=True, platform="windows"
    )
    out = ex.execute("python -V", approved_by_user=False)
    assert not out.ok
    assert out.blocked


def test_executor_allows_non_allowlisted_with_approval() -> None:
    ex = SystemExecutor(
        mode="admin", root_dir=Path("."), enable_exec=False, platform="windows"
    )
    out = ex.execute("python -V", approved_by_user=True)
    assert out.ok
    assert out.output.startswith("dry-run")
