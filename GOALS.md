# Goals

## Purpose
Deliver a reliable, fully local simulation of one customer site with two enrolled robots, cloud UI/API, on-prem authority, MQTT messaging, durable recovery, and demonstrable safety behavior within a 6–8 hour assessment.

## Required outcomes
Job submission, validation, per-robot queues, simulated execution/failure, live status, enrollment, restart recovery, duplicate safety, safety pause/resume, persistence, deterministic demos, and clear documentation.

## Success conditions
Both robots complete valid jobs; invalid capability/enrollment requests are rejected; offline jobs remain pending and recover once; duplicate delivery cannot execute twice; person-entered pauses the affected cell and person-left resumes safely; history survives restart; all claims have tests or recorded demo evidence.

## Non-goals
Physical robotics, ROS/KUKA integration, cameras, 3D simulation, cloud hosting, multi-site tenancy, and production-grade identity are out of scope.

## Constraints and expectations
FastAPI cloud, React UI, separate Python on-prem, MQTT/Mosquitto, local Docker Compose, separate persistence, on-prem safety authority, application-level idempotency, deterministic failure injection, and no direct cloud/on-prem HTTP.

## Requirement matrix
| Requirement | Planned capability | Verification | Evidence |
|---|---|---|---|
| Local stack | Compose services and volumes | compose config/smoke | README recording |
| MQTT-only boundary | Topics/envelope, no HTTP path | architecture review/integration | diagram |
| Two robots/capabilities | registry and validation | API/integration tests | UI recording |
| Job lifecycle | durable state machines | unit/integration tests | status history |
| Live UI | WebSocket/SSE projection | browser/e2e check | recording |
| Enrollment | MQTT enrollment handshake | enrollment test | contract docs |
| Offline recovery | outbox/inbox and replay | restart scenario | recording |
| Exactly-once simulation | unique execution claim | duplicate test | README boundary |
| Safety | on-prem cell state machine | safety tests | recording |
| Persistence | separate SQLite stores | restart test | evidence table |
| Deterministic simulation | scripts/failure mode | repeatable demo | demo script |

Known unknowns: final framework choices, authentication depth, and exact UI styling; confirm during Phase 1 without changing boundaries.
