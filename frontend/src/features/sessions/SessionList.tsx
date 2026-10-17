import { useState } from "react";
import { api, ApiError } from "../../api/client";
import type { PaginatedSessions, SessionResponse } from "../../api/types";
import StatusBadge from "../../components/StatusBadge";
import "./SessionList.css";

interface Props {
  sessions: PaginatedSessions | null;
  onSessionSelect: (session: SessionResponse) => void;
  onNewSession: () => void;
  onSessionsChange: (sessions: PaginatedSessions | null) => void;
  total: number;
  loading: boolean;
}

export default function SessionList({
  sessions,
  onSessionSelect,
  onNewSession,
  onSessionsChange,
  total,
  loading,
}: Props) {
  const [page, setPage] = useState(1);

  const loadPage = async (p: number) => {
    try {
      const data = await api.listSessions({ page: p, per_page: 20 });
      onSessionsChange(data);
      setPage(p);
    } catch (e) {
      if (e instanceof ApiError) {
        console.error(e.message);
      }
    }
  };

  const totalPages = Math.ceil(total / 20);

  if (!sessions) return null;

  const items = sessions.items;

  return (
    <div className="session-list" data-testid="session-list">
      <div className="session-list-header">
        <h2>Sessions</h2>
        <button className="btn btn-primary" onClick={onNewSession} data-testid="new-session-btn">
          + New Session
        </button>
      </div>

      {items.length === 0 && !loading && (
        <div className="empty-state">
          <div className="empty-icon">📭</div>
          <p>No sessions yet. Create one to get started.</p>
          <button className="btn btn-primary" onClick={onNewSession}>
            Create Session
          </button>
        </div>
      )}

      {items.length > 0 && (
        <>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Status</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((session) => (
                <tr key={session.id} data-testid={`session-row-${session.id}`}>
                  <td>
                    <strong className="session-name">{session.name}</strong>
                    {session.description && (
                      <div className="session-desc">{session.description}</div>
                    )}
                  </td>
                  <td>
                    <StatusBadge status={session.status} size="sm" />
                  </td>
                  <td className="session-date">
                    {new Date(session.created_at).toLocaleDateString()}
                  </td>
                  <td>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => onSessionSelect(session)}
                      data-testid={`open-session-${session.id}`}
                    >
                      Open
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {total > items.length && (
            <div className="pagination">
              <button
                className="btn btn-secondary btn-sm pagination-btn"
                onClick={() => loadPage(page - 1)}
                disabled={page <= 1}
                data-testid="prev-page"
              >
                Previous
              </button>
              <span className="page-info">
                Page {page} of {totalPages}
              </span>
              <button
                className="btn btn-secondary btn-sm pagination-btn"
                onClick={() => loadPage(page + 1)}
                disabled={page >= totalPages}
                data-testid="next-page"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}