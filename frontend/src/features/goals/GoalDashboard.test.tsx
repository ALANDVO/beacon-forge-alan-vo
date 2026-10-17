import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import GoalDashboard from "./GoalDashboard";
import { api } from "../../api/client";
import type { SessionResponse, PaginatedGoals, GoalResponse } from "../../api/types";

const mockSession: SessionResponse = {
  id: "sess-1",
  name: "Test Session",
  description: "A test session",
  status: "active",
  started_at: "2026-10-17T10:00:00Z",
  ended_at: null,
  created_at: "2026-10-17T10:00:00Z",
  updated_at: "2026-10-17T10:00:00Z",
};

const mockGoals: PaginatedGoals = {
  items: [
    {
      id: "goal-1",
      session_id: "sess-1",
      description: "Implement feature X",
      token_budget: 1000,
      tokens_consumed: 500,
      status: "running",
      started_at: "2026-10-17T10:05:00Z",
      completed_at: null,
      created_at: "2026-10-17T10:03:00Z",
      updated_at: "2026-10-17T10:05:00Z",
    },
  ],
  total: 1,
  page: 1,
  per_page: 20,
};

vi.mock("../../api/client", () => ({
  api: {
    listGoals: vi.fn(),
    getTimeline: vi.fn(),
    transitionGoal: vi.fn(),
  },
  ApiError: class ApiError extends Error {},
}));

describe("GoalDashboard", () => {
  it("renders session name and goal list", async () => {
    vi.mocked(api.listGoals).mockResolvedValue(mockGoals);

    render(
      <GoalDashboard session={mockSession} onBack={vi.fn()} />,
    );

    expect(screen.getByText("Test Session")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Implement feature X")).toBeInTheDocument();
    });
  });

  it("shows New Goal button when no goal is selected", async () => {
    vi.mocked(api.listGoals).mockResolvedValue(mockGoals);

    render(
      <GoalDashboard session={mockSession} onBack={vi.fn()} />,
    );

    await waitFor(() => {
      expect(screen.getByTestId("new-goal-btn")).toBeInTheDocument();
    });
  });

  it("calls onBack when Back button is clicked", async () => {
    vi.mocked(api.listGoals).mockResolvedValue(mockGoals);
    const onBack = vi.fn();

    render(
      <GoalDashboard session={mockSession} onBack={onBack} />,
    );

    await waitFor(() => {
      expect(screen.getByTestId("back-to-sessions")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("back-to-sessions"));
    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it("opens GoalForm when New Goal button is clicked", async () => {
    vi.mocked(api.listGoals).mockResolvedValue(mockGoals);

    render(
      <GoalDashboard session={mockSession} onBack={vi.fn()} />,
    );

    await waitFor(() => {
      expect(screen.getByTestId("new-goal-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("new-goal-btn"));
    expect(screen.getByTestId("goal-form")).toBeInTheDocument();
  });

  it("renders empty state when no goals exist", async () => {
    const emptyGoals: PaginatedGoals = { items: [], total: 0, page: 1, per_page: 20 };
    vi.mocked(api.listGoals).mockResolvedValue(emptyGoals);

    render(
      <GoalDashboard session={mockSession} onBack={vi.fn()} />,
    );

    await waitFor(() => {
      expect(screen.getByText(/No goals yet/)).toBeInTheDocument();
    });
  });
});