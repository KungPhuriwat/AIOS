from __future__ import annotations

import os
import re
from dataclasses import dataclass


WIN_DENY_COMMANDS = {
    "del",
    "erase",
    "format",
    "shutdown",
    "taskkill",
    "reg",
    "diskpart",
    "rmdir",
    "remove-item",
}

UNIX_DENY_COMMANDS = {
    "rm",
    "mkfs",
    "shutdown",
    "reboot",
    "kill",
    "killall",
    "dd",
    "chmod",
    "chown",
    "sudo",
}

WIN_ALLOW_COMMANDS = {
    "dir",
    "echo",
    "type",
    "where",
    "whoami",
    "ipconfig",
    "get-process",
    "get-service",
}

UNIX_ALLOW_COMMANDS = {
    "ls",
    "cat",
    "echo",
    "pwd",
    "whoami",
    "ps",
    "id",
}

RISK_SIGNATURES = {
    "rmrf",
    "delfq",
    "erase",
    "format",
    "dropdatabase",
    "shutdown",
    "taskkill",
    "removeitem",
    "rmdirsq",
    "regdelete",
    "diskpart",
}


@dataclass
class PermissionDecision:
    allowed: bool
    reason: str


class PermissionGateway:
    def __init__(self, default_mode: str = "read", platform: str | None = None) -> None:
        self.default_mode = default_mode
        self.platform = (platform or _detect_platform()).lower()

    def evaluate(
        self, task_type: str, prompt: str, approved_by_user: bool = False
    ) -> PermissionDecision:
        if task_type != "ops":
            return PermissionDecision(allowed=True, reason="ผ่าน policy")

        if approved_by_user:
            return PermissionDecision(allowed=True, reason="ผู้ใช้อนุมัติแล้ว")

        if self.default_mode == "read":
            return PermissionDecision(
                allowed=False,
                reason="โหมดปัจจุบันเป็น read-only สำหรับงานระบบ",
            )

        parsed = self._parse_segments(prompt)
        risk = self._detect_risk(prompt, parsed)
        if risk:
            return PermissionDecision(
                allowed=False,
                reason=f"คำสั่งเสี่ยงสูง ({risk}) ต้องได้รับการอนุมัติจากผู้ใช้ก่อน",
            )

        if parsed and not self._all_commands_allowlisted(parsed):
            return PermissionDecision(
                allowed=False,
                reason="คำสั่งไม่อยู่ใน allowlist ของ platform ต้องได้รับการอนุมัติจากผู้ใช้ก่อน",
            )

        return PermissionDecision(allowed=True, reason="ผ่าน policy")

    def _parse_segments(self, prompt: str) -> list[str]:
        parts = re.split(r"\|\||&&|[|;]", prompt)
        commands: list[str] = []
        for part in parts:
            token = part.strip()
            if not token:
                continue
            first = token.split()[0].strip("'\"`").lower()
            if first:
                commands.append(first)
        return commands

    def _detect_risk(self, prompt: str, commands: list[str]) -> str | None:
        lowered = prompt.lower()
        compact = re.sub(r"[^a-z0-9]+", "", lowered)

        for signature in RISK_SIGNATURES:
            if signature in compact:
                return signature

        deny_set = (
            WIN_DENY_COMMANDS if self.platform == "windows" else UNIX_DENY_COMMANDS
        )
        for cmd in commands:
            if cmd in deny_set:
                return cmd

        if re.search(r"(^|\s)-{1,2}rf($|\s)", lowered):
            return "-rf"

        if re.search(r"(^|\s)/[fqs]{1,3}($|\s)", lowered):
            return "dangerous-flags"

        if re.search(r"\b(c:\\|/)(\*|$)", lowered):
            return "root-path-target"

        return None

    def _all_commands_allowlisted(self, commands: list[str]) -> bool:
        if not commands:
            return False

        allow_set = (
            WIN_ALLOW_COMMANDS if self.platform == "windows" else UNIX_ALLOW_COMMANDS
        )
        return all(cmd in allow_set for cmd in commands)


def _detect_platform() -> str:
    if os.name == "nt":
        return "windows"
    return "unix"
