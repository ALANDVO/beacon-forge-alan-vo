# Changelog

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## [1.0.0] — 2026-10-17

### Added
- Beacon Forge: FastAPI backend with session goal lifecycle domain engine.
- Session management: create sessions representing AI coding agent sessions.
- Goal management: create goals with optional token budgets, track lifecycle
  status (pending → running → completed | failed) with deterministic state
  machine enforcement.
- Event-sourced activity timeline with snapshot compaction engine, directly
  addressing unbounded event-log growth (opencode issue #33356).
- Token budget enforcement: goal completion rejected when consumed tokens
  exceed budget + tolerance.
- REST API: session CRUD, goal CRUD, goal status transitions, event append,
  compacted timeline retrieval, with pagination and filtering.
- SQLite persistence via SQLAlchemy with UTC timestamps and audit fields.
- React + TypeScript frontend with typed API client and goal dashboard showing
  session list, goal creation, status transitions, and activity timeline.
- Docker backend/frontend images (nonroot), docker-compose with Keycloak and
  persistent volumes.
- CI workflow: backend pytest, frontend npm build + test, Docker builds.
- Full README with install/run/test steps, architecture diagram, AI/ML
  evaluation section, and security limitations.