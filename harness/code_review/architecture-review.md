# Architecture-level review

Date: 2026-11-16

## Intended architecture

The documented model is sound at the boundary level: the cloud owns requests
and projections, on-prem owns enrollment, queues, execution, and safety, and
MQTT is the only cloud/on-prem path. The shared envelope and separate SQLite
schemas support that separation.

## Current implementation gaps

### Runtime wiring does not yet implement the declared boundary

The cloud creates durable-looking outbox rows but has no MQTT publisher or
subscriber lifecycle. The on-prem service exposes only health and diagnostics;
the scheduler, safety controller, enrollment coordinator, and MQTT transport
are not started by the process. The architecture is therefore represented in
unit-test classes and documents, not in the running services.

### Persistence is not durable in the service processes

`CloudStore()` and `OnPremStore()` default to `:memory:`. A process restart
loses jobs, outbox records, inbox records, enrollment state, queues, and safety
state unless a caller explicitly supplies a file path. This conflicts with the
offline recovery and restart guarantees described in the requirements.

### Exactly-once is only partially connected

The on-prem scheduler has unique command and execution claims, which is the
right simulated boundary. However, because no runtime MQTT consumer invokes the
scheduler, those claims do not protect the real Compose flow yet. A production
adapter must persist the inbox/claim before executing and acknowledge replay
after the transaction commits.

### Safety authority is correctly placed but not operationally reachable

`SafetyController` blocks starts and records occupancy in tests. No on-prem
MQTT handler or API lifecycle calls `person_entered` or `person_left`, so a live
cell cannot currently receive the safety events described by the contract.

### Security boundary is incomplete

Mosquitto allows anonymous access and exposes the listener on all interfaces.
There is no service authentication or topic authorization. That is acceptable
for a local take-home simulation only if it is stated as a limitation; it is not
safe as a production deployment.

### UI is not yet a projection client

The React app does not call `/api/jobs`, `/api/robots`, or `/api/events`. It
cannot display authoritative on-prem status, pending/offline state, or safety
reasons. Browser testing must wait until the UI and runtime transport are wired.

## Recommended implementation order

1. Keep the fixed repository-root Docker contexts and startup import correction.
2. Add explicit file-backed paths for cloud and on-prem SQLite stores through
   environment variables and Compose volumes.
3. Implement a small MQTT adapter with reconnect, durable outbox publication,
   inbox deduplication, and clean startup/shutdown hooks.
4. Start the on-prem enrollment, scheduler, execution, and safety handlers from
   the service lifecycle.
5. Connect cloud status ingestion to the broker and publish projection updates.
6. Build the React job/robot/status view and add Playwright tests for health,
   job submission, duplicate replay, offline recovery, and safety pause/resume.
7. Add broker authentication and topic ACLs before treating the stack as more
   than a local simulation.

## Review conclusion

The corrected Docker packaging and cloud import remove two immediate startup
blockers. The remaining runtime and architecture gaps are larger than a
documentation-only Phase 7 change: the Compose stack still does not exercise
the full declared workflow until MQTT lifecycle wiring, file-backed persistence,
on-prem handlers, and the operator UI are implemented.
