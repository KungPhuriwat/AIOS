from __future__ import annotations

from dataclasses import dataclass

from ..agents.coding_agent import CodingAgent
from .learner import LearningOutcome
from .models import TaskResult


@dataclass
class BenchmarkSummary:
    language: str
    avg_success_rate: float
    avg_test_pass_rate: float
    avg_bug_rate: float
    avg_confidence: float


class CodingBenchmarkEngine:
    def evaluate_task(
        self, language: str, prompt: str, result: TaskResult
    ) -> LearningOutcome:
        text = result.output.lower()
        quality_terms = [
            "test",
            "unit",
            "edge",
            "error",
            "lint",
            "static",
            "validation",
        ]
        hits = sum(1 for t in quality_terms if t in text)

        success_rate = 0.95 if result.ok else 0.3
        test_pass_rate = min(1.0, 0.45 + (hits * 0.1))
        if result.inferred:
            test_pass_rate = max(0.2, test_pass_rate - 0.2)

        bug_rate = 0.05
        if result.confidence < 0.75:
            bug_rate = 0.12
        if not result.ok:
            bug_rate = 0.35

        return LearningOutcome(
            skill_name=language,
            success_rate=success_rate,
            test_pass_rate=test_pass_rate,
            bug_rate=bug_rate,
        )

    def run_language_benchmark(
        self, agent: CodingAgent, language: str
    ) -> BenchmarkSummary:
        prompts = [
            "create robust input validation strategy",
            "design unit tests with edge cases",
            "refactor for reliability and maintainability",
        ]
        outcomes = []
        confidence_sum = 0.0

        for p in prompts:
            result = agent.run(prompt=p, language=language)
            outcomes.append(
                self.evaluate_task(language=language, prompt=p, result=result)
            )
            confidence_sum += result.confidence

        n = float(len(outcomes))
        return BenchmarkSummary(
            language=language,
            avg_success_rate=sum(o.success_rate for o in outcomes) / n,
            avg_test_pass_rate=sum(o.test_pass_rate for o in outcomes) / n,
            avg_bug_rate=sum(o.bug_rate for o in outcomes) / n,
            avg_confidence=confidence_sum / n,
        )
