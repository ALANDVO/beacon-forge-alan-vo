import { api, ApiError } from "../../api/client";
import type { GoalResponse, PaginatedGoals } from "../../api/types";
import StatusBadge from "../../components/StatusBadge";
import "./GoalList.css";

interface Props {
  goals: PaginatedGoals;
  onGoalSelect: (goal: GoalResponse) => void;
  onGoalsChange: (goals: PaginatedGoals) => void;
}

export default function GoalList({ goals, onGoalSelect, onGoalsChange }: Props) {
  const handleTransition = async (goal: GoalResponse, target: string) => {
    try {
      await api.transitionGoal(goal.id, { target, tokens_spent: 0 });
      const data = await api.listGoals({ session_id: goal.session_id, page: 1, per_page: 20 });
      onGoalsChange(data);
    } catch (err) {
      if (err instanceof ApiError) {
        console.error(err.message);
      }
    }
  };

  const handleDelete = async (goal: GoalResponse) => {
    if (!confirm("Delete this goal? This cannot be undone.")) return;
    try {
      await api.deleteGoal(goal.id);
      const data = await api.listGoals({ session_id: goal.session_id, page: 1, per_page: 20 });
      onGoalsChange(data);
    } catch (err) {
      if (err instanceof ApiError) {
        console.error(err.message);
      }
    }
  };

  const getNextTransitions = (status: string): string[] => {
    const map: Record<string, string[]> = {
      pending: ["running", "failed"],
      running: ["paused", "completed", "failed"],
      paused: ["running"],
      failed: ["running"],
      completed: [],
    };
    return map[status] ?? [];
  };

  const getTransitionLabel = (status: string) => {
    const map: Record<string, string> = {
      pending: "Start",
      running: "Complete",
      paused: "Resume",
      failed: "Retry",
    };
    return map[status] ?? "Action";
  };

  return (
    <div className="goal-list" data-testid="goal-list">
      {goals.items.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🎯</div>
          <p>No goals yet. Create one to get started.</p>
        </div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Goal</th>
              <th>Status</th>
              <th>Tokens</th>
              <th>Timeline</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {goals.items.map((goal) => {
              const nextTargets = getNextTransitions(goal.status);
              const primaryTarget = nextTargets[0];

              return (
                <tr key={goal.id} data-testid={`goal-row-${goal.id}`}>
                  <td>
                    <div
                      className="goal-desc"
                      onClick={() => onGoalSelect(goal)}
                      title="View details"
                    >
                      {goal.description}
                    </div>
                  </td>
                  <td>
                    <StatusBadge status={goal.status} size="sm" />
                  </td>
                  <td className="goal-tokens">
                    {goal.tokens_consumed}
                    {goal.token_budget && (
                      <span className="total-budget">/ {goal.token_budget}</span>
                    )}
                  </td>
                  <td>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => onGoalSelect(goal)}
                      data-testid={`view-timeline-${goal.id}`}
                    >
                      Timeline
                    </button>
                  </td>
                  <td>
                    {primaryTarget && (
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={() => handleTransition(goal, primaryTarget)}
                        data-testid={`transition-${goal.id}`}
                      >
                        {getTransitionLabel(goal.status)}
                      </button>
                    )}
                    {nextTargets.length > 1 && nextTargets[1] !== undefined && (
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => handleTransition(goal, nextTargets[1]!)}
                        data-testid={`transition-alt-${goal.id}`}
                      >
                        {nextTargets[1]}
                      </button>
                    )}
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => handleDelete(goal)}
                      data-testid={`delete-${goal.id}`}
                    >
                      Del
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}