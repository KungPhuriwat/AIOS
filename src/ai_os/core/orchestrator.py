from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

from ..agents.coding_agent import CodingAgent
from .audit import SignedAuditLogger
from .benchmark import CodingBenchmarkEngine
from .executor import SystemExecutor
from .honesty import HonestyLayer
from .jobs import JobManager
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

        ops_mode = os.getenv("AIOS_OPS_MODE", "read").strip().lower()
        enable_exec = os.getenv("AIOS_ENABLE_OPS_EXEC", "1").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.gateway = PermissionGateway(default_mode=ops_mode)
        self.executor = SystemExecutor(
            mode=ops_mode, root_dir=Path.cwd(), enable_exec=enable_exec
        )

        self.learner = SelfLearner()
        self.honesty = HonestyLayer()
        self.benchmark = CodingBenchmarkEngine()
        self.coding_agent = CodingAgent()
        self.jobs = JobManager()

        self.audit_path = data_dir / "audit.log"
        self.audit = SignedAuditLogger(self.audit_path)

        migration = self.audit.migrate_legacy()
        if migration.get("migrated"):
            self._audit("audit_migrated", migration)
        repaired = self.audit.repair_invalid_chain()
        if repaired.get("repaired"):
            self._audit("audit_repaired", repaired)

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
            payload = self._post_process_skill(
                result, request.language or "python", request.prompt
            )
            self._audit("code_task", {"request": asdict(request), "result": payload})
            return payload

        exec_result = self.executor.execute(
            request.prompt, approved_by_user=approved_by_user
        )
        result = TaskResult(
            ok=exec_result.ok,
            output=exec_result.output,
            confidence=0.88 if exec_result.ok else 0.35,
            evidence=["system-executor", f"returncode={exec_result.returncode}"],
            inferred=False,
        )
        honesty = self.honesty.as_dict(result)
        payload = {
            "ok": result.ok,
            "output": result.output,
            "returncode": exec_result.returncode,
            "blocked": exec_result.blocked,
            "reason": exec_result.reason,
            "honesty": honesty,
        }
        self._audit("ops_task", {"request": asdict(request), "result": payload})
        return payload

    def _post_process_skill(
        self, result: TaskResult, language: str, prompt: str
    ) -> dict:
        current = self.registry.get_all().get(language, {}).get("level", 5.0)
        outcome: LearningOutcome = self.benchmark.evaluate_task(
            language=language, prompt=prompt, result=result
        )
        score = self.learner.score(outcome)
        new_level = self.learner.next_level(current, score)
        updated = self.registry.upsert(language, new_level, score)

        summary = self._build_skill_summary(
            language,
            current,
            updated["level"],
            score,
            result.ok,
        )
        fanout = self.notifier.notify(summary)
        honesty = self.honesty.as_dict(result)

        return {
            "ok": result.ok,
            "output": result.output,
            "confidence": result.confidence,
            "honesty": honesty,
            "skill": updated,
            "benchmark": {
                "success_rate": round(outcome.success_rate, 2),
                "test_pass_rate": round(outcome.test_pass_rate, 2),
                "bug_rate": round(outcome.bug_rate, 2),
                "score": round(score, 2),
            },
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

    def run_benchmark(self, language: str) -> dict:
        summary = self.benchmark.run_language_benchmark(self.coding_agent, language)
        current = self.registry.get_all().get(language, {}).get("level", 5.0)
        outcome = LearningOutcome(
            skill_name=language,
            success_rate=summary.avg_success_rate,
            test_pass_rate=summary.avg_test_pass_rate,
            bug_rate=summary.avg_bug_rate,
        )
        score = self.learner.score(outcome)
        new_level = self.learner.next_level(current, score)
        updated = self.registry.upsert(language, new_level, score)

        msg = (
            f"benchmark_update lang={language} old={round(current, 2)} "
            f"new={updated['level']} score={round(score, 2)} confidence={round(summary.avg_confidence, 2)}"
        )
        fanout = self.notifier.notify(msg)
        payload = {
            "ok": True,
            "language": language,
            "benchmark": {
                "avg_success_rate": round(summary.avg_success_rate, 2),
                "avg_test_pass_rate": round(summary.avg_test_pass_rate, 2),
                "avg_bug_rate": round(summary.avg_bug_rate, 2),
                "avg_confidence": round(summary.avg_confidence, 2),
                "score": round(score, 2),
            },
            "skill": updated,
            "notification": {
                "summary": msg,
                "local_log": fanout.local_log,
                "sent_channels": fanout.sent,
                "failed_channels": fanout.failed,
            },
        }
        self._audit("benchmark_task", payload)
        return payload

    def run_training_cycle(self, language: str, rounds: int = 3) -> dict:
        total_rounds = max(1, min(20, int(rounds)))
        before = self.registry.get_all().get(language, {}).get("level", 5.0)
        rounds_out: list[dict] = []
        for idx in range(total_rounds):
            bench = self.run_benchmark(language)
            rounds_out.append(
                {
                    "round": idx + 1,
                    "score": bench["benchmark"]["score"],
                    "level": bench["skill"]["level"],
                    "avg_confidence": bench["benchmark"]["avg_confidence"],
                }
            )

        after = self.registry.get_all().get(language, {}).get("level", before)
        payload = {
            "ok": True,
            "language": language,
            "rounds": total_rounds,
            "level_before": before,
            "level_after": after,
            "delta": round(after - before, 2),
            "history": rounds_out,
        }
        self._audit("training_cycle", payload)
        return payload

    def submit_training_job(self, language: str, rounds: int = 3) -> dict:
        payload = {"language": language, "rounds": rounds}
        job_id = self.jobs.submit(
            job_type="train",
            payload=payload,
            fn=lambda p: self.run_training_cycle(
                str(p.get("language", "python")), int(p.get("rounds", 3))
            ),
        )
        out = {"ok": True, "job_id": job_id, "job_type": "train", "payload": payload}
        self._audit("job_submitted", out)
        return out

    def submit_benchmark_job(self, language: str) -> dict:
        payload = {"language": language}
        job_id = self.jobs.submit(
            job_type="benchmark",
            payload=payload,
            fn=lambda p: self.run_benchmark(str(p.get("language", "python"))),
        )
        out = {
            "ok": True,
            "job_id": job_id,
            "job_type": "benchmark",
            "payload": payload,
        }
        self._audit("job_submitted", out)
        return out

    def get_job(self, job_id: str) -> dict:
        row = self.jobs.get(job_id)
        if row is None:
            return {"ok": False, "error": "job_not_found", "job_id": job_id}
        return {"ok": True, "job": row}

    def list_jobs(self, limit: int = 20) -> dict:
        return {"ok": True, "jobs": self.jobs.list(limit=limit)}

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

    def show_policy_status(self) -> dict[str, str | bool]:
        return {
            "ops_mode": self.gateway.default_mode,
            "platform": self.gateway.platform,
            "ops_exec_enabled": self.executor.enable_exec,
        }

    def show_dashboard(self) -> dict:
        skills = self.registry.get_all()
        top_skills = sorted(
            [{"language": k, **v} for k, v in skills.items()],
            key=lambda x: x.get("level", 0.0),
            reverse=True,
        )[:3]
        return {
            "provider": self.show_provider_status(),
            "notify": self.show_notify_status(),
            "audit": self.show_audit_status(),
            "policy": self.show_policy_status(),
            "skills_count": len(skills),
            "top_skills": top_skills,
            "latest_changes": self.registry.latest_changes(limit=5),
            "jobs": self.jobs.list(limit=5),
        }

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
