"""Unit tests for the GoalLifecycleEngine state machine."""
import pytest

from app.models.goal import GoalStatus
from app.services.goal_engine import GoalLifecycleEngine, GoalStateError


@pytest.fixture
def engine():
    return GoalLifecycleEngine()


class TestStateTransitions:
    """Valid and invalid state transitions."""

    def test_pending_to_running(self, engine):
        result = engine.transition(GoalStatus.PENDING, GoalStatus.RUNNING)
        assert result.allowed
        assert result.new_status == GoalStatus.RUNNING

    def test_running_to_completed_no_budget(self, engine):
        result = engine.transition(GoalStatus.RUNNING, GoalStatus.COMPLETED)
        assert result.allowed

    def test_running_to_failed(self, engine):
        result = engine.transition(GoalStatus.RUNNING, GoalStatus.FAILED)
        assert result.allowed
        assert result.new_status == GoalStatus.FAILED

    def test_running_to_paused(self, engine):
        result = engine.transition(GoalStatus.RUNNING, GoalStatus.PAUSED)
        assert result.allowed
        assert result.new_status == GoalStatus.PAUSED

    def test_paused_to_running(self, engine):
        result = engine.transition(GoalStatus.PAUSED, GoalStatus.RUNNING)
        assert result.allowed

    def test_paused_to_completed(self, engine):
        """Cannot complete directly from paused — must resume first."""
        with pytest.raises(GoalStateError):
            engine.transition(GoalStatus.PAUSED, GoalStatus.COMPLETED)

    def test_failed_to_running_retry(self, engine):
        result = engine.transition(GoalStatus.FAILED, GoalStatus.RUNNING)
        assert result.allowed

    def test_completed_to_any_forbidden(self, engine):
        """Completed is terminal — all transitions raise GoalStateError."""
        for target in GoalStatus:
            if target == GoalStatus.COMPLETED:
                continue
            with pytest.raises(GoalStateError, match="Cannot transition"):
                engine.transition(GoalStatus.COMPLETED, target)

    def test_same_status_rejected(self, engine):
        with pytest.raises(GoalStateError):
            engine.transition(GoalStatus.PENDING, GoalStatus.PENDING)

    def test_pending_to_failed_rejected(self, engine):
        """Cannot fail directly from pending — goal hasn't started."""
        with pytest.raises(GoalStateError):
            engine.transition(GoalStatus.PENDING, GoalStatus.FAILED)


class TestTokenBudget:
    """Token budget enforcement on completion."""

    def test_complete_within_budget(self, engine):
        result = engine.transition(
            GoalStatus.RUNNING,
            GoalStatus.COMPLETED,
            tokens_spent=500,
            token_budget=1000,
            tokens_consumed_so_far=200,
        )
        assert result.allowed
        assert result.tokens_added == 500

    def test_complete_exceeds_budget_with_tolerance(self, engine):
        """5 % tolerance: budget 1000, consumed 200, spent 850 → total 1050 ≤ 1050."""
        result = engine.transition(
            GoalStatus.RUNNING,
            GoalStatus.COMPLETED,
            tokens_spent=850,
            token_budget=1000,
            tokens_consumed_so_far=200,
        )
        assert result.allowed  # 1050 ≤ 1050 (5% tolerance)

    def test_complete_exceeds_budget_rejected(self, engine):
        """Budget 1000, consumed 200, spent 900 → total 1100 > 1050 (max)."""
        result = engine.transition(
            GoalStatus.RUNNING,
            GoalStatus.COMPLETED,
            tokens_spent=900,
            token_budget=1000,
            tokens_consumed_so_far=200,
        )
        assert not result.allowed
        assert "budget exceeded" in (result.reason or "").lower()

    def test_complete_no_budget_always_allowed(self, engine):
        result = engine.transition(
            GoalStatus.RUNNING,
            GoalStatus.COMPLETED,
            tokens_spent=100_000,
            token_budget=None,
        )
        assert result.allowed

    def test_budget_not_enforced_on_non_complete(self, engine):
        """Token budget only checked on completion, not on other transitions."""
        result = engine.transition(
            GoalStatus.RUNNING,
            GoalStatus.FAILED,
            tokens_spent=10_000,
            token_budget=100,
        )
        assert result.allowed


class TestAllowedTargets:
    """The allowed_targets helper."""

    def test_pending_targets(self, engine):
        targets = engine.allowed_targets(GoalStatus.PENDING)
        assert "running" in targets
        assert "paused" in targets

    def test_completed_targets_empty(self, engine):
        assert engine.allowed_targets(GoalStatus.COMPLETED) == []

    def test_failed_targets(self, engine):
        targets = engine.allowed_targets(GoalStatus.FAILED)
        assert targets == ["running"]