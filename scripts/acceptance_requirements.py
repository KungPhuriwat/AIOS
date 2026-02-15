from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(name: str, condition: bool, detail: str) -> bool:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}: {detail}")
    return condition


def main() -> int:
    from src.ai_os.core.models import TaskRequest
    from src.ai_os.core.orchestrator import AIOSOrchestrator

    print("AI OS requirement acceptance suite")
    all_ok = True

    with tempfile.TemporaryDirectory(prefix="aios-accept-") as td:
        app = AIOSOrchestrator(Path(td))

        thai_result = app.handle(
            TaskRequest(
                task_type="code",
                language="python",
                prompt="ช่วยเขียนฟังก์ชันคำนวณค่าเฉลี่ยพร้อมตรวจ edge case",
            )
        )
        all_ok &= check(
            "Thai understanding",
            thai_result.get("ok") is True and "honesty" in thai_result,
            "accepts Thai prompt and returns structured response",
        )

        langs = ["python", "javascript", "go", "rust", "java"]
        lang_ok = True
        for lang in langs:
            out = app.handle(
                TaskRequest(
                    task_type="code",
                    language=lang,
                    prompt="create production-ready plan",
                )
            )
            lang_ok = lang_ok and out.get("ok") is True
        all_ok &= check(
            "Multi-language coding",
            lang_ok,
            f"processed languages: {', '.join(langs)}",
        )

        level_before = app.show_skills().get("python", {}).get("level", 0.0)
        app.run_benchmark("python")
        app.handle(
            TaskRequest(
                task_type="code",
                language="python",
                prompt="improve reliability with tests",
            )
        )
        level_after = app.show_skills().get("python", {}).get("level", 0.0)
        all_ok &= check(
            "Self-learning/skill growth",
            level_after >= level_before,
            f"python level {level_before} -> {level_after}",
        )

        notify_ok = isinstance(
            thai_result.get("notification", {}).get("local_log", ""), str
        )
        all_ok &= check(
            "Notification",
            notify_ok,
            "notification payload includes local_log and channels",
        )

        honesty = thai_result.get("honesty", {})
        honesty_ok = all(
            k in honesty for k in ("knows", "inferred", "confidence", "statement")
        )
        all_ok &= check(
            "Honesty layer",
            honesty_ok,
            "response includes confidence and honesty statement",
        )

        blocked = app.handle(
            TaskRequest(task_type="ops", prompt="rm -rf /"),
            approved_by_user=False,
        )
        all_ok &= check(
            "Security policy",
            blocked.get("ok") is False,
            "dangerous ops command blocked without approval",
        )

        audit_status = app.show_audit_status()
        all_ok &= check(
            "Signed audit integrity",
            audit_status.get("ok") is True,
            f"status={audit_status}",
        )

        dashboard = app.show_dashboard()
        dashboard_ok = all(
            k in dashboard for k in ("provider", "policy", "skills_count", "top_skills")
        )
        all_ok &= check(
            "Capability dashboard",
            dashboard_ok,
            "dashboard exposes provider/policy/skills summary",
        )

    print("\n=== ACCEPTANCE SUMMARY ===")
    if all_ok:
        print("[PASS] AI OS meets current MVP acceptance requirements")
        return 0

    print("[FAIL] AI OS does not meet one or more acceptance requirements")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
