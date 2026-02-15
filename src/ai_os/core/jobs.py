from __future__ import annotations

import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable


JobFn = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass
class JobRecord:
    job_id: str
    job_type: str
    status: str
    payload: dict[str, Any]
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = threading.Lock()

    def submit(self, job_type: str, payload: dict[str, Any], fn: JobFn) -> str:
        job_id = str(uuid.uuid4())
        record = JobRecord(
            job_id=job_id,
            job_type=job_type,
            status="pending",
            payload=payload,
            created_at=_now_iso(),
        )
        with self._lock:
            self._jobs[job_id] = record

        t = threading.Thread(target=self._run_job, args=(job_id, fn), daemon=True)
        t.start()
        return job_id

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._jobs.get(job_id)
            return None if record is None else asdict(record)

    def list(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._jobs.values())
        items.sort(key=lambda r: r.created_at, reverse=True)
        return [asdict(r) for r in items[: max(1, limit)]]

    def wait(
        self, job_id: str, timeout_sec: float = 10.0, interval_sec: float = 0.05
    ) -> dict[str, Any] | None:
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            row = self.get(job_id)
            if row is None:
                return None
            if row["status"] in {"completed", "failed"}:
                return row
            time.sleep(interval_sec)
        return self.get(job_id)

    def _run_job(self, job_id: str, fn: JobFn) -> None:
        with self._lock:
            record = self._jobs[job_id]
            record.status = "running"
            record.started_at = _now_iso()

        try:
            result = fn(record.payload)
            with self._lock:
                record = self._jobs[job_id]
                record.status = "completed"
                record.result = result
                record.finished_at = _now_iso()
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                record = self._jobs[job_id]
                record.status = "failed"
                record.error = str(exc)
                record.finished_at = _now_iso()


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"
