from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


GIT_BIN_CANDIDATES = [
    r"C:\Program Files\Git\cmd",
    r"C:\Program Files\Git\bin",
]


def _build_env() -> dict[str, str]:
    env = dict(os.environ)
    path_parts = env.get("PATH", "").split(os.pathsep) if env.get("PATH") else []
    for candidate in GIT_BIN_CANDIDATES:
        if Path(candidate).exists() and candidate not in path_parts:
            path_parts.insert(0, candidate)
    env["PATH"] = os.pathsep.join(path_parts)
    return env


def run_cmd(cmd: list[str], title: str) -> bool:
    print(f"\n[STEP] {title}")
    print("[CMD]", " ".join(cmd))
    result = subprocess.run(cmd, check=False, cwd=ROOT, env=_build_env())
    if result.returncode != 0:
        print(f"[FAIL] {title} (exit={result.returncode})")
        return False
    print(f"[PASS] {title}")
    return True


def runtime_checks() -> bool:
    from src.ai_os.core.orchestrator import AIOSOrchestrator
    from src.ai_os.core.permissions import PermissionGateway

    print("\n[STEP] Runtime checks (provider/notify/audit/security)")
    ok = True

    app = AIOSOrchestrator(ROOT / "data")
    provider = app.show_provider_status()
    notify = app.show_notify_status()
    audit = app.show_audit_status()
    probe = app.test_provider()

    print("provider:", provider)
    print("notify:", notify)
    print("audit:", audit)
    print("provider_test:", {k: probe[k] for k in ("ok", "latency_ms") if k in probe})

    if "provider" not in provider:
        print("[FAIL] provider status missing key")
        ok = False

    if not all(k in notify for k in ("discord", "line", "email")):
        print("[FAIL] notify status missing keys")
        ok = False

    if not audit.get("ok", False):
        print("[FAIL] audit chain is not healthy")
        ok = False

    if not isinstance(probe.get("ok"), bool):
        print("[FAIL] test_provider output invalid")
        ok = False

    gate_win = PermissionGateway(default_mode="admin", platform="windows")
    gate_unix = PermissionGateway(default_mode="admin", platform="unix")

    blocked_cases = [
        gate_unix.evaluate("ops", "rm -rf /", approved_by_user=False),
        gate_win.evaluate("ops", "del /f /q C:/important/*", approved_by_user=False),
        gate_win.evaluate("ops", "e r a s e C:/data", approved_by_user=False),
    ]

    if not all(not d.allowed for d in blocked_cases):
        print("[FAIL] security policy bypass detected")
        ok = False
    else:
        print("[PASS] security bypass checks blocked as expected")

    if ok:
        print("[PASS] Runtime checks")
    else:
        print("[FAIL] Runtime checks")

    return ok


def main() -> int:
    print("AI OS 10-minute checklist")
    all_ok = True

    all_ok &= run_cmd([sys.executable, "-m", "pytest", "-q"], "Run full pytest suite")
    all_ok &= run_cmd(
        [sys.executable, "-m", "pre_commit", "run", "--all-files"],
        "Run pre-commit security gates",
    )
    all_ok &= runtime_checks()

    print("\n=== SUMMARY ===")
    if all_ok:
        print("[PASS] All checklist items passed")
        return 0

    print("[FAIL] One or more checklist items failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
