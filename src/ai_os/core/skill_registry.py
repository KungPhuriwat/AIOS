from __future__ import annotations

import json
from pathlib import Path

from .models import SkillLevel


class SkillRegistry:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"skills": {}, "changes": []})

    def _read(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: dict) -> None:
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def get_all(self) -> dict[str, dict]:
        return self._read()["skills"]

    def upsert(self, name: str, new_level: float, benchmark_score: float) -> dict:
        data = self._read()
        old = data["skills"].get(name)
        item = SkillLevel(
            name=name,
            level=round(new_level, 2),
            last_updated=SkillLevel.now_iso(),
            benchmark_score=round(benchmark_score, 2),
        )
        data["skills"][name] = item.__dict__

        if old is None or old["level"] != item.level:
            data["changes"].append(
                {
                    "skill": name,
                    "old_level": None if old is None else old["level"],
                    "new_level": item.level,
                    "ts": item.last_updated,
                    "benchmark_score": item.benchmark_score,
                }
            )

        self._write(data)
        return item.__dict__

    def latest_changes(self, limit: int = 10) -> list[dict]:
        data = self._read()
        return list(reversed(data["changes"][-limit:]))
