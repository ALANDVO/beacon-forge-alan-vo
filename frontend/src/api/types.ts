/**
 * Typed API surface derived from the Beacon Forge backend (FastAPI)
 * response envelopes.  Fields mirror backend/app/models/schemas.py.
 */

export type SessionStatus = "active" | "paused" | "archived" | "completed";

export type GoalStatus = "pending" | "running" | "paused" | "completed" | "failed";

export type EventType =
  | "created"
  | "started"
  | "paused"
  | "resumed"
  | "completed"
  | "failed"
  | "note"
  | "budget_updated"
  | "snapshot";

export interface SessionResponse {
  id: string;
  name: string;
  description: string | null;
  status: SessionStatus;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SessionCreate {
  name: string;
  description?: string | null;
}

export interface GoalResponse {
  id: string;
  session_id: string;
  description: string;
  token_budget: number | null;
  tokens_consumed: number;
  status: GoalStatus;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface GoalCreate {
  description: string;
  token_budget?: number | null;
}

export interface GoalUpdate {
  description?: string | null;
  token_budget?: number | null;
}

export interface GoalTarget {
  target: string;
  tokens_spent?: number;
  note?: string | null;
}

export interface GoalEventResponse {
  id: string;
  goal_id: string;
  seq: number;
  event_type: string;
  data: Record<string, unknown>;
  tokens_at_event: number;
  created_at: string;
}

export interface TimelineResponse {
  goal_id: string;
  goal_status: string;
  goal_tokens_consumed: number;
  goal_token_budget: number | null;
  latest_snapshot: GoalEventResponse | null;
  events: GoalEventResponse[];
}

export interface EventAppend {
  event_type: EventType;
  data?: Record<string, unknown> | null;
}

export interface PaginatedSessions {
  items: SessionResponse[];
  total: number;
  page: number;
  per_page: number;
}

export interface PaginatedGoals {
  items: GoalResponse[];
  total: number;
  page: number;
  per_page: number;
}

export interface ErrorResponse {
  detail: string;
}

export interface CompactResponse {
  goal_id: string;
  total_events_before: number;
  total_events_after: number;
  snapshots_pruned: number;
  latest_snapshot_id: string | null;
}

export interface CompactAllResponse {
  goals_compacted: number;
  total_events_before: number;
  total_events_after: number;
  total_snapshots_pruned: number;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
}