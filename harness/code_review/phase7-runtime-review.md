# Phase 7 runtime and browser review

Date: 2026-11-16

## Validation attempted

- `./scripts/dev/doctor.sh`
- `docker compose config`
- `docker compose up --build`
- `docker compose ps`
- `docker compose logs`
- `python3 -m unittest discover -s tests -v`
- `python3 -m compileall cloud onprem shared tests`
- Chrome local-file smoke check for `README.md`
- Playwright CLI discovery with `npx playwright --version`

Docker is not installed in the current environment, so Compose startup, service
logs, container health checks, and live browser testing against the application
could not be executed. The Chrome smoke check only verified that the generated
README renders from the local filesystem; it did not verify the React app or API.

## Findings

### P0 — Cloud container could not import its application (fixed in working tree)

- Location: `cloud/app/main.py:10`
- Problem: the original code instantiated `CloudStore` without importing it.
- Fix applied: removed the second store construction and kept the single store
  imported from `.service`.
- Impact: importing `app.main:app` raises `NameError`, so the cloud container
  cannot start and its `/healthz` check cannot pass.
- Evidence: source inspection; the missing symbol is visible at line 10. A live
  import could not be run because FastAPI is not installed locally and Docker is
  unavailable.
- Suggested fix: import `CloudStore` from `.persistence`, or remove the second
  store construction and use the service store consistently. Add a container
  import/health smoke test.
- Invariant: every Compose service must start and expose its health endpoint.

### P0 — Python images omitted the shared contract package (fixed in working tree)

- Location: `cloud/Dockerfile:5`, `onprem/Dockerfile:5`
- Problem: each Docker build copied only its local `app` directory. Both apps
  import `shared.contracts`, but `shared/` was outside each build context.
- Fix applied: cloud and on-prem now use the repository root as build context,
  and each Dockerfile copies its app plus `shared/`.
- Impact: after the cloud `CloudStore` issue is fixed, both service images still
  fail with `ModuleNotFoundError: shared`.
- Evidence: Docker build contexts are `./cloud` and `./onprem` in
  `docker-compose.yml:14,25`; both Dockerfiles copy only `app`.
- Suggested fix: use a repository-root build context and copy `shared` into the
  image, or package/install the shared module as a dependency. Add a Docker
  build plus import smoke test.
- Invariant: cloud and on-prem must use the same versioned envelope and domain
  contracts.

### P1 — Compose did not run the implemented on-prem workflow (fixed in working tree)

- Location: `onprem/app/main.py:9-11`
- Problem: the original on-prem HTTP service exposed only health and skeleton
  diagnostics. No runtime handlers were started.
- Fix applied: the service now starts MQTT, enrollment publication, scheduler
  execution, persistent safety handling, diagnostics, and local safety-event
  simulation.
- Impact: a healthy container would still not process cloud commands, publish
  status, or demonstrate offline/safety behavior.
- Evidence: the process entrypoint contains only two routes; the scheduler and
  safety classes are not imported or started.
- Suggested fix: wire the runtime adapter and lifecycle startup/shutdown before
  claiming Compose end-to-end behavior.
- Invariant: on-prem owns acceptance, execution, queueing, and safety.

### P1 — Cloud API had no runtime MQTT publisher or consumer (fixed in working tree)

- Location: `cloud/app/main.py:29-38`, `cloud/app/service.py:5-16`
- Problem: the original job creation path only wrote an outbox row.
- Fix applied: cloud startup now connects paho MQTT, publishes pending outbox
  rows, and consumes status/enrollment events.
- Impact: jobs remain pending and live status cannot flow through the declared
  cloud/on-prem boundary.
- Evidence: no paho client, background task, or outbox loop exists in the cloud
  entrypoint.
- Suggested fix: implement durable outbox publication, inbound status handling,
  reconnect behavior, and lifecycle cleanup; then verify with broker logs and API
  assertions.
- Invariant: MQTT is the only cloud-to-on-prem path and durable records must
  survive reconnects.

### P1 — Compose frontend port did not match the image server (fixed in working tree)

- Location: `docker-compose.yml:36-39`, `frontend/Dockerfile:10`
- Problem: the frontend image uses nginx, which listens on port 80 by default,
  but Compose originally published `5173:5173`.
- Fix applied: Compose now publishes `5173:80`.
- Impact: the published frontend URL on port 5173 will not reach the nginx
  server.
- Suggested fix: publish `5173:80`, or configure nginx to listen on 5173 and add
  a health check. Verify with a browser request after the image starts.
- Invariant: documented local URLs must resolve to the running service.

### P2 — Safety state was not exposed through the running service (fixed in working tree)

- Location: `onprem/app/safety.py`, `onprem/app/main.py`
- Problem: the original safety controller existed only as a testable class.
- Fix applied: MQTT safety events and `/api/safety/events` now invoke the
  controller and persist occupancy.
- Impact: the safety invariant is covered by unit tests but cannot be exercised
  through the declared runtime path.
- Suggested fix: connect safety event ingestion to the on-prem process and emit
  durable status events.
- Invariant: a person in a cell must pause/block work on-prem immediately.

### P2 — Frontend was a Phase 1 placeholder (fixed in working tree)

- Location: `frontend/src/main.tsx:5-6`
- Problem: the original UI rendered only static text.
- Fix applied: the React console now submits jobs, consumes SSE projections,
  displays robots/jobs, and sends local safety simulation events through the
  on-prem proxy.
- Impact: browser testing cannot verify job submission, live status, enrollment,
  offline recovery, or safety reasons.
- Suggested fix: implement the operator flow and add Playwright tests once the
  runtime services are available.
- Invariant: the cloud UI must display authoritative on-prem projections.

## Static checks observed

- Python AST parsing passed.
- Existing unit suite passed: 22 tests.
- Python compilation passed.
- YAML parsing passed with Ruby's YAML parser; this is not a substitute for
  `docker compose config`.
- Docker, FastAPI runtime, npm install/build, Playwright CLI, Compose logs, and
  live application browser checks remain unverified due missing Docker and
  unavailable package-network access.
