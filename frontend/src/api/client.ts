/**
 * Typed API client for the Beacon Forge backend.
 *
 * Reads the API base URL and key from Vite environment variables
 * (``VITE_API_URL``, ``VITE_API_KEY``).  Falls back to ``http://127.0.0.1:8000``
 * and no auth for local development.
 */
import type {
  ErrorResponse,
  EventAppend,
  GoalCreate,
  GoalResponse,
  GoalTarget,
  GoalUpdate,
  HealthResponse,
  PaginatedGoals,
  PaginatedSessions,
  SessionCreate,
  SessionResponse,
  TimelineResponse,
} from "./types";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
const API_KEY = import.meta.env.VITE_API_KEY ?? "";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public body: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class BeaconForgeClient {
  private base: string;
  private apiKey: string;

  constructor(base: string = API_BASE, apiKey: string = API_KEY) {
    this.base = base.replace(/\/+$/, "");
    this.apiKey = apiKey;
  }

  private get headers(): Record<string, string> {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (this.apiKey) {
      h["X-API-Key"] = this.apiKey;
    }
    return h;
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const url = `${this.base}${path}`;
    const resp = await fetch(url, {
      ...init,
      headers: { ...this.headers, ...init?.headers },
    });
    if (!resp.ok) {
      let body: unknown;
      try {
        body = await resp.json();
      } catch {
        body = await resp.text();
      }
      const detail =
        typeof body === "object" && body !== null && "detail" in body
          ? (body as ErrorResponse).detail
          : `HTTP ${resp.status}`;
      throw new ApiError(detail, resp.status, body);
    }
    if (resp.status === 204) return undefined as T;
    return (await resp.json()) as T;
  }

  // --- Health ---
  health(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health");
  }

  // --- Sessions ---
  listSessions(params?: { page?: number; per_page?: number }): Promise<PaginatedSessions> {
    const q = new URLSearchParams();
    if (params?.page) q.set("page", String(params.page));
    if (params?.per_page) q.set("per_page", String(params.per_page));
    const qs = q.toString() ? `?${q.toString()}` : "";
    return this.request<PaginatedSessions>(`/api/sessions${qs}`);
  }

  createSession(payload: SessionCreate): Promise<SessionResponse> {
    return this.request<SessionResponse>("/api/sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  getSession(id: string): Promise<SessionResponse> {
    return this.request<SessionResponse>(`/api/sessions/${id}`);
  }

  updateSession(id: string, name?: string, description?: string): Promise<SessionResponse> {
    const q = new URLSearchParams();
    if (name !== undefined) q.set("name", name);
    if (description !== undefined) q.set("description", description);
    const qs = q.toString() ? `?${q.toString()}` : "";
    return this.request<SessionResponse>(`/api/sessions/${id}${qs}`, { method: "PATCH" });
  }

  archiveSession(id: string): Promise<SessionResponse> {
    return this.request<SessionResponse>(`/api/sessions/${id}`, { method: "DELETE" });
  }

  // --- Goals ---
  listGoals(params?: {
    session_id?: string;
    status?: string;
    page?: number;
    per_page?: number;
  }): Promise<PaginatedGoals> {
    const q = new URLSearchParams();
    if (params?.session_id) q.set("session_id", params.session_id);
    if (params?.status) q.set("status", params.status);
    if (params?.page) q.set("page", String(params.page));
    if (params?.per_page) q.set("per_page", String(params.per_page));
    const qs = q.toString() ? `?${q.toString()}` : "";
    return this.request<PaginatedGoals>(`/api/goals${qs}`);
  }

  createGoal(sessionId: string, payload: GoalCreate): Promise<GoalResponse> {
    return this.request<GoalResponse>(`/api/sessions/${sessionId}/goals`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  getGoal(id: string): Promise<GoalResponse> {
    return this.request<GoalResponse>(`/api/goals/${id}`);
  }

  updateGoal(id: string, payload: GoalUpdate): Promise<GoalResponse> {
    return this.request<GoalResponse>(`/api/goals/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  }

  deleteGoal(id: string): Promise<GoalResponse> {
    return this.request<GoalResponse>(`/api/goals/${id}`, { method: "DELETE" });
  }

  transitionGoal(id: string, payload: GoalTarget): Promise<GoalResponse> {
    return this.request<GoalResponse>(`/api/goals/${id}/transition`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  appendEvent(id: string, payload: EventAppend): Promise<{ id: string; seq: number; event_type: string }> {
    return this.request<{ id: string; seq: number; event_type: string }>(
      `/api/goals/${id}/events`,
      { method: "POST", body: JSON.stringify(payload) },
    );
  }

  getTimeline(id: string): Promise<TimelineResponse> {
    return this.request<TimelineResponse>(`/api/goals/${id}/timeline`);
  }
}

export const api = new BeaconForgeClient();