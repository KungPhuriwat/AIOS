from __future__ import annotations

import time
from typing import Callable, TypeVar

T = TypeVar("T")


def retry_call(
    fn: Callable[[], T],
    attempts: int = 3,
    base_delay: float = 0.6,
    backoff: float = 2.0,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> T:
    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    delay = base_delay
    last_exc: Exception | None = None
    for idx in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if idx == attempts - 1:
                break
            if delay > 0:
                sleep_fn(delay)
            delay *= backoff

    assert last_exc is not None
    raise last_exc
