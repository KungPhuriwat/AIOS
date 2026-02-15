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
