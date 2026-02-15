import json
import time
from pathlib import Path

from src.ai_os.core.jobs import JobManager


def test_job_manager_submit_and_complete() -> None:
    jm = JobManager()

    def fn(payload: dict) -> dict:
        return {"ok": True, "value": payload["x"] + 1}

    job_id = jm.submit("unit", {"x": 1}, fn)
    row = jm.wait(job_id, timeout_sec=2)
    assert row is not None
    assert row["status"] == "completed"
    assert row["result"]["value"] == 2


def test_job_manager_fail() -> None:
    jm = JobManager()

    def bad(_payload: dict) -> dict:
        raise RuntimeError("boom")

    job_id = jm.submit("unit", {}, bad)
    row = jm.wait(job_id, timeout_sec=2)
    assert row is not None
    assert row["status"] == "failed"
    assert "boom" in row["error"]


def test_job_manager_cancel_pending() -> None:
    jm = JobManager()

    def slow(_payload: dict) -> dict:
        time.sleep(0.3)
        return {"ok": True}

    first = jm.submit("unit", {}, slow)
    second = jm.submit("unit", {}, slow)

    ok, reason = jm.cancel(second)
    assert ok
    assert reason == "canceled"

    _ = jm.wait(first, timeout_sec=2)
    second_row = jm.get(second)
    assert second_row is not None
    assert second_row["status"] == "canceled"


def test_job_manager_cancel_running_cooperative() -> None:
    jm = JobManager()

    def slow(_payload: dict, progress, should_cancel) -> dict:
        for idx in range(100):
            if should_cancel():
                return {"ok": False}
            progress(idx / 100, f"tick_{idx}")
            time.sleep(0.01)
        return {"ok": True}

    job_id = jm.submit("unit", {}, slow)
    deadline = time.time() + 2
    while time.time() < deadline:
        row = jm.get(job_id)
        if row is not None and row["status"] == "running":
            break
        time.sleep(0.01)

    ok, reason = jm.cancel(job_id)
    assert ok
    assert reason == "cancel_requested"

    row = jm.wait(job_id, timeout_sec=3)
    assert row is not None
    assert row["status"] == "canceled"


def test_job_manager_persistence(tmp_path: Path) -> None:
    path = tmp_path / "jobs.json"
    jm = JobManager(store_path=path)

    def fn(payload: dict) -> dict:
        return {"ok": True, "value": payload["x"] + 1}

    job_id = jm.submit("unit", {"x": 1}, fn)
    _ = jm.wait(job_id, timeout_sec=2)

    jm2 = JobManager(store_path=path)
    row = jm2.get(job_id)
    assert row is not None
    assert row["status"] == "completed"


def test_job_manager_marks_interrupted_on_reload(tmp_path: Path) -> None:
    path = tmp_path / "jobs.json"
    path.write_text(
        json.dumps(
            {
                "jobs": [
                    {
                        "job_id": "x",
                        "job_type": "train",
                        "status": "running",
                        "payload": {},
                        "created_at": "2026-01-01T00:00:00Z",
                        "progress": 0.4,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    jm = JobManager(store_path=path)
    row = jm.get("x")
    assert row is not None
    assert row["status"] == "failed"
    assert row["error"] == "interrupted_restart"


def test_job_manager_cleanup_retention_zero(tmp_path: Path) -> None:
    path = tmp_path / "jobs.json"
    jm = JobManager(store_path=path)

    def fn(_payload: dict) -> dict:
        return {"ok": True}

    job_id = jm.submit("unit", {}, fn)
    row = jm.wait(job_id, timeout_sec=2)
    assert row is not None
    assert row["status"] == "completed"

    out = jm.cleanup(retention_days=0)
    assert out["ok"] is True
    assert out["removed"] >= 1
    assert jm.get(job_id) is None
