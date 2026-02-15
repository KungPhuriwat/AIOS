from pathlib import Path

from src.ai_os.core.env_loader import load_env_file


def test_load_env_file_sets_variables(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("AIOS_LLM_PROVIDER=opencode\nX_TEST=1\n", encoding="utf-8")
    monkeypatch.delenv("AIOS_LLM_PROVIDER", raising=False)
    out = load_env_file(env_file)
    assert out["AIOS_LLM_PROVIDER"] == "opencode"


def test_load_env_file_does_not_override_by_default(
    tmp_path: Path, monkeypatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("X_TEST=2\n", encoding="utf-8")
    monkeypatch.setenv("X_TEST", "9")
    out = load_env_file(env_file)
    assert out["X_TEST"] == "9"
