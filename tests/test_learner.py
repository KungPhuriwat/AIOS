from src.ai_os.core.learner import LearningOutcome, SelfLearner


def test_learner_increases_level_for_good_score() -> None:
    learner = SelfLearner()
    outcome = LearningOutcome(
        "python", success_rate=0.95, test_pass_rate=0.9, bug_rate=0.05
    )
    score = learner.score(outcome)
    nxt = learner.next_level(5.0, score)
    assert nxt > 5.0
