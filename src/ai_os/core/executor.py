from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .permissions import UNIX_ALLOW_COMMANDS, WIN_ALLOW_COMMANDS


@dataclass
class ExecutionResult:
    ok: bool
    output: str
    returncode: int
    blocked: bool = False
    reason: str = ""


class SystemExecutor:
    def __init__(
        self,
        mode: str = "read",
        root_dir: Path | None = None,
        enable_exec: bool = True,
        timeout_sec: int = 20,
        platform: str | None = None,
    ) -> None:
        self.mode = mode
        self.root_dir = root_dir or Path.cwd()
        self.enable_exec = enable_exec
        self.timeout_sec = timeout_sec
        self.platform = (platform or ("windows" if os.name == "nt" else "unix")).lower()

    def execute(self, prompt: str, approved_by_user: bool = False) -> ExecutionResult:
        command = prompt.strip()
        if not command:
            return ExecutionResult(
                ok=False,
                output="empty command",
                returncode=2,
                blocked=True,
                reason="empty",
            )

        first = command.split()[0].strip("'\"`").lower()
        allowlist = (
            WIN_ALLOW_COMMANDS if self.platform == "windows" else UNIX_ALLOW_COMMANDS
        )

        if self.mode == "read" and not approved_by_user:
            return ExecutionResult(
                ok=False,
                output="ops mode is read-only",
                returncode=3,
                blocked=True,
                reason="read_only",
            )

        if not approved_by_user and first not in allowlist:
            return ExecutionResult(
                ok=False,
                output=f"command '{first}' is not in allowlist",
                returncode=4,
                blocked=True,
                reason="not_allowlisted",
            )

        if not self.enable_exec:
            return ExecutionResult(
                ok=True,
                output=f"dry-run: {command}",
                returncode=0,
            )

        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(ok=False, output="command timeout", returncode=124)
        except OSError as exc:
            return ExecutionResult(ok=False, output=f"exec error: {exc}", returncode=1)

        out = (proc.stdout or "") + (proc.stderr or "")
        out = out.strip()[:2000]
        return ExecutionResult(
            ok=proc.returncode == 0,
            output=out or "(no output)",
            returncode=proc.returncode,
        )
