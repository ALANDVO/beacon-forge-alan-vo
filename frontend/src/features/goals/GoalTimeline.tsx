import type { GoalEventResponse, TimelineResponse } from "../../api/types";
import StatusBadge from "../../components/StatusBadge";
import "./GoalTimeline.css";

interface Props {
  timeline: TimelineResponse;
  onExport: () => void;
}

function formatEventType(type: string): string {
  const map: Record<string, string> = {
    created: "Goal Created",
    started: "Goal Started",
    paused: "Goal Paused",
    resumed: "Goal Resumed",
    completed: "Goal Completed",
    failed: "Goal Failed",
    note: "Note",
    snapshot: "State Snapshot",
    budget_updated: "Budget Updated",
  };
  return map[type] ?? type;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

function formatData(data: Record<string, unknown>): string {
  if (!data || Object.keys(data).length === 0) return "";
  const parts: string[] = [];
  if ("tokens_spent" in data) parts.push(`tokens: ${data.tokens_spent}`);
  if ("note" in data) parts.push(`note: "${data.note}"`);
  if ("token_budget" in data) parts.push(`budget: ${data.token_budget}`);
  if ("state" in data) parts.push(`state: ${JSON.stringify(data.state)}`);
  Object.entries(data).forEach(([k, v]) => {
    if (!["tokens_spent", "note", "token_budget", "state"].includes(k)) {
      parts.push(`${k}: ${JSON.stringify(v)}`);
    }
  });
  return parts.join(", ");
}

export default function GoalTimeline({ timeline, onExport }: Props) {
  return (
    <div className="goal-timeline" data-testid="goal-timeline">
      <div className="timeline-header-bar">
        <div>
          <StatusBadge status={timeline.goal_status} />
          <span className="goal-tokens-display">
            Tokens: {timeline.goal_tokens_consumed}
            {timeline.goal_token_budget && (
              <span className="budget">/ {timeline.goal_token_budget}</span>
            )}
          </span>
        </div>
        <button
          className="btn btn-secondary btn-sm"
          onClick={onExport}
          data-testid="export-timeline"
        >
          Export JSON
        </button>
      </div>

      {timeline.latest_snapshot && (
        <div className="snapshot-card card" data-testid="latest-snapshot">
          <div className="snapshot-label">Latest Snapshot</div>
          <div className="snapshot-data">{formatData(timeline.latest_snapshot.data)}</div>
        </div>
      )}

      {timeline.events.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📜</div>
          <p>No events in the activity log.</p>
        </div>
      ) : (
        <div className="timeline-list">
          {timeline.events.map((ev: GoalEventResponse) => (
            <div
              key={ev.id}
              className="timeline-item"
              data-testid={`event-${ev.event_type}-${ev.seq}`}
            >
              <div className="timeline-header">
                <span className="timeline-event-type">{formatEventType(ev.event_type)}</span>
                <span className="timeline-time">{formatTime(ev.created_at)}</span>
              </div>
              {ev.tokens_at_event > 0 && (
                <div className="timeline-tokens">
                  Tokens: {ev.tokens_at_event}
                </div>
              )}
              {ev.data && Object.keys(ev.data).length > 0 && (
                <div className="timeline-data">{formatData(ev.data)}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export { formatEventType, formatTime, formatData };