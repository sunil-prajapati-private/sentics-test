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
cloud/       FastAPI service and cloud SQLite persistence
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

When the required tools are installed, also run:

```bash
docker compose config
cd frontend && npm install && npm run build
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
- Duplicate command and status-message protection.
- Queue reconstruction after restart.
- Safe handling of an ambiguous persisted running job using
  `restart_recovery_ambiguous`.
- Persisted per-cell occupancy and on-prem safety pause/resume behavior.

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

At the current repository state, the frontend is still a static scaffold. It
does not yet submit jobs or consume the cloud event stream, so a browser check
can verify only page loading until the UI integration is completed.

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

The last four steps require the on-prem MQTT runtime and UI controls to be
wired. They are not currently available through the running HTTP skeleton.

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
The repository currently has deterministic Python tests for Phases 2–6. Docker,
Mosquitto integration, and browser recording depend on host tooling and must be
verified separately. The frontend source is still a minimal operator UI
scaffold, so it should not be presented as a complete live dashboard.

## Project phases

The human-gated roadmap is in [PLANS.md](PLANS.md). Phase 7 is documentation
and review: README, architecture and contract documentation, trade-offs,
recording instructions, code review, security review, and final evidence. Stop
at human review after those artifacts are complete.
