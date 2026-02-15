from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from time import perf_counter

from ..agents.coding_agent import CodingAgent
from .audit import SignedAuditLogger
from .honesty import HonestyLayer
from .learner import LearningOutcome, SelfLearner
from .models import TaskRequest, TaskResult
from .notifier import Notifier
from .permissions import PermissionGateway
from .skill_registry import SkillRegistry


class AIOSOrchestrator:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.registry = SkillRegistry(data_dir / "skills.json")
        self.notifier = Notifier(data_dir / "notifications.log")
        self.gateway = PermissionGateway(default_mode="read")
        self.learner = SelfLearner()
        self.honesty = HonestyLayer()
        self.coding_agent = CodingAgent()
        self.audit_path = data_dir / "audit.log"
        self.audit = SignedAuditLogger(self.audit_path)

        migration = self.audit.migrate_legacy()
        if migration.get("migrated"):
            self._audit("audit_migrated", migration)

    def _audit(self, event_type: str, detail: dict) -> None:
        self.audit.append(event_type=event_type, detail=detail)

    def handle(self, request: TaskRequest, approved_by_user: bool = False) -> dict:
        decision = self.gateway.evaluate(
            request.task_type, request.prompt, approved_by_user
        )
        if not decision.allowed:
            self._audit(
                "permission_blocked",
                {"request": asdict(request), "reason": decision.reason},
            )
            return {"ok": False, "reason": decision.reason}

        if request.task_type == "code":
            result = self.coding_agent.run(request.prompt, request.language)
            payload = self._post_process_skill(result, request.language or "python")
            self._audit("code_task", {"request": asdict(request), "result": payload})
            return payload

        result = TaskResult(
            ok=True, output="งานระบบถูกอนุมัติ (MVP ยังไม่รันคำสั่งจริง)", confidence=0.8
        )
        honesty = self.honesty.as_dict(result)
        self._audit("ops_task", {"request": asdict(request), "honesty": honesty})
        return {"ok": True, "output": result.output, "honesty": honesty}

    def _post_process_skill(self, result: TaskResult, language: str) -> dict:
        current = self.registry.get_all().get(language, {}).get("level", 5.0)
        outcome = LearningOutcome(
            skill_name=language,
            success_rate=0.9 if result.ok else 0.4,
            test_pass_rate=0.88,
            bug_rate=0.08 if result.ok else 0.3,
        )
        score = self.learner.score(outcome)
        new_level = self.learner.next_level(current, score)
        updated = self.registry.upsert(language, new_level, score)

        summary = self._build_skill_summary(
            language, current, updated["level"], score, result.ok
        )
        fanout = self.notifier.notify(summary)
        honesty = self.honesty.as_dict(result)

        return {
            "ok": result.ok,
            "output": result.output,
            "confidence": result.confidence,
            "honesty": honesty,
            "skill": updated,
            "notification": {
                "summary": summary,
                "local_log": fanout.local_log,
                "sent_channels": fanout.sent,
                "failed_channels": fanout.failed,
            },
        }

    def _build_skill_summary(
        self,
        language: str,
        old_level: float,
        new_level: float,
        score: float,
        task_ok: bool,
    ) -> str:
        direction = "UP" if new_level >= old_level else "DOWN"
        return (
            f"skill_update[{direction}] lang={language} old={round(old_level, 2)} "
            f"new={round(new_level, 2)} score={round(score, 2)} task_ok={task_ok}"
        )

    def show_skills(self) -> dict[str, dict]:
        return self.registry.get_all()

    def show_audit(self, limit: int = 20) -> list[str]:
        if not self.audit_path.exists():
            return []
        lines = self.audit_path.read_text(encoding="utf-8").splitlines()
        return lines[-limit:]

    def show_provider_status(self) -> dict[str, str]:
        return self.coding_agent.provider_status()

    def show_notify_status(self) -> dict[str, bool]:
        return self.notifier.status()

    def show_audit_status(self) -> dict:
        return self.audit.verify_chain()

    def test_provider(self) -> dict:
        started = perf_counter()
        try:
            result = self.coding_agent.run(
                prompt="health check: return one short coding readiness line",
                language="python",
            )
            latency_ms = round((perf_counter() - started) * 1000, 2)
            payload = {
                "ok": result.ok,
                "provider": self.show_provider_status(),
                "latency_ms": latency_ms,
                "confidence": result.confidence,
                "evidence": result.evidence,
                "inferred": result.inferred,
                "response_preview": result.output[:240],
            }
            self._audit("provider_test", payload)
            return payload
        except Exception as exc:  # noqa: BLE001
            latency_ms = round((perf_counter() - started) * 1000, 2)
            payload = {
                "ok": False,
                "provider": self.show_provider_status(),
                "latency_ms": latency_ms,
                "error": str(exc),
            }
            self._audit("provider_test_error", payload)
            return payload
