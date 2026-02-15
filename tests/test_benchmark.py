from src.ai_os.core.benchmark import CodingBenchmarkEngine
from src.ai_os.core.models import TaskResult


def test_benchmark_evaluate_task_returns_reasonable_ranges() -> None:
    engine = CodingBenchmarkEngine()
    result = TaskResult(
        ok=True,
        output="Use unit test and edge validation with lint",
        confidence=0.85,
        inferred=False,
    )
    outcome = engine.evaluate_task(language="python", prompt="x", result=result)
    assert 0.0 <= outcome.success_rate <= 1.0
    assert 0.0 <= outcome.test_pass_rate <= 1.0
    assert 0.0 <= outcome.bug_rate <= 1.0


def test_benchmark_penalizes_inferred_output() -> None:
    engine = CodingBenchmarkEngine()
    result = TaskResult(ok=True, output="generic answer", confidence=0.6, inferred=True)
    outcome = engine.evaluate_task(language="python", prompt="x", result=result)
    assert outcome.test_pass_rate < 0.6
