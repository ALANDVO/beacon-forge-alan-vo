import { useState } from "react";
import { api, ApiError } from "../../api/client";
import type { SessionResponse } from "../../api/types";
import "./SessionForm.css";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: (session: SessionResponse) => void;
}

export default function SessionForm({ open, onClose, onCreated }: Props) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const session = await api.createSession({
        name: name.trim(),
        description: description.trim() || undefined,
      });
      onCreated(session);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create session");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" data-testid="session-form-modal">
      <div className="modal">
        <div className="modal-header">
          <h2>New Session</h2>
          <button className="modal-close" onClick={onClose} data-testid="close-session-form">
            ×
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="session-name">Name</label>
            <input
              id="session-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Refactor auth module"
              required
              minLength={1}
              maxLength={200}
              disabled={submitting}
              data-testid="session-name-input"
            />
          </div>
          <div className="form-group">
            <label htmlFor="session-desc">Description (optional)</label>
            <textarea
              id="session-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this session about?"
              maxLength={2000}
              rows={3}
              disabled={submitting}
              data-testid="session-desc-input"
            />
          </div>
          {error && <div className="error-text">{error}</div>}
          <div className="modal-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={submitting}
              data-testid="cancel-session"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={submitting || !name.trim()}
              data-testid="create-session-btn"
            >
              {submitting ? "Creating…" : "Create Session"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}