"""Goal lifecycle state machine — deterministic, domain-enforced transitions.

State machine (current → target → new_state):

    pending   → running   (start)
    pending   → paused    (pause without start — defensive)
    running   → paused    (pause)
    running   → completed (finish — token budget enforced)
    running   → failed    (abort)
    paused    → running   (resume)
    failed    → running   (retry)
    completed → *         FORBIDDEN (terminal)

Invariants enforced on ``complete``:
    - consumed tokens ≤ budget × (1 + tolerance)  when a budget exists.
    - A goal with no budget can always be completed.

This is the substantive domain engine: state validation, token accounting,
and transition rules — not plain CRUD.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..core.config import settings
from ..models.goal import GoalStatus


@dataclass(frozen=True)
class TransitionResult:
    """Result of a state-machine transition attempt."""

    new_status: GoalStatus
    tokens_added: int
    allowed: bool
    reason: str | None = None  # None when allowed; message when rejected.


class GoalStateError(Exception):
    """Raised when a state transition is invalid."""


class GoalLifecycleEngine:
    """Deterministic goal state machine with token-budget enforcement."""

    # Current status → set of allowed target statuses.
    _TRANSITIONS: dict[GoalStatus, frozenset[GoalStatus]] = {
        GoalStatus.PENDING: frozenset({GoalStatus.RUNNING, GoalStatus.PAUSED}),
        GoalStatus.RUNNING: frozenset({GoalStatus.PAUSED, GoalStatus.COMPLETED, GoalStatus.FAILED}),
        GoalStatus.PAUSED: frozenset({GoalStatus.RUNNING}),
        GoalStatus.FAILED: frozenset({GoalStatus.RUNNING}),
        GoalStatus.COMPLETED: frozenset(),  # terminal
    }

    def __init__(self, budget_tolerance: float | None = None):
        self._tolerance = budget_tolerance if budget_tolerance is not None else settings.goal_budget_tolerance

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def can_transition(self, current: GoalStatus, target: GoalStatus) -> bool:
        """Return True if ``current → target`` is a valid transition."""
        return target in self._TRANSITIONS.get(current, frozenset())

    def validate_transition(self, current: GoalStatus, target: GoalStatus) -> None:
        """Raise GoalStateError if the transition is invalid."""
        if current == target:
            raise GoalStateError(f"Goal is already {target.value}")
        if not self.can_transition(current, target):
            raise GoalStateError(
                f"Cannot transition from {current.value} to {target.value}"
            )

    def transition(
        self,
        current: GoalStatus,
        target: GoalStatus,
        tokens_spent: int = 0,
        token_budget: int | None = None,
        tokens_consumed_so_far: int = 0,
    ) -> TransitionResult:
        """Validate and produce a transition result.

        On completion, enforces the token-budget invariant.
        """
        self.validate_transition(current, target)

        # Token budget enforcement only on completion.
        if target == GoalStatus.COMPLETED and token_budget is not None:
            total = tokens_consumed_so_far + tokens_spent
            max_allowed = int(token_budget * (1 + self._tolerance))
            if total > max_allowed:
                return TransitionResult(
                    new_status=target,
                    tokens_added=tokens_spent,
                    allowed=False,
                    reason=(
                        f"Token budget exceeded: consumed {total}, "
                        f"budget {token_budget} (with {self._tolerance:.0%} tolerance → max {max_allowed})"
                    ),
                )

        return TransitionResult(
            new_status=target,
            tokens_added=tokens_spent,
            allowed=True,
        )

    def allowed_targets(self, current: GoalStatus) -> list[str]:
        """Return list of valid next statuses for ``current``."""
        return sorted(s.value for s in self._TRANSITIONS.get(current, frozenset()))