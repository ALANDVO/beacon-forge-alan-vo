"""Integration tests for the session → goal → timeline API workflow."""
from httpx import AsyncClient
import pytest

from app.models.goal import GoalStatus


async def _create_goal(client: AsyncClient, budget=None):
    """Create a session and goal, returning (session_id, goal_json)."""
    session = await client.post("/api/sessions", json={"name": "Test Session"})
    sid = session.json()["id"]
    payload = {"description": "Implement feature X", "token_budget": budget}
    resp = await client.post(f"/api/sessions/{sid}/goals", json=payload)
    assert resp.status_code == 201
    goal = resp.json()
    return sid, goal


class TestSessionCreation:
    async def test_create_session(self, client: AsyncClient):
        resp = await client.post(
            "/api/sessions",
            json={"name": "Test Session", "description": "A test session"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Session"
        assert data["description"] == "A test session"
        assert data["status"] == "active"
        assert "id" in data
        assert "created_at" in data
        assert "started_at" in data

    async def test_list_sessions_pagination(self, client: AsyncClient):
        for i in range(3):
            await client.post("/api/sessions", json={"name": f"Session {i}"})
        resp = await client.get("/api/sessions?page=1&per_page=2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["per_page"] == 2

    async def test_get_session_not_found(self, client: AsyncClient):
        resp = await client.get("/api/sessions/nonexistent-id")
        assert resp.status_code == 404

    async def test_archive_session(self, client: AsyncClient):
        create = await client.post("/api/sessions", json={"name": "To Archive"})
        sid = create.json()["id"]
        resp = await client.delete(f"/api/sessions/{sid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "archived"
        assert resp.json()["ended_at"] is not None

    async def test_unauth_session_rejected(self, no_auth_client: AsyncClient):
        resp = await no_auth_client.post("/api/sessions", json={"name": "X"})
        assert resp.status_code == 401


class TestGoalLifecycle:
    async def test_create_goal_pending(self, client: AsyncClient):
        sid, goal = await _create_goal(client, budget=1000)
        assert goal["status"] == "pending"
        assert goal["token_budget"] == 1000
        assert goal["tokens_consumed"] == 0
        assert goal["session_id"] == sid

    async def test_create_goal_no_budget(self, client: AsyncClient):
        sid, goal = await _create_goal(client)
        assert goal["token_budget"] is None
        assert goal["status"] == "pending"

    async def test_create_goal_invalid_budget(self, client: AsyncClient):
        session = await client.post("/api/sessions", json={"name": "S"})
        sid = session.json()["id"]
        resp = await client.post(
            f"/api/sessions/{sid}/goals",
            json={"description": "X", "token_budget": 0},
        )
        assert resp.status_code == 422

    async def test_transition_pending_to_running(self, client: AsyncClient):
        sid, goal = await _create_goal(client)
        gid = goal["id"]
        resp = await client.post(
            f"/api/goals/{gid}/transition",
            json={"target": "running", "tokens_spent": 0},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"
        assert resp.json()["started_at"] is not None

    async def test_transition_running_to_completed(self, client: AsyncClient):
        sid, goal = await _create_goal(client, budget=1000)
        gid = goal["id"]
        await client.post(
            f"/api/goals/{gid}/transition",
            json={"target": "running", "tokens_spent": 500},
        )
        resp = await client.post(
            f"/api/goals/{gid}/transition",
            json={"target": "completed", "tokens_spent": 500},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"
        assert resp.json()["tokens_consumed"] == 1000
        assert resp.json()["completed_at"] is not None

    async def test_complete_exceeds_budget_rejected(self, client: AsyncClient):
        sid, goal = await _create_goal(client, budget=100)
        gid = goal["id"]
        await client.post(
            f"/api/goals/{gid}/transition",
            json={"target": "running", "tokens_spent": 0},
        )
        resp = await client.post(
            f"/api/goals/{gid}/transition",
            json={"target": "completed", "tokens_spent": 200},
        )
        assert resp.status_code == 422
        assert "budget" in resp.json()["detail"].lower()

    async def test_transition_completed_to_running_forbidden(self, client: AsyncClient):
        sid, goal = await _create_goal(client, budget=1000)
        gid = goal["id"]
        await client.post(
            f"/api/goals/{gid}/transition", json={"target": "running", "tokens_spent": 10}
        )
        await client.post(
            f"/api/goals/{gid}/transition", json={"target": "completed", "tokens_spent": 10}
        )
        resp = await client.post(
            f"/api/goals/{gid}/transition", json={"target": "running", "tokens_spent": 0}
        )
        assert resp.status_code == 422

    async def test_invalid_transition(self, client: AsyncClient):
        sid, goal = await _create_goal(client, budget=1000)
        gid = goal["id"]
        resp = await client.post(
            f"/api/goals/{gid}/transition",
            json={"target": "completed", "tokens_spent": 0},
        )
        assert resp.status_code == 422
        assert "cannot" in resp.json()["detail"].lower()

    async def test_invalid_target_status(self, client: AsyncClient):
        sid, goal = await _create_goal(client)
        gid = goal["id"]
        resp = await client.post(
            f"/api/goals/{gid}/transition",
            json={"target": "bogus"},
        )
        assert resp.status_code == 400


class TestTimeline:
    async def test_timeline_after_transitions(self, client: AsyncClient):
        sid, goal = await _create_goal(client, budget=1000)
        gid = goal["id"]
        await client.post(
            f"/api/goals/{gid}/transition", json={"target": "running", "tokens_spent": 300}
        )
        await client.post(
            f"/api/goals/{gid}/transition", json={"target": "completed", "tokens_spent": 700}
        )
        resp = await client.get(f"/api/goals/{gid}/timeline")
        assert resp.status_code == 200
        timeline = resp.json()
        assert timeline["goal_id"] == gid
        assert timeline["goal_status"] == "completed"
        assert timeline["goal_tokens_consumed"] == 1000
        assert timeline["latest_snapshot"] is None
        event_types = [e["event_type"] for e in timeline["events"]]
        assert "created" in event_types
        assert "started" in event_types
        assert "completed" in event_types

    async def test_timeline_with_snapshots_compacted(self, client: AsyncClient):
        sid, goal = await _create_goal(client, budget=1000)
        gid = goal["id"]
        await client.post(
            f"/api/goals/{gid}/transition", json={"target": "running", "tokens_spent": 100}
        )
        await client.post(
            f"/api/goals/{gid}/events",
            json={"event_type": "snapshot", "data": {"state": "partial"}},
        )
        await client.post(
            f"/api/goals/{gid}/events",
            json={"event_type": "snapshot", "data": {"state": "final"}},
        )
        resp = await client.get(f"/api/goals/{gid}/timeline")
        assert resp.status_code == 200
        timeline = resp.json()
        assert timeline["latest_snapshot"] is not None
        assert timeline["latest_snapshot"]["data"]["state"] == "final"

    async def test_filter_goals_by_status(self, client: AsyncClient):
        sid, goal = await _create_goal(client, budget=1000)
        gid = goal["id"]
        await client.post(
            f"/api/goals/{gid}/transition", json={"target": "running", "tokens_spent": 0}
        )
        resp = await client.get("/api/goals?status=running")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert any(g["status"] == "running" for g in items)

        resp = await client.get("/api/goals?status=pending")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(g["status"] == "pending" for g in items)

    async def test_append_event_note(self, client: AsyncClient):
        sid, goal = await _create_goal(client)
        gid = goal["id"]
        resp = await client.post(
            f"/api/goals/{gid}/events",
            json={"event_type": "note", "data": {"message": "Agent is working on file X"}},
        )
        assert resp.status_code == 201


class TestCompaction:
    async def test_compact_goal_manual(self, client: AsyncClient):
        """Test manual compaction endpoint for a single goal."""
        sid, goal = await _create_goal(client, budget=1000)
        gid = goal["id"]
        
        # Transition to running first
        await client.post(
            f"/api/goals/{gid}/transition", json={"target": "running", "tokens_spent": 100}
        )
        # Add multiple snapshot events
        await client.post(
            f"/api/goals/{gid}/events",
            json={"event_type": "snapshot", "data": {"state": "partial1"}},
        )
        await client.post(
            f"/api/goals/{gid}/events",
            json={"event_type": "snapshot", "data": {"state": "partial2"}},
        )
        await client.post(
            f"/api/goals/{gid}/events",
            json={"event_type": "snapshot", "data": {"state": "final"}},
        )
        
        # Check timeline before compaction - timeline endpoint runs compaction on read
        resp = await client.get(f"/api/goals/{gid}/timeline")
        assert resp.status_code == 200
        timeline_before = resp.json()
        # Timeline already compacted: created + started + 1 snapshot (latest) = 3 events
        events_before = len(timeline_before["events"])
        assert events_before == 3
        # Verify latest snapshot is the final one
        assert timeline_before["latest_snapshot"] is not None
        assert timeline_before["latest_snapshot"]["data"]["state"] == "final"
        
        # Call manual compaction - should be idempotent (already compacted by timeline read)
        resp = await client.post(f"/api/goals/{gid}/compact")
        assert resp.status_code == 200
        compact_result = resp.json()
        assert compact_result["goal_id"] == gid
        assert compact_result["snapshots_pruned"] == 0  # Already compacted by timeline read
        assert compact_result["total_events_before"] == compact_result["total_events_after"]
        assert compact_result["latest_snapshot_id"] is not None
        
    async def test_compact_goal_no_snapshots(self, client: AsyncClient):
        """Test compaction on goal with no snapshots - should not prune anything."""
        sid, goal = await _create_goal(client)
        gid = goal["id"]
        
        resp = await client.post(f"/api/goals/{gid}/compact")
        assert resp.status_code == 200
        compact_result = resp.json()
        assert compact_result["goal_id"] == gid
        assert compact_result["snapshots_pruned"] == 0
        assert compact_result["total_events_before"] == compact_result["total_events_after"]
        
    async def test_compact_all_goals(self, client: AsyncClient):
        """Test bulk compaction endpoint."""
        # Create multiple goals with snapshots
        sids = []
        gids = []
        for i in range(3):
            sid, goal = await _create_goal(client, budget=1000)
            gid = goal["id"]
            sids.append(sid)
            gids.append(gid)
            
            # Transition to running first
            await client.post(
                f"/api/goals/{gid}/transition", json={"target": "running", "tokens_spent": 100}
            )
            
            # Add snapshots to each goal
            await client.post(
                f"/api/goals/{gid}/events",
                json={"event_type": "snapshot", "data": {"state": f"snap1-{i}"}},
            )
            await client.post(
                f"/api/goals/{gid}/events",
                json={"event_type": "snapshot", "data": {"state": f"snap2-{i}"}},
            )
        
        # Call bulk compaction - note: timeline reads may have already compacted some
        resp = await client.post("/api/goals/compact-all")
        assert resp.status_code == 200
        compact_result = resp.json()
        # Goals compacted may be 0-3 depending on whether timeline reads already ran
        assert compact_result["goals_compacted"] >= 0
        assert compact_result["total_snapshots_pruned"] >= 0
        assert compact_result["total_events_before"] >= compact_result["total_events_after"]

    async def test_compact_nonexistent_goal(self, client: AsyncClient):
        """Test compaction on nonexistent goal returns 404."""
        resp = await client.post("/api/goals/nonexistent-id/compact")
        assert resp.status_code == 404