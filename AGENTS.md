# Remote Robot Cell repository guidance

## Purpose
This is a local Remote Robot Cell take-home project, evaluated on reliable behavior, clear architecture, and explainable trade-offs.

## Scope and authority
- Cloud: FastAPI plus React; on-prem: a separate Python service.
- MQTT is the only cloud-to-on-prem path. There is no direct HTTP path or shared database.
- No physical robot, ROS, KUKA, camera, or cloud deployment is required.
- Cloud requests jobs and displays state. On-prem owns acceptance, rejection, queues, execution, safety pause/resume, and robot state.
- Safety is authoritative on-prem; cloud cannot directly control or resume a robot. On-prem reports are authoritative in cloud projections.

## Reliability and safety invariants
- Commands/events have stable identifiers and a common envelope (schema version, message ID, event type, source, site, job, correlation ID, occurred-at, payload as applicable).
- Durable persistence, idempotent handlers, uniqueness/deduplication, and monotonic transitions are required. MQTT QoS alone is not exactly-once execution.
- The simulated exactly-once boundary and crash recovery policy must be documented.
- A person in a cell pauses that cell on-prem immediately; cloud outage cannot disable this. New work cannot start in an unsafe cell. Safety events are idempotent.

## Workflow
Read only relevant files after a concise preflight. Work on one human-approved phase at a time; do not start the next phase automatically. Preserve user changes. Do not commit, push, deploy, write externally, or change credentials unless explicitly requested. Run relevant checks and report exact commands, output, and skipped checks. Never claim an unobserved pass.

## Review
Order findings P0–P3. Each finding includes severity, file/line or symbol, problem, impact, evidence, suggested fix, and invariant. Human review covers architecture, API compatibility, safety, and release; deterministic tools cover formatting, linting, typing, tests, and schemas.

## Context economy
Skills are narrow and short; detailed references belong in docs and scripts. Load documents progressively.
