from __future__ import annotations

import inspect
import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


ProgressFn = Callable[[float, str | None], None]
CancelFn = Callable[[], bool]
JobFn = Callable[..., dict[str, Any]]


class JobCanceledError(RuntimeError):
    pass


@dataclass
class JobRecord:
    job_id: str
    job_type: str
    status: str
    payload: dict[str, Any]
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    progress: float = 0.0
    message: str | None = None
    cancel_requested: bool = False
    result: dict[str, Any] | None = None
    error: str | None = None


class JobManager:
    def __init__(
        self,
        store_path: Path | None = None,
        max_jobs: int = 500,
        retention_days: float = 7.0,
    ) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._job_fns: dict[str, JobFn] = {}
        self._queue: list[str] = []
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = False

        self._store_path = store_path
        self._max_jobs = max(50, int(max_jobs))
        self._retention_seconds = max(0.0, float(retention_days)) * 86400.0

        if self._store_path is not None:
            self._store_path.parent.mkdir(parents=True, exist_ok=True)

        self._load()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    def submit(self, job_type: str, payload: dict[str, Any], fn: JobFn) -> str:
        job_id = str(uuid.uuid4())
        record = JobRecord(
            job_id=job_id,
            job_type=job_type,
            status="pending",
            payload=payload,
            created_at=_now_iso(),
            progress=0.0,
            message="queued",
        )

        with self._lock:
            self._jobs[job_id] = record
            self._job_fns[job_id] = fn
            self._queue.append(job_id)
            self._prune_locked()
            self._save_locked()

        self._wake.set()
        return job_id

    def cancel(self, job_id: str) -> tuple[bool, str]:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return False, "job_not_found"

            if record.status == "pending":
                record.status = "canceled"
                record.finished_at = _now_iso()
                record.message = "canceled_by_user"
                record.cancel_requested = True
                self._queue = [x for x in self._queue if x != job_id]
                self._job_fns.pop(job_id, None)
                self._save_locked()
                return True, "canceled"

            if record.status == "running":
                record.cancel_requested = True
                record.message = "cancel_requested"
                self._save_locked()
                return True, "cancel_requested"

            return False, f"cannot_cancel_{record.status}"

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._jobs.get(job_id)
            return None if record is None else asdict(record)

    def list(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._jobs.values())
        items.sort(key=lambda r: r.created_at, reverse=True)
        return [asdict(r) for r in items[: max(1, limit)]]

    def stats(self) -> dict[str, int]:
        out = {
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "canceled": 0,
            "cancel_requested": 0,
            "queue_depth": 0,
        }
        with self._lock:
            for row in self._jobs.values():
                if row.status in out:
                    out[row.status] += 1
                if row.cancel_requested:
                    out["cancel_requested"] += 1
            out["queue_depth"] = len(self._queue)

        out["total"] = (
            out["pending"]
            + out["running"]
            + out["completed"]
            + out["failed"]
            + out["canceled"]
        )
        return out

    def cleanup(self, retention_days: float | None = None) -> dict[str, Any]:
        with self._lock:
            retention = (
                self._retention_seconds
                if retention_days is None
                else max(0.0, float(retention_days)) * 86400.0
            )
            removed = self._cleanup_locked(retention_seconds=retention)
            self._save_locked()

        return {
            "ok": True,
            "removed": removed,
            "retention_days": round(retention / 86400.0, 3),
        }

    def wait(
        self,
        job_id: str,
        timeout_sec: float = 10.0,
        interval_sec: float = 0.05,
    ) -> dict[str, Any] | None:
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            row = self.get(job_id)
            if row is None:
                return None
            if row["status"] in {"completed", "failed", "canceled"}:
                return row
            time.sleep(interval_sec)
        return self.get(job_id)

    def close(self) -> None:
        self._stop = True
        self._wake.set()
        self._worker.join(timeout=1)

    def _worker_loop(self) -> None:
        while not self._stop:
            self._wake.wait(timeout=0.1)
            self._wake.clear()

            while True:
                with self._lock:
                    job_id = self._queue.pop(0) if self._queue else None
                    if job_id is None:
                        break

                    record = self._jobs.get(job_id)
                    if record is None or record.status != "pending":
                        continue

                    record.status = "running"
                    record.started_at = _now_iso()
                    record.progress = max(record.progress, 0.01)
                    record.message = "running"
                    self._save_locked()

                self._run_job(job_id)

    def _run_job(self, job_id: str) -> None:
        with self._lock:
            record = self._jobs.get(job_id)
            fn = self._job_fns.get(job_id)
            payload = {} if record is None else dict(record.payload)

        if record is None or fn is None:
            with self._lock:
                rec = self._jobs.get(job_id)
                if rec is not None:
                    rec.status = "failed"
                    rec.error = "missing_job_handler"
                    rec.message = "failed"
                    rec.finished_at = _now_iso()
                    self._save_locked()
            return

        def should_cancel() -> bool:
            with self._lock:
                rec = self._jobs.get(job_id)
                return bool(rec is not None and rec.cancel_requested)

        def progress_cb(progress: float, message: str | None = None) -> None:
            with self._lock:
                rec = self._jobs.get(job_id)
                if rec is None or rec.status != "running":
                    return
                rec.progress = max(0.0, min(1.0, float(progress)))
                if message is not None:
                    rec.message = message
                self._save_locked()

            if should_cancel():
                raise JobCanceledError("cancel_requested")

        try:
            if should_cancel():
                raise JobCanceledError("cancel_requested")

            result = _invoke_job_fn(fn, payload, progress_cb, should_cancel)

            with self._lock:
                rec = self._jobs[job_id]
                if rec.cancel_requested:
                    rec.status = "canceled"
                    rec.error = "cancel_requested"
                    rec.message = "canceled"
                else:
                    rec.status = "completed"
                    rec.result = result
                    rec.progress = 1.0
                    rec.message = "completed"
                rec.finished_at = _now_iso()
                self._job_fns.pop(job_id, None)
                self._save_locked()

        except JobCanceledError:
            with self._lock:
                rec = self._jobs[job_id]
                rec.status = "canceled"
                rec.error = "cancel_requested"
                rec.message = "canceled"
                rec.finished_at = _now_iso()
                self._job_fns.pop(job_id, None)
                self._save_locked()

        except Exception as exc:  # noqa: BLE001
            with self._lock:
                rec = self._jobs[job_id]
                rec.status = "failed"
                rec.error = str(exc)
                rec.message = "failed"
                rec.finished_at = _now_iso()
                self._job_fns.pop(job_id, None)
                self._save_locked()

    def _load(self) -> None:
        if self._store_path is None or not self._store_path.exists():
            return

        try:
            raw = json.loads(self._store_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return

        items = raw.get("jobs", []) if isinstance(raw, dict) else []
        changed = False
        for row in items:
            if not isinstance(row, dict):
                continue

            job_id = str(row.get("job_id", "")).strip()
            if not job_id:
                continue

            record = JobRecord(
                job_id=job_id,
                job_type=str(row.get("job_type", "unknown")),
                status=str(row.get("status", "failed")),
                payload=dict(row.get("payload", {})),
                created_at=str(row.get("created_at", _now_iso())),
                started_at=row.get("started_at"),
                finished_at=row.get("finished_at"),
                progress=float(row.get("progress", 0.0)),
                message=row.get("message"),
                cancel_requested=bool(row.get("cancel_requested", False)),
                result=row.get("result"),
                error=row.get("error"),
            )

            if record.status in {"pending", "running"}:
                record.status = "failed"
                record.error = "interrupted_restart"
                record.message = "failed"
                record.finished_at = _now_iso()
                changed = True

            self._jobs[job_id] = record

        if changed:
            self._save_locked()

    def _save_locked(self) -> None:
        if self._store_path is None:
            return

        self._cleanup_locked(retention_seconds=self._retention_seconds)
        payload = {
            "jobs": [
                asdict(r)
                for r in sorted(self._jobs.values(), key=lambda x: x.created_at)
            ]
        }
        self._store_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _cleanup_locked(self, retention_seconds: float) -> int:
        removed = 0
        now_ts = time.time()

        terminal_states = {"completed", "failed", "canceled"}
        if retention_seconds >= 0.0:
            cutoff = now_ts - retention_seconds
            for job_id, rec in list(self._jobs.items()):
                if rec.status not in terminal_states:
                    continue
                ts = _record_ts(rec)
                if ts <= cutoff:
                    self._jobs.pop(job_id, None)
                    self._job_fns.pop(job_id, None)
                    removed += 1

        if len(self._jobs) > self._max_jobs:
            terminal = [r for r in self._jobs.values() if r.status in terminal_states]
            terminal.sort(key=lambda r: r.created_at)
            while len(self._jobs) > self._max_jobs and terminal:
                victim = terminal.pop(0)
                self._jobs.pop(victim.job_id, None)
                self._job_fns.pop(victim.job_id, None)
                removed += 1

        return removed

    def _prune_locked(self) -> None:
        self._cleanup_locked(retention_seconds=self._retention_seconds)


def _invoke_job_fn(
    fn: JobFn,
    payload: dict[str, Any],
    progress_cb: ProgressFn,
    should_cancel: CancelFn,
) -> dict[str, Any]:
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return fn(payload)

    params = list(sig.parameters.values())
    positional = [
        p
        for p in params
        if p.kind
        in {
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        }
    ]

    if len(positional) >= 3:
        return fn(payload, progress_cb, should_cancel)
    if len(positional) >= 2:
        return fn(payload, progress_cb)
    return fn(payload)


def _record_ts(record: JobRecord) -> float:
    raw = record.finished_at or record.created_at
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return time.time()


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"
