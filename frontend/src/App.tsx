import { useEffect, useState } from "react";
import { api, ApiError } from "./api/client";
import type { PaginatedSessions, SessionResponse } from "./api/types";
import GoalDashboard from "./features/goals/GoalDashboard";
import SessionList from "./features/sessions/SessionList";
import SessionForm from "./features/sessions/SessionForm";
import Loading from "./components/Loading";
import ErrorBoundary from "./components/ErrorBoundary";

function App() {
  const [sessions, setSessions] = useState<PaginatedSessions | null>(null);
  const [selectedSession, setSelectedSession] = useState<SessionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNewSession, setShowNewSession] = useState(false);

  const loadSessions = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listSessions();
      setSessions(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load sessions");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  const handleSessionCreated = (session: SessionResponse) => {
    setShowNewSession(false);
    setSessions((prev) =>
      prev ? { ...prev, items: [session, ...prev.items] } : null,
    );
    setSelectedSession(session);
    loadSessions();
  };

  const handleSessionSelect = (session: SessionResponse) => {
    setSelectedSession(session);
  };

  const goBack = () => {
    setSelectedSession(null);
  };

  return (
    <ErrorBoundary>
      <div className="app">
        <header className="app-header">
          <h1>Beacon Forge</h1>
          <p className="subtitle">Agent session goal management</p>
        </header>

        <main className="app-main">
          {loading && <Loading />}
          {error && <div className="error-banner">{error}</div>}

          {!selectedSession && sessions && (
            <>
              <SessionForm
                open={showNewSession}
                onClose={() => setShowNewSession(false)}
                onCreated={handleSessionCreated}
              />
              <SessionList
                sessions={sessions}
                onSessionSelect={handleSessionSelect}
                onNewSession={() => setShowNewSession(true)}
                onSessionsChange={setSessions}
                total={sessions.total}
                loading={loading}
              />
            </>
          )}

          {selectedSession && (
            <GoalDashboard
              session={selectedSession}
              onBack={goBack}
            />
          )}
        </main>

        <footer className="app-footer">
          <span className="tag">AI/ML developer tool</span>
        </footer>
      </div>
    </ErrorBoundary>
  );
}

export default App;