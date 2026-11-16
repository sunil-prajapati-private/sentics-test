# Architecture-level review

Date: 2026-11-16

## Intended architecture

The documented model is sound at the boundary level: the cloud owns requests
and projections, on-prem owns enrollment, queues, execution, and safety, and
MQTT is the only cloud/on-prem path. The shared envelope and separate SQLite
schemas support that separation.

## Current implementation status and remaining gaps

### Runtime wiring now implements the declared boundary

The cloud now starts an MQTT client, publishes pending outbox rows, consumes
on-prem status/enrollment events, and exposes broker state in health output. The
on-prem service starts the MQTT client, enrollment publication, scheduler
worker, execution simulation, and safety event handling. The Compose runtime
path is now represented in the running services as well as unit tests.

### Persistence is file-backed in Compose and in-memory by default for tests

Compose supplies `/data/cloud.sqlite3` and `/data/onprem.sqlite3` on named
volumes. Local unit tests continue to use `:memory:` by default to remain
isolated. The Compose persistence path now survives service restarts.

### Exactly-once is connected at the simulated boundary

The on-prem MQTT consumer invokes the scheduler, which persists command IDs and
unique execution claims before simulated execution. A production controller
would still need transactional hardware acknowledgements for physical motion.

### Safety authority is correctly placed and operationally reachable

`SafetyController` blocks starts and records occupancy. The on-prem MQTT handler
and local simulator endpoint invoke `person_entered` and `person_left`; the UI
uses the proxied local endpoint and never grants cloud safety authority.

### Security boundary is incomplete

Mosquitto allows anonymous access and exposes the listener on all interfaces.
There is no service authentication or topic authorization. That is acceptable
for a local take-home simulation only if it is stated as a limitation; it is not
safe as a production deployment.

### UI is now a projection client

The React app calls `/api/jobs` and `/api/robots`, subscribes to `/api/events`,
submits jobs, displays status reasons, and exposes local safety simulation
controls. Browser testing now covers a real operator flow when Compose is up.

## Recommended implementation order

1. Keep the repository-root Docker contexts and startup import correction.
2. Run Compose and browser tests with Docker Desktop to verify the runtime path.
3. Add Playwright tests for health, job submission, duplicate replay, offline
   recovery, and safety pause/resume.
4. Add broker authentication and topic ACLs before treating the stack as more
   than a local simulation.

## Review conclusion

The corrected Docker packaging and cloud import remove the startup blockers.
The runtime path, file-backed Compose persistence, on-prem handlers, and
operator UI are now implemented. Remaining validation is host-dependent Docker
and browser execution; anonymous MQTT and simulated-only execution remain
intentional local-assessment limitations.
