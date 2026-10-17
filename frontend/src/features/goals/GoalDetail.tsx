import { useEffect, useState } from "react";
import { api, ApiError } from "../../api/client";
import type { GoalResponse, TimelineResponse } from "../../api/types";
import GoalTimeline from "./GoalTimeline";
import StatusBadge from "../../components/StatusBadge";
import Loading from "../../components/Loading";
import "./GoalDetail.css";

interface Props {
  goal: GoalResponse;
  onGoalUpdate: (goal: GoalResponse) => void;
  onBack: () => void;
}

export default function GoalDetail({ goal: initialGoal, onGoalUpdate, onBack }: Props) {
  const [goal, setGoal] = useState<GoalResponse>(initialGoal);
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTimeline = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getTimeline(goal.id);
      setTimeline(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load timeline");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTimeline();
  }, [goal.id]);

  const handleTransition = async (target: string) => {
    try {
      const updated = await api.transitionGoal(goal.id, { target, tokens_spent: 0 });
      setGoal(updated);
      onGoalUpdate(updated);
      setTimeout(loadTimeline, 100);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Transition failed");
    }
  };

  const handleExport = () => {
    if (!timeline) return;
    const dataStr = JSON.stringify(timeline, null, 2);
    const blob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `goal-${goal.id}-timeline.json`;
    a.click();
    URL.revokeObjectURL(url);
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

  const next = getNextTransitions(goal.status);

  return (
    <div className="goal-detail" data-testid="goal-detail">
      <button className="back-btn" onClick={onBack} data-testid="back-to-dashboard">
        ← Back to Goals
      </button>

      <div className="card">
        <div className="goal-info-card">
          <h2>{goal.description}</h2>
          <div className="goal-meta">
            <span className="meta-item">
              <strong>Status:</strong>
              <StatusBadge status={goal.status} />
            </span>
            <span className="meta-item">
              <strong>Tokens:</strong>
              {`${goal.tokens_consumed}${goal.token_budget ? ` / ${goal.token_budget}` : ""}`}
            </span>
            <span className="meta-item">
              <strong>Created:</strong> {new Date(goal.created_at).toLocaleString()}
            </span>
            {goal.started_at && (
              <span className="meta-item">
                <strong>Started:</strong> {new Date(goal.started_at).toLocaleString()}
              </span>
            )}
            {goal.completed_at && (
              <span className="meta-item">
                <strong>Completed:</strong> {new Date(goal.completed_at).toLocaleString()}
              </span>
            )}
          </div>
        </div>

        {next.length > 0 && (
          <div className="transition-buttons">
            {next.map((target) => (
              <button
                key={target}
                className={`btn ${target === "completed" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => handleTransition(target)}
                data-testid={`transition-to-${target}`}
              >
                {target.charAt(0).toUpperCase() + target.slice(1)}
              </button>
            ))}
          </div>
        )}

        {error && <div className="error-banner">{error}</div>}
      </div>

      <div className="card">
        <h3>Activity Timeline</h3>
        {loading && <Loading label="Loading timeline…" />}
        {timeline && (
          <GoalTimeline timeline={timeline} onExport={handleExport} />
        )}
        {!timeline && !loading && (
          <button
            className="btn btn-secondary"
            onClick={loadTimeline}
            data-testid="load-timeline-btn"
          >
            Load Timeline
          </button>
        )}
      </div>
    </div>
  );
}