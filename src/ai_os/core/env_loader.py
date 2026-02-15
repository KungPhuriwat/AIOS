from __future__ import annotations

from pathlib import Path


def load_env_file(path: str | Path = ".env", override: bool = False) -> dict[str, str]:
    env_path = Path(path)
    loaded: dict[str, str] = {}
    if not env_path.exists():
        return loaded

    import os

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue

        if key in os.environ and not override:
            loaded[key] = os.environ[key]
            continue

        os.environ[key] = value
        loaded[key] = value

    return loaded
