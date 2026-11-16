# Remote Robot Cell

This repository is a local simulation of a remote robot cell. A cloud FastAPI
service accepts jobs and exposes projections, a React frontend is intended for
operator visibility, and a separate on-prem Python service owns enrollment,
queues, execution, robot state, and safety decisions. MQTT is the only
cloud-to-on-prem boundary; the services do not share a database or call each
other over HTTP.

The project is designed for a local assessment. It does not require a physical
robot, ROS, KUKA hardware, camera, cloud deployment, or production identity
system.

## Repository layout

```text
cloud/       FastAPI service, cloud operational persistence, and Mongo identity store
frontend/    React/Vite operator UI scaffold
onprem/      On-prem service, scheduler, persistence, and safety controller
shared/      Envelope, MQTT topic, capability, and state-transition contracts
infra/       Mosquitto configuration
scripts/     Development helpers and deterministic demo scripts
tests/       Phase 2–6 Python unit tests
docs/        Architecture, MQTT contract, requirements, and test guidance
harness/     Phase context, build evidence, and review artifacts
```

## Prerequisites

The intended local stack uses:

- Python 3.11+ (the current environment uses Python 3.14.6)
- Node.js and npm for the frontend
- Docker and Docker Compose for Mosquitto and service containers
- MongoDB is started by Compose for identity users; operational job history remains in separate cloud/on-prem SQLite stores to preserve the PDF's local persistence and MQTT ownership boundaries.

Check the local toolchain with:

```bash
./scripts/dev/doctor.sh
```

## Initialize the Python environment

The setup script creates `.venv` and installs the cloud and on-prem Python
requirements:

```bash
./scripts/dev/setup.sh
source .venv/bin/activate
```

The script needs package-install network access. If installation is not
available, the standard-library unit tests can still be run with `python3`.

## Start the local stack

Copy the example configuration if you want a local environment file:

```bash
cp .env.example .env
docker compose up --build
```

Services are intended to be available at:

- Frontend: `http://localhost:5173`
- Cloud API: `http://localhost:8000`
- On-prem health endpoint: `http://localhost:8001/healthz`
- MQTT broker: `localhost:1883`

Useful Compose commands:

```bash
docker compose ps
docker compose logs -f
docker compose down
```

The current repository contains health endpoints and service scaffolding, while
the full live MQTT and browser flow still requires the Docker runtime and a
running frontend/API stack.

## Test and validation commands

Run the deterministic Python suite:

```bash
python3 -m unittest discover -s tests -v
```

Run Python compilation and whitespace checks:

```bash
python3 -m compileall cloud onprem shared tests
git diff --check
```

Install the HTTP test-client dependency and run the local runtime smoke check:

```bash
./.venv/bin/pip install -r test-requirements.txt
PYTHONPATH=. .venv/bin/python scripts/test/runtime-smoke.py
```

When the required tools are installed, also run:

```bash
docker compose config
cd frontend && npm install && npm run build
```

For the browser smoke test, start the stack first and run from `frontend/`:

```bash
npm install
npx playwright install chromium
npm run test:e2e
```

The Phase 6 deterministic demonstrations are:

```bash
./scripts/demo/phase6-offline.sh
./scripts/demo/phase6-safety.sh
```

## Implemented behavior

- Capability validation for two simulated robots and their stations.
- Durable cloud jobs and outbox records.
- Separate cloud and on-prem SQLite schemas.
- MQTT envelope and canonical topic helpers.
- Enrollment persistence and on-prem enrollment enforcement.
- Per-robot serialized queues with independent robot execution.
- Deterministic failure injection.
- `JOB_DURATION_SECONDS` controls simulated execution length (default `3`); `failure_mode=timeout` exercises one bounded retry, while `always_fail` produces a deterministic failure.
- Duplicate command and status-message protection.
- Queue reconstruction after restart.
- Safe handling of an ambiguous persisted running job using
  `restart_recovery_ambiguous`.
- Persisted per-cell occupancy and on-prem safety pause/resume behavior.
- Cloud-projected robot state (`idle`, `busy`, `paused`) and heartbeat-based online status.
- MQTT-routed safety simulation, queued-job cancellation, configurable execution duration, and bounded timeout retry.

## Reliability and safety boundary

MQTT delivery is treated as at-least-once. Stable message IDs, persisted inbox
records, unique execution claims, and monotonic state transitions make replay
safe in the simulated state machine. This provides exactly-once simulated
application effect for the persisted execution record; it does not provide
physical exactly-once robot motion.

On-prem is authoritative for safety. A person entering a cell blocks new work
and pauses active work in that cell even if the cloud is unavailable. The cloud
receives projections and cannot directly approve safety or resume a robot.

See [docs/architecture.md](docs/architecture.md) and
[docs/mqtt-contract.md](docs/mqtt-contract.md) for the detailed boundaries and
message contract.

## Authentication and seeded operators

Authentication is an added security layer; it is not specified by the take-home
PDF. The cloud API uses MongoDB for identity records and an HTTP-only JWT cookie
for sessions. Job submission, safety events, cancellation, job history, robot
projections, and SSE require an active session. Health checks remain public for
Compose health checks. There is no public signup endpoint.

`docker compose up --build` starts MongoDB and runs the idempotent `seed-users`
service. It creates these active local demonstration users:

| Username | Password | Role |
| --- | --- | --- |
| `operator1` | `operator1-password` | operator |
| `supervisor1` | `supervisor1-password` | supervisor |

Change the seed values before using this outside a local assessment. The seed
uses an upsert, so rerunning setup does not create duplicate users. User records
have an `active` flag and login rejects inactive users; activation is an
administrative database operation rather than public signup.

The browser opens at `http://localhost:5173`, shows the login screen, and keeps
the session in an HTTP-only cookie. Direct API clients must first call
`POST /auth/login` and retain the returned cookie.

The login form intentionally does not pre-fill a username or password. Use the
seeded values above manually when testing locally.

## Demonstration flow

The intended recording sequence is documented in
[docs/testing-and-demo.md](docs/testing-and-demo.md). It covers:

1. Happy-path jobs for both robots.
2. Invalid capability or enrollment requests.
3. Cloud jobs queued while on-prem is offline.
4. Restart replay and duplicate delivery.
5. Person-entered pause, unsafe-cell start blocking, and safe resume.

Capture service logs, API responses, status history, and the UI state for each
scenario. Do not describe a browser or Compose result as passed unless it was
observed in the current environment.

## Manual application and server test guide

This section describes the intended operator workflow when Docker is available.
Run commands from the repository root.

### 1. Start all servers

```bash
docker compose up --build -d
docker compose ps
```

Expected services:

| Service | URL or address | Purpose |
|---|---|---|
| Frontend | `http://localhost:5173` | Operator browser interface |
| Cloud API | `http://localhost:8000` | Jobs, robots, and event stream |
| On-prem API | `http://localhost:8001` | On-prem health and diagnostics |
| MQTT | `localhost:1883` | Cloud/on-prem transport |

Watch startup logs in a second terminal:

```bash
docker compose logs -f mqtt cloud onprem frontend
```

The logs should show each service starting without import errors, connection
loops, or repeated health-check failures.

### 2. Check every server manually

```bash
curl -i http://localhost:8000/healthz
curl -i http://localhost:8001/healthz
curl -i http://localhost:8001/diagnostics
curl -i http://localhost:8000/api/robots
curl -i http://localhost:8000/api/jobs
```

Expected results:

- Cloud `/healthz` returns HTTP 200 and `{"service":"cloud"}`.
- On-prem `/healthz` returns HTTP 200 and `{"service":"onprem"}`.
- On-prem diagnostics returns HTTP 200.
- Robot and job endpoints return JSON arrays.
- `docker compose ps` shows the services as running or healthy.

### 3. Open and inspect the application

Open `http://localhost:5173` in Chrome or another browser. Confirm that:

1. The page loads without a blank screen.
2. The browser console has no JavaScript or asset errors.
3. The Network panel shows frontend assets loading successfully.
4. The application displays the expected robot/job view once the UI flow is
   implemented.

The frontend submits jobs and safety simulation events through the cloud API,
listens to the SSE event stream, and shows enrollment, robot-state, online, and
job projections. The browser check should therefore cover page rendering and
the actions below. The browser never calls the on-prem service directly.

### 4. Submit a valid cloud job

Use the API directly while observing the browser and service logs:

```bash
curl -i -X POST http://localhost:8000/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{"robot_id":"robot-1","source_station":"A","destination_station":"B"}'
```

Expected response:

- HTTP 202.
- A JSON job with a `job_id` and `status` set to `pending`.
- A corresponding cloud outbox record in the service logs or persistence
  inspection.

Then retrieve the job:

```bash
curl -s http://localhost:8000/api/jobs/<job_id>
```

### 5. Verify invalid requests are rejected

```bash
curl -i -X POST http://localhost:8000/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{"robot_id":"robot-1","source_station":"A","destination_station":"E"}'
```

Expected result: HTTP 422 with a capability or route validation error. No valid
execution should be created.

### 6. Verify live events

Open an event stream in a terminal:

```bash
curl -N http://localhost:8000/api/events
```

Submit another valid job and confirm that the stream emits `data:` records. A
browser Network panel can inspect the same stream when the frontend subscribes
to it.

### 7. Verify offline recovery and safety

Use the deterministic checks first:

```bash
./scripts/demo/phase6-offline.sh
./scripts/demo/phase6-safety.sh
```

For the full Compose demonstration, capture these steps and expected results:

1. Stop on-prem with `docker compose stop onprem`.
2. Submit a cloud job and confirm it remains pending.
3. Start on-prem with `docker compose start onprem`.
4. Confirm replay and completion in logs and job status.
5. Replay the same command ID and confirm there is no second execution.
6. Send a person-entered safety event for a cell.
7. Confirm active work pauses and new work cannot start in that cell.
8. Send person-left and confirm safe resume.

The Compose runtime now wires these events through the on-prem controller and
publishes job status projections back to the cloud. Physical robot motion is
still simulated.

### 8. Stop the servers and preserve evidence

```bash
docker compose logs --no-color > /tmp/remote-robot-cell-compose.log
docker compose down
```

Keep the log file, curl responses, browser screenshots, and test output together
when recording a pass/fail result. A service that starts but does not process
MQTT commands is only a health-check pass, not an end-to-end pass.

## Current verification status

The build evidence is maintained in [harness/build-log.md](harness/build-log.md).
The repository has deterministic Python tests, a FastAPI runtime smoke path,
frontend build/lint and Playwright checks, and a verified Docker/Mosquitto
Compose run covering both-robot jobs, offline replay, safety pause/resume,
heartbeats, cancellation, and timeout retry. A screen recording still needs to
be captured separately for the take-home submission.

## Project phases

Phase 7 covers documentation, runtime review, security review, test evidence,
and the final operator workflow.

## Additional engineering notes: how AI was used responsibly

AI assistance was used as a review and implementation accelerator, while the
repository kept human-checkable boundaries:

- Requirements were extracted from the take-home PDF before implementation;
  PDF requirements were kept separate from optional security enhancements.
- The MQTT-only cloud/on-prem boundary and on-prem safety authority were treated
  as invariants before changing code.
- Changes were kept incremental and reversible: shared contracts, persistence,
  runtime wiring, UI, authentication, and documentation were reviewed as
  separate concerns.
- Security decisions were made explicit. MongoDB stores identity records,
  passwords are PBKDF2 hashes, sessions use HTTP-only JWT cookies, and there is
  no public signup route. Sample credentials are documented but never embedded
  in the login form.
- Reliability claims were tested at the application boundary. Durable message
  IDs, deduplication, execution claims, monotonic transitions, and offline
  replay were verified rather than inferred from MQTT QoS alone.
- Deterministic tests cover contracts, queues, safety, restart recovery, and
  failure modes. Frontend lint, TypeScript build, Playwright, Compose config,
  Docker builds, live service health, login, and protected API access were also
  run where the environment supported them.
- Review artifacts record residual limits clearly: the system simulates robot
  motion, and a screen recording remains a manual submission step.
