from pathlib import Path

from src.ai_os.core.skill_registry import SkillRegistry


def test_skill_registry_upsert(tmp_path: Path) -> None:
    reg = SkillRegistry(tmp_path / "skills.json")
    row = reg.upsert("python", 6.2, 0.83)
    assert row["level"] == 6.2
    assert "python" in reg.get_all()
