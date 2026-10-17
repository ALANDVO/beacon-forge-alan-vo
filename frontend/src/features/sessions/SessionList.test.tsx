import { render, screen, fireEvent } from "@testing-library/react";
import SessionList from "./SessionList";
import type { PaginatedSessions } from "../../api/types";

const mockSessions: PaginatedSessions = {
  items: [
    {
      id: "sess-1",
      name: "Refactor auth",
      description: "Clean up auth module",
      status: "active",
      started_at: "2026-10-17T10:00:00Z",
      ended_at: null,
      created_at: "2026-10-17T10:00:00Z",
      updated_at: "2026-10-17T10:00:00Z",
    },
    {
      id: "sess-2",
      name: "Fix bug #42",
      description: null,
      status: "completed",
      started_at: "2026-10-16T08:00:00Z",
      ended_at: "2026-10-16T09:00:00Z",
      created_at: "2026-10-16T08:00:00Z",
      updated_at: "2026-10-16T09:00:00Z",
    },
  ],
  total: 2,
  page: 1,
  per_page: 20,
};

describe("SessionList", () => {
  it("renders session rows with names and status badges", () => {
    const onSelect = vi.fn();
    const onNew = vi.fn();
    const onChange = vi.fn();

    render(
      <SessionList
        sessions={mockSessions}
        onSessionSelect={onSelect}
        onNewSession={onNew}
        onSessionsChange={onChange}
        total={mockSessions.total}
        loading={false}
      />,
    );

    expect(screen.getByText("Refactor auth")).toBeInTheDocument();
    expect(screen.getByText("Fix bug #42")).toBeInTheDocument();
    expect(screen.getAllByTestId("status-badge")).toHaveLength(2);
  });

  it("calls onNewSession when the New Session button is clicked", () => {
    const onSelect = vi.fn();
    const onNew = vi.fn();
    const onChange = vi.fn();

    render(
      <SessionList
        sessions={mockSessions}
        onSessionSelect={onSelect}
        onNewSession={onNew}
        onSessionsChange={onChange}
        total={mockSessions.total}
        loading={false}
      />,
    );

    fireEvent.click(screen.getByTestId("new-session-btn"));
    expect(onNew).toHaveBeenCalledTimes(1);
  });

  it("calls onSessionSelect when a session's Open button is clicked", () => {
    const onSelect = vi.fn();

    render(
      <SessionList
        sessions={mockSessions}
        onSessionSelect={onSelect}
        onNewSession={vi.fn()}
        onSessionsChange={vi.fn()}
        total={mockSessions.total}
        loading={false}
      />,
    );

    fireEvent.click(screen.getByTestId("open-session-sess-1"));
    expect(onSelect).toHaveBeenCalledWith(mockSessions.items[0]);
  });

  it("renders empty state when no sessions exist", () => {
    const emptySessions: PaginatedSessions = {
      items: [],
      total: 0,
      page: 1,
      per_page: 20,
    };

    render(
      <SessionList
        sessions={emptySessions}
        onSessionSelect={vi.fn()}
        onNewSession={vi.fn()}
        onSessionsChange={vi.fn()}
        total={0}
        loading={false}
      />,
    );

    expect(screen.getByText(/No sessions yet/)).toBeInTheDocument();
  });
});