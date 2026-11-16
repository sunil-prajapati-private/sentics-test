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

- Date/phase: 2026-11-16 / Phase 7
- Files changed: added `README.md` with repository layout, initialization, Compose usage, verification commands, reliability/safety boundaries, demo flow, and current limitations.
- Verification: `./scripts/dev/doctor.sh` found Python 3.14.6 and Node v26.5.0/npm 11.17.0; `python3 -m unittest discover -s tests -v` passed (22 tests); `python3 -m compileall cloud onprem shared tests` passed; `git diff --check` passed.
- Browser smoke check: Chrome opened `file:///Users/sunilprajapati/Desktop/sentics-test/README.md` and visibly rendered the generated README content.
- Initialization/runtime limits: `./scripts/dev/setup.sh` created `.venv` but dependency installation could not resolve `pypi.org`; FastAPI is therefore unavailable for a live API check. Docker is missing, so Compose/Mosquitto integration cannot run. `npm install --no-audit --no-fund` was started but could not complete with the available network; frontend build was not claimed.
- Phase 7 status: documentation baseline and deterministic checks complete; live service, Compose, and frontend runtime evidence remain pending host dependency/network availability.

- Runtime/code review follow-up: added `harness/code_review/phase7-runtime-review.md` with prioritized findings. P0 findings are the missing `CloudStore` import in `cloud/app/main.py` and missing `shared/` package in both Python images; P1 findings include unwired MQTT runtime paths and the frontend nginx/Compose port mismatch.
- Follow-up verification: the 22-test suite, Python compilation, and `git diff --check` passed again. `docker compose config` could not run because Docker is not installed. `npx playwright --version` could not complete because the package was unavailable without network access. Chrome permissions were available for a local README smoke check, but no application runtime was available to test.
- Test warning: the passing suite emitted `ResourceWarning` messages for unclosed SQLite connections in `onprem/app/execution.py:40`; this is recorded as a cleanup concern, not a test failure.

- Phase 7 fixes: removed the invalid duplicate `CloudStore` construction from `cloud/app/main.py`; changed cloud and on-prem Docker builds to use repository-root context and copy `shared/`; corrected frontend publication to `5173:80` for nginx.
- Architecture review: added `harness/code_review/architecture-review.md`. It confirms the intended ownership boundary but records remaining runtime gaps: no MQTT lifecycle wiring, default in-memory service stores, unreachable on-prem scheduler/safety handlers, anonymous MQTT, and a static frontend.
- Post-fix checks: unit tests 22/22 passed; Python compilation passed; YAML parsing and Docker build-input path checks passed; Docker image build, Compose logs, and Playwright application tests remain blocked by missing Docker and unavailable package-network access.
- README follow-up: added a manual application/server guide covering Compose startup, per-service health checks, browser inspection, valid and invalid job requests, SSE verification, offline/safety scenarios, log capture, and shutdown. It explicitly distinguishes current HTTP-skeleton behavior from flows that still require MQTT/UI runtime wiring.
