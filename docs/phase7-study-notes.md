# Remote Robot Cell: Phase 7 study notes

## What the take-home PDF requires about failures

The PDF says that a simulated job takes a few seconds and **can sometimes fail**. It does not prescribe a particular failure cause, probability, API field, or implementation technique.

This project makes that requirement deterministic for demonstrations:

- `failure_mode=always_fail` makes the simulated execution finish as `failed` with reason `deterministic_failure`.
- `failure_mode=timeout` exercises one bounded retry and then finishes as `failed` if the retry is exhausted.
- Stopping the on-prem service is a separate offline-recovery test. It leaves cloud jobs pending and verifies replay after restart; it is not the same as an execution failure.

This is an explicit simulation assumption because the take-home has no physical robot, ROS, KUKA controller, or camera.

## How to trigger the failure simulation

In the operator UI, choose **Always fail** or **Timeout then retry** under **Failure simulation**, then submit a valid job.

The equivalent API request is:

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{"robot_id":"robot-1","source_station":"A","destination_station":"B","failure_mode":"always_fail"}'
```

## Services

| Service | What to study | Where it is used |
| --- | --- | --- |
| Cloud API | Request validation, job persistence, MQTT outbox, status projection, SSE | `cloud/app/main.py`, `cloud/app/service.py` |
| React frontend | State, forms, fetch, SSE, rendering, operator actions | `frontend/src/main.tsx` |
| On-prem service | Enrollment, queueing, execution, safety authority, MQTT consumer | `onprem/app/main.py`, `onprem/app/execution.py`, `onprem/app/safety.py` |
| Mosquitto | MQTT broker, topics, QoS 1, retained state, persistence | `docker-compose.yml`, `infra/mosquitto/mosquitto.conf` |
| SQLite | Durable jobs, queues, deduplication, execution claims, outboxes | `cloud/app/persistence.py`, `onprem/app/persistence.py` |
| Docker Compose | Local service network, health checks, volumes, startup ordering | `docker-compose.yml` |

## Authentication study note

Authentication is an added project security layer, not a take-home PDF requirement. MongoDB stores identity records, the setup seeder creates two active demonstration users, and the cloud issues an HTTP-only JWT cookie after login. The React login screen calls `/auth/login`; the backend enforces the cookie on robot-control APIs. There is no public signup route. Study `cloud/app/auth.py`, `cloud/app/seed.py`, `cloud/app/main.py`, and the `/auth/` proxy in `frontend/nginx.conf`.

## Libraries and concepts

| Library or tool | Study this | Project role |
| --- | --- | --- |
| Python | Threads, exceptions, dataclasses, environment variables | On-prem worker and shared contracts |
| FastAPI | Routes, request models, startup/shutdown lifecycle, streaming responses | Cloud and on-prem HTTP APIs |
| Pydantic | JSON request validation and typed models | Job and safety requests |
| Uvicorn | ASGI server process and container command | Runs both Python services |
| Paho MQTT | Client IDs, subscriptions, QoS, persistent sessions, reconnects | Cloud/on-prem transport |
| React | Components, hooks, controlled forms, event handlers | Operator console |
| TypeScript | Types, strict compiler checks, API response shapes | Frontend safety and build checks |
| Vite | Development server, proxy, production bundling | Frontend development/build |
| Nginx | Static assets, API proxying, SSE buffering/timeouts | Production frontend container |
| SQLite | Tables, primary keys, unique constraints, transactions | Durable local state |
| Playwright | Browser automation and assertions | UI smoke test |
| unittest | Focused deterministic unit tests | Contract, queue, safety, and recovery tests |
| Docker | Images, volumes, networks, health checks | Reproducible local runtime |

## Suggested study order

1. Read `docs/architecture.md` to understand ownership and the MQTT-only boundary.
2. Trace one job from `POST /api/jobs` to the cloud outbox.
3. Follow the MQTT command into `Runtime.on_message` and `RobotScheduler.receive`.
4. Read `worker_loop` and `RobotScheduler.finish` to see success and deterministic failure.
5. Read `SafetyController` and then the robot-state projection path.
6. Run the Python tests, then the browser test, then the Compose manual flow in `README.md`.

## Important boundary

The system guarantees exactly-once **simulated application effect** through durable IDs, deduplication, and execution claims. It cannot guarantee exactly-once physical robot motion because there is no physical controller in this take-home.
