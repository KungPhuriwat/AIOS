from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LearningOutcome:
    skill_name: str
    success_rate: float
    test_pass_rate: float
    bug_rate: float


class SelfLearner:
    def score(self, outcome: LearningOutcome) -> float:
        # Weighted score: correctness dominates, bugs penalize heavily.
        raw = (
            (0.5 * outcome.success_rate)
            + (0.45 * outcome.test_pass_rate)
            - (0.35 * outcome.bug_rate)
        )
        return max(0.0, min(1.0, raw))

    def next_level(self, current_level: float, score: float) -> float:
        if score < 0.6:
            return current_level
        growth = (score - 0.6) * 2.5
        return min(10.0, current_level + growth)
