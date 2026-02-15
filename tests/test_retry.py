import pytest

from src.ai_os.core.retry import retry_call


def test_retry_call_retries_until_success() -> None:
    state = {"n": 0}

    def flaky() -> int:
        state["n"] += 1
        if state["n"] < 3:
            raise RuntimeError("temporary")
        return 42

    result = retry_call(flaky, attempts=3, base_delay=0)
    assert result == 42


def test_retry_call_raises_after_attempts() -> None:
    def always_fail() -> int:
        raise RuntimeError("failed")

    with pytest.raises(RuntimeError):
        retry_call(always_fail, attempts=2, base_delay=0)
