# Human-gated implementation roadmap

Each phase stops after its acceptance criteria and requires explicit approval before the next phase.

## Phase 0 — Foundation
Purpose: this repository operating system, requirements, architecture, contracts, skills, commands, and harness. Dependencies: none. Non-goal: application code. Verify Markdown consistency and repository checks. Stop when bootstrap artifacts are reviewed.

## Phase 1 — Minimal service skeleton
Purpose: cloud FastAPI, React, on-prem Python, broker, Compose, health checks. Depends on Phase 0. Likely files: cloud/, frontend/, onprem/, infra/, compose files. Acceptance: local services start and health checks respond. Non-goal: feature completeness. Verify compose config and smoke test; evidence: logs. Stop after skeleton review.

## Phase 2 — Contracts, persistence, enrollment
Implement envelope/topics, separate SQLite schemas, enrollment, durable outbox/inbox, uniqueness and deduplication. Depends on Phase 1. Verify schema/unit tests and enrollment flow. Stop before job UI.

## Phase 3 — Cloud jobs and live status
Implement submission/pending state, MQTT publication, ingestion, SSE/WebSocket, job list and robot projection. Depends on Phase 2. Verify API and stream tests. Stop before scheduler.

## Phase 4 — On-prem scheduling and robots
Implement capability validation, per-robot serialized queues, simulation, deterministic failures, and status events. Depends on Phase 3. Verify worker and transition tests. Stop before recovery/safety.

## Phase 5 — Offline recovery and safety
Implement pending replay, broker persistence, startup recovery, simulated person events, pause/resume, and recovery tests. Depends on Phase 4. Verify duplicate, restart, and safety scenarios. Stop before demo polish.

## Phase 6 — Verification and demo automation
Add unit/integration/Compose/e2e checks and scripts for happy path, offline, duplicate, and safety demonstrations. Depends on Phase 5. Stop when evidence is repeatable.

## Phase 7 — Documentation and review
Update README, diagrams, contracts, trade-offs, recording script; perform code/security review. Depends on Phase 6. Stop at final human review.
