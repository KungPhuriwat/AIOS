import json
from pathlib import Path

from src.ai_os.core.audit import SignedAuditLogger


def test_signed_audit_chain_is_valid(tmp_path: Path) -> None:
    logger = SignedAuditLogger(tmp_path / "audit.log", secret="test-secret")
    logger.append("event1", {"x": 1})
    logger.append("event2", {"y": 2})
    status = logger.verify_chain()
    assert status["ok"]
    assert status["entries"] == 2


def test_signed_audit_chain_detects_tampering(tmp_path: Path) -> None:
    path = tmp_path / "audit.log"
    logger = SignedAuditLogger(path, secret="test-secret")
    logger.append("event1", {"x": 1})
    logger.append("event2", {"y": 2})

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows[1]["detail"] = {"y": 999}
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows)
        + "\n",
        encoding="utf-8",
    )

    status = logger.verify_chain()
    assert not status["ok"]
    assert status["reason"] == "entry_hash_mismatch"


def test_signed_audit_handles_legacy_lines_without_crashing(tmp_path: Path) -> None:
    path = tmp_path / "audit.log"
    path.write_text("{'legacy': true}\n", encoding="utf-8")
    logger = SignedAuditLogger(path, secret="test-secret")
    logger.append("event1", {"x": 1})
    status = logger.verify_chain()
    assert not status["ok"]
    assert status["reason"] == "legacy_lines_present"
    assert status["entries"] == 1


def test_signed_audit_migrates_legacy_file(tmp_path: Path) -> None:
    path = tmp_path / "audit.log"
    path.write_text("{'legacy': true}\n", encoding="utf-8")
    logger = SignedAuditLogger(path, secret="test-secret")
    migration = logger.migrate_legacy()
    assert migration["migrated"]
    assert path.exists()
    assert path.read_text(encoding="utf-8") == ""
    backup = Path(migration["backup"])
    assert backup.exists()


def test_signed_audit_repairs_invalid_chain(tmp_path: Path) -> None:
    path = tmp_path / "audit.log"
    logger = SignedAuditLogger(path, secret="test-secret")
    logger.append("event1", {"x": 1})
    logger.append("event2", {"y": 2})

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows[1]["entry_hash"] = "broken"
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows)
        + "\n",
        encoding="utf-8",
    )

    repaired = logger.repair_invalid_chain()
    assert repaired["repaired"]
    assert path.exists()
    assert path.read_text(encoding="utf-8") == ""
    assert Path(repaired["backup"]).exists()
