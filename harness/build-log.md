# Build log

- Date/phase: 2026-11-15 / Phase 0
- Preflight: `pwd`; `git status --short`; `git diff --check`; `rg --files`; tool versions. Repository was empty and not a Git worktree; Python 3.15.0 and Codex 0.169.0-alpha.11.1 were available; Node, Docker, pytest, and ruff were unavailable.
- Files changed: root guidance, goals/plans/prompts, docs, commands, and harness artifacts. Requested `.agents/skills/` files could not be created because `.agents` is read-only in this environment.
- Checks: documentation consistency by inspection; no application tests applicable.
- Skipped: Git diff checks (no repository), Compose validation (no Compose), Markdown linter (not installed).
- Decisions: MQTT-only boundary, on-prem safety authority, durable application deduplication, simulated exactly-once boundary.
- Risks: implementation and runtime behavior are not yet verified; assessment PDF was unavailable.

- Phase 1: created service skeleton, Compose file, frontend scaffold, environment files, Makefile, setup/doctor scripts, README, and development-environment documentation.
- Phase 1 checks: Python AST and shell syntax passed. Docker Compose validation skipped because Docker is unavailable. Dependency installation and frontend build were not run because host tooling/network prerequisites are unavailable.

- Phase 1: created service skeleton, Compose file, frontend scaffold, environment files, Makefile, setup/doctor scripts, README, and development-environment documentation.
- Phase 1 checks: Python AST and shell syntax passed. Docker Compose validation skipped because Docker is unavailable. Dependency installation and frontend build were not run because host tooling/network prerequisites are unavailable.

- Phase 2: added shared contracts, transition guards, capability validation, separate cloud/on-prem SQLite schemas, enrollment persistence, outbox/inbox/event tables, execution claims, and unit tests.
- Phase 2 verification: `python3 -m unittest discover -s tests -v` passed (5 tests).
- Phase 2 skipped: pytest/ruff (not installed), Docker/MQTT integration (Docker unavailable), frontend checks (Node unavailable).

- Phase 3: added canonical MQTT topic helpers, envelope encode/decode validation, deterministic in-memory broker, enrollment coordinator, optional paho-mqtt dependencies, and MQTT/enrollment tests.
- Phase 3 verification: `python3 -m unittest discover -s tests -v` passed (9 tests).
- Phase 3 skipped: live broker/reconnect test and paho installation because Docker and network tooling are unavailable.

- Phase 4: added cloud job service logic, durable pending jobs and outbox records, API endpoint definitions, status ingestion with authorization/transition checks, and SSE update stream.
- Phase 4 verification: `python3 -m unittest discover -s tests -v` passed (12 tests).
- Phase 4 skipped: FastAPI runtime/API client checks because dependencies are not installed; live MQTT publication and frontend integration remain later work.

- Phase 5: added on-prem scheduler, explicit enrollment enforcement, durable queue insertion, one active execution per robot, concurrent independent robots, deterministic failure modes, and status event generation.
- Phase 5 verification: `python3 -m unittest discover -s tests -v` passed (16 tests).
- Phase 5 skipped: real MQTT/on-prem process integration and timing-based simulation checks; Docker and runtime dependencies remain unavailable.

- Phase 6: added durable queued-job reconstruction, safe restart handling for ambiguous running executions, duplicate replay protection, on-prem cell occupancy persistence, safety pause/resume, unsafe-cell start blocking, and deterministic offline/safety demo scripts.
- Phase 6 verification: `python3 -m unittest discover -s tests -v` passed (22 tests); Python compilation passed.
- Phase 6 skipped: Compose/Mosquitto integration and browser recording because Docker and Node are unavailable.
