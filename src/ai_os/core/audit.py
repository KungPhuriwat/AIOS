from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class SignedAuditEntry:
    ts: str
    event_type: str
    detail: dict[str, Any]
    prev_hash: str
    entry_hash: str


class SignedAuditLogger:
    def __init__(self, path: Path, secret: str | None = None) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.secret = (
            secret or os.getenv("AIOS_AUDIT_SECRET", "dev-insecure-audit-secret")
        ).encode("utf-8")

    def append(self, event_type: str, detail: dict[str, Any]) -> SignedAuditEntry:
        ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        prev_hash = self._last_hash()
        payload = {
            "ts": ts,
            "event_type": event_type,
            "detail": detail,
            "prev_hash": prev_hash,
        }
        entry_hash = self._compute_hash(payload)
        entry = SignedAuditEntry(
            ts=ts,
            event_type=event_type,
            detail=detail,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
        )
        with self.path.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(entry.__dict__, ensure_ascii=False, sort_keys=True) + "\n"
            )
        return entry

    def migrate_legacy(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"migrated": False, "legacy_lines": 0}

        lines = self.path.read_text(encoding="utf-8").splitlines()
        legacy_lines = 0
        for line in lines:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                legacy_lines += 1
                continue
            if (
                not isinstance(row, dict)
                or "entry_hash" not in row
                or "prev_hash" not in row
            ):
                legacy_lines += 1

        if legacy_lines == 0:
            return {"migrated": False, "legacy_lines": 0}

        stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        backup = self.path.with_name(f"{self.path.name}.legacy-{stamp}")
        self.path.replace(backup)
        self.path.write_text("", encoding="utf-8")
        return {"migrated": True, "legacy_lines": legacy_lines, "backup": str(backup)}

    def verify_chain(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"ok": True, "entries": 0, "legacy_lines": 0}

        lines = self.path.read_text(encoding="utf-8").splitlines()
        prev_hash = "GENESIS"
        signed_entries = 0
        legacy_lines = 0

        for idx, line in enumerate(lines, start=1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                legacy_lines += 1
                continue

            if (
                not isinstance(row, dict)
                or "entry_hash" not in row
                or "prev_hash" not in row
            ):
                legacy_lines += 1
                continue

            if row.get("prev_hash") != prev_hash:
                return {
                    "ok": False,
                    "entries": signed_entries,
                    "legacy_lines": legacy_lines,
                    "failed_line": idx,
                    "reason": "prev_hash_mismatch",
                }

            payload = {
                "ts": row.get("ts"),
                "event_type": row.get("event_type"),
                "detail": row.get("detail"),
                "prev_hash": row.get("prev_hash"),
            }
            expected = self._compute_hash(payload)
            if row.get("entry_hash") != expected:
                return {
                    "ok": False,
                    "entries": signed_entries,
                    "legacy_lines": legacy_lines,
                    "failed_line": idx,
                    "reason": "entry_hash_mismatch",
                }

            prev_hash = row["entry_hash"]
            signed_entries += 1

        return {
            "ok": legacy_lines == 0,
            "entries": signed_entries,
            "legacy_lines": legacy_lines,
            "reason": "legacy_lines_present" if legacy_lines else "verified",
        }

    def _last_hash(self) -> str:
        if not self.path.exists():
            return "GENESIS"

        lines = self.path.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("entry_hash"):
                return str(row["entry_hash"])
        return "GENESIS"

    def _compute_hash(self, payload: dict[str, Any]) -> str:
        canonical = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hmac.new(self.secret, canonical, hashlib.sha256).hexdigest()
