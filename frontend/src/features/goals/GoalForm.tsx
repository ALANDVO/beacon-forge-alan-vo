import { useState } from "react";
import { api, ApiError } from "../../api/client";
import type { GoalResponse } from "../../api/types";
import "./GoalForm.css";

interface Props {
  sessionId: string;
  onGoalCreated: (goal: GoalResponse) => void;
  onCancel: () => void;
}

export default function GoalForm({ sessionId, onGoalCreated, onCancel }: Props) {
  const [description, setDescription] = useState("");
  const [tokenBudget, setTokenBudget] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const goal = await api.createGoal(sessionId, {
        description: description.trim(),
        token_budget: tokenBudget.trim() ? parseInt(tokenBudget, 10) : undefined,
      });
      onGoalCreated(goal);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create goal");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="goal-form" onSubmit={handleSubmit} data-testid="goal-form">
      <div className="form-group">
        <label htmlFor="goal-desc">Goal Description</label>
        <input
          id="goal-desc"
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="What should the agent accomplish?"
          required
          minLength={1}
          maxLength={2000}
          disabled={submitting}
          data-testid="goal-desc-input"
        />
      </div>
      <div className="form-group">
        <label htmlFor="goal-budget">Token Budget (optional)</label>
        <input
          id="goal-budget"
          type="number"
          value={tokenBudget}
          onChange={(e) => setTokenBudget(e.target.value)}
          placeholder="e.g. 1000"
          min={1}
          disabled={submitting}
          data-testid="goal-budget-input"
        />
        <div className="hint">
          Maximum tokens the agent may spend. Completion is rejected if exceeded
          beyond 5% tolerance.
        </div>
      </div>
      {error && <div className="error-text">{error}</div>}
      <div className="form-actions">
        <button
          type="button"
          className="btn btn-secondary"
          onClick={onCancel}
          disabled={submitting}
          data-testid="cancel-goal"
        >
          Cancel
        </button>
        <button
          type="submit"
          className="btn btn-primary"
          disabled={submitting || !description.trim()}
          data-testid="create-goal-btn"
        >
          {submitting ? "Creating…" : "Create Goal"}
        </button>
      </div>
    </form>
  );
}