import { api, ApiError } from "../../api/client";
import type {
  CompactAllResponse,
  GoalResponse,
  PaginatedGoals,
  SessionResponse,
} from "../../api/types";
import GoalForm from "./GoalForm";
import GoalList from "./GoalList";
import GoalDetail from "./GoalDetail";
import Loading from "../../components/Loading";
import "./GoalDashboard.css";

interface Props {
  session: SessionResponse;
  onBack: () => void;
}
export default function GoalDashboard({ session, onBack }: Props) {
  const [goals, setGoals] = useState<PaginatedGoals | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [selectedGoal, setSelectedGoal] = useState<GoalResponse | null>(null);

  const loadGoals = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listGoals({
        session_id: session.id,
        page: 1,
        per_page: 20,
      });
      setGoals(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load goals");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGoals();
  }, [session.id]);

  const handleGoalCreated = (goal: GoalResponse) => {
    setShowCreateForm(false);
    loadGoals();
  };

  const handleGoalUpdate = (updated: GoalResponse) => {
    if (goals) {
      setGoals({
        ...goals,
        items: goals.items.map((g) => (g.id === updated.id ? updated : g)),
      });
    }
  };

  const handleGoalSelect = (goal: GoalResponse) => {
    setSelectedGoal(goal);
  };

  const handleExportAll = () => {
    if (!goals) return;
    const exportData = goals.items.map((g) => ({
      id: g.id,
      description: g.description,
      status: g.status,
      tokens_consumed: g.tokens_consumed,
      token_budget: g.token_budget,
    }));
    const dataStr = JSON.stringify(exportData, null, 2);
    const blob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `session-${session.id}-goals.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="goal-dashboard" data-testid="goal-dashboard">
      <div className="dashboard-header">
        <button className="back-btn" onClick={onBack} data-testid="back-to-sessions">
          ← Back to Sessions
        </button>
        <div>
          <h2>{session.name}</h2>
          {session.description && <p className="session-desc">{session.description}</p>}
        </div>
        <div className="dashboard-actions">
          <button
            className="btn btn-secondary btn-sm"
            onClick={handleExportAll}
            disabled={!goals?.items?.length}
            data-testid="export-goals"
          >
            Export Goals
          </button>
          {!selectedGoal && (
            <button
              className="btn btn-primary btn-sm"
              onClick={() => setShowCreateForm(true)}
              data-testid="new-goal-btn"
            >
              + New Goal
            </button>
          )}
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {showCreateForm && !selectedGoal && (
        <div className="card">
          <h3>New Goal</h3>
          <GoalForm
            sessionId={session.id}
            onGoalCreated={handleGoalCreated}
            onCancel={() => setShowCreateForm(false)}
          />
        </div>
      )}

      {loading && <Loading label="Loading goals…" />}

      {!loading && goals && selectedGoal && (
        <GoalDetail
          goal={selectedGoal}
          onGoalUpdate={handleGoalUpdate}
          onBack={() => setSelectedGoal(null)}
        />
      )}

      {!loading && goals && !selectedGoal && (
        <GoalList
          goals={goals}
          onGoalSelect={handleGoalSelect}
          onGoalsChange={setGoals}
        />
      )}
    </div>
  );
}

