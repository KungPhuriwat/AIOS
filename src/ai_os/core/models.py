from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TaskRequest:
    task_type: str
    prompt: str
    language: str | None = None


@dataclass
class TaskResult:
    ok: bool
    output: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    inferred: bool = False


@dataclass
class SkillLevel:
    name: str
    level: float
    last_updated: str
    benchmark_score: float

    @staticmethod
    def now_iso() -> str:
        return datetime.utcnow().isoformat(timespec="seconds") + "Z"


@dataclass
class AuditEvent:
    ts: str
    event_type: str
    detail: dict[str, Any]
