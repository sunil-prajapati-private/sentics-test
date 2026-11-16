# Take-home PDF versus implementation review

Review date: 2026-11-16  
Source: `Downloads/Take_Home_Remote_Robot_Cell.pdf`  
Scope: read-only comparison of the supplied take-home instructions with the current repository.

## Instructions extracted from the PDF

The required system is a local Docker Compose simulation containing a cloud FastAPI service, React operator UI, a separate on-prem Python service, and a local Mosquitto broker. Cloud and on-prem must communicate through MQTT only; they must not share a database or call one another directly over HTTP. The scenario has one site and two robots: Robot 1 serves A/B/C in cell 1 and Robot 2 serves C/D/E in cell 2.

The required behavior is:

- The cloud UI submits jobs and displays live job transitions: pending, received, queued, running, done, failed, or rejected.
- On-prem owns enrollment, acceptance/rejection, per-robot serialization and queueing, simulated execution, failure, and all safety decisions.
- Robots are enrolled before jobs are accepted, and the enrollment/connection design is explained in the README.
- Jobs submitted while on-prem is offline remain pending and are processed exactly once after reconnect, without loss or duplicate execution.
- A person-entered event pauses the affected cell immediately; person-left permits safe resume. This must work independently of cloud availability, and the cloud must show the paused state and reason.
- Job history survives restart, and the repository provides a way to generate dummy events/messages.

The deliverables also require a README with run instructions, architecture diagram, MQTT topics and formats, design trade-offs, assumptions, and a screen recording showing both-robot execution, offline recovery, safety pause/resume, and a code walkthrough. Bonus items are heartbeats, queued-job cancellation, and timeout/retry.

## Requirement matrix

| PDF requirement | Assessment | Evidence |
| --- | --- | --- |
| Cloud FastAPI, React, separate on-prem service, MQTT contracts | Pass structurally | `cloud/`, `frontend/`, `onprem/`, `shared/`, Compose services, and `docs/mqtt-contract.md` |
| Two robots and station capabilities | Pass in scheduler/tests | `shared/contracts/capabilities.py`, `onprem/app/execution.py` |
| Cloud job lifecycle and live UI refresh | Partial | Cloud persists status and exposes SSE; the UI renders job status in `frontend/src/main.tsx:29-35,72`. Full broker-backed live flow is not verified in this host. |
| Enrollment before acceptance | Pass in application logic; runtime evidence pending | `onprem/app/main.py:140-142` publishes enrollment and `onprem/app/execution.py:24` rejects unenrolled robots. |
| Per-robot queue and one active job | Pass structurally | `onprem/app/execution.py:29-34` and worker loop at `onprem/app/main.py:144-163`. |
| Persistence across restart | Pass structurally | SQLite stores and named Compose volumes at `docker-compose.yml:17-19,31-34`. |
| Dummy event/message generation | Pass | README demo scripts and the safety API are documented. |
| Safety pause/resume independent of cloud | Partial | The controller is on-prem authoritative, but the browser calls on-prem HTTP directly through `frontend/src/main.tsx:53-58` and `frontend/nginx.conf:19-24`, which conflicts with the PDF's MQTT-only cloud/on-prem boundary. |
| Cloud shows current robot state idle/busy/paused | Missing | `frontend/src/main.tsx:6,73` displays enrollment and capabilities only. The on-prem `robot_state` table exists, but no runtime path updates or publishes it. |
| Offline recovery, exactly-once after reconnect | Partial/unverified | Durable application outboxes and deduplication exist, but the Paho clients do not configure persistent MQTT sessions (`onprem/app/main.py:125-132`, `cloud/app/main.py:87-94`). A Compose broker-backed outage/reconnect test has not run. |
| Screen recording and final end-to-end evidence | Missing | README describes the sequence at `README.md:158-171,291-315`, but no recording artifact exists and Docker Desktop is unavailable in this environment. |
| Bonus heartbeats/online status | Missing | Topic helpers/docs exist, but no runtime heartbeat publisher or UI online/offline field is wired. |
| Bonus queued cancellation | Missing | No cancel API or UI action was found. |
| Bonus timeout/retry | Missing | No timeout/retry policy is implemented; deterministic failure simulation is present. |

## Findings ordered by severity

### P1 — Direct browser-to-on-prem safety path violates the stated boundary

**Location:** `frontend/src/main.tsx:53-58`; `frontend/nginx.conf:19-24`; `frontend/vite.config.ts:8-11`.

**Problem:** The operator browser posts safety events directly to the on-prem HTTP service. The PDF says cloud and on-prem communicate only through MQTT and have no direct HTTP path. The safety decision remains on-prem, but this UI route is still a second cloud/on-prem control path and makes the architecture inconsistent with the required boundary.

**Suggested fix:** Route the simulation command through a cloud endpoint that publishes a safety command over MQTT, or provide a documented CLI/demo script for person-entered/left events and remove the browser's direct on-prem proxy. Keep the on-prem controller authoritative and reject unsafe transitions there.

**Invariant:** MQTT is the only cloud-to-on-prem path; cloud cannot directly control or resume a robot.

### P1 — Required current robot state is not projected to the UI

**Location:** `frontend/src/main.tsx:6,73`; `onprem/app/persistence.py:3`; `onprem/app/main.py:144-163`; `cloud/app/persistence.py:5,31-36`.

**Problem:** The UI shows robot ID, cell, stations, and enrollment state, but not idle, busy, or paused. Although on-prem has a `robot_state` table and topic helper, the worker and safety paths do not update/publish robot-state events, and the cloud store has no robot-state columns.

**Impact:** This misses a named must-have: the UI must show both robots' current state and the cloud must show a safety pause reason.

**Suggested fix:** Persist and publish state transitions for enrollment, idle, running, paused, and offline/unknown; consume them into the cloud robot projection and render state plus pause reason in the UI.

**Invariant:** On-prem robot/safety state is authoritative; cloud only displays a projection.

### P1 — Offline exactly-once is not demonstrated and MQTT session durability is incomplete

**Location:** `cloud/app/main.py:45-50,87-94`; `onprem/app/main.py:125-139`.

**Problem:** The application outboxes and message deduplication are useful, but both Paho clients use the default connection/session behavior. If the broker remains up while on-prem is down, a command published to a non-persistent session may not be available when on-prem reconnects. The claimed exactly-once application effect therefore still depends on an unverified delivery path.

**Suggested fix:** Configure persistent MQTT sessions and broker persistence, or keep pending commands publishable until an on-prem receipt/ack is durably observed. Add a real Compose test that stops on-prem, submits a job, restarts it, replays the command, and verifies one execution record.

**Invariant:** MQTT QoS is at-least-once; durable records and idempotent handlers must prevent lost or repeated simulated execution.

### P2 — Simulated execution is shorter than the requested “few seconds”

**Location:** `onprem/app/main.py:161-163`.

**Problem:** Each job currently receives a one-second deadline. That is still observable, but it is shorter than the PDF's “few seconds” simulation and makes queueing and pause demonstrations harder to observe.

**Suggested fix:** Use a documented configurable duration of roughly 2–3 seconds for demos and tests.

### P2 — Required submission evidence is incomplete

**Location:** `README.md:158-171,291-322`.

**Problem:** The README correctly describes the recording and manual verification sequence, but the required screen recording and live Compose/Mosquitto run have not been produced. `docker compose config` and local deterministic tests are not substitutes for the requested end-to-end evidence.

**Suggested fix:** Once Docker Desktop is available, run the complete sequence, save Compose logs, capture the browser and code walkthrough, and link the recording from the final repository/README. Add the GitHub repository link required by the PDF.

### P2 — Bonus operational features are not implemented

Heartbeats/online status, queued-job cancellation, and timeout/retry were not found. These are bonus items in the PDF and do not block the core submission, but should be listed explicitly as not implemented rather than implied by the topic documentation.

## Verification boundary

The repository's deterministic Python tests, compile check, frontend build/lint, runtime smoke script, Playwright UI test, Docker image builds, `docker compose config`, broker-backed Compose execution, offline replay, safety projection, cancellation, and timeout retry have now passed. The final screen recording remains unproduced.

## Post-review implementation update

The identified code gaps were addressed after this review:

- Safety simulation now uses the cloud API and MQTT command topic; the frontend no longer proxies to on-prem.
- On-prem publishes robot state and heartbeats; cloud persists state, reason, last-seen time, and online status for the UI.
- Cloud job commands remain replayable until a terminal on-prem status is observed, and persistent MQTT sessions are configured.
- Execution duration is configurable (`JOB_DURATION_SECONDS`, default three seconds), with bounded timeout retry (`JOB_MAX_RETRIES`).
- Queued jobs can be cancelled through `DELETE /api/jobs/{job_id}` and the UI.

The remaining submission deliverable is the screen recording. The full Compose run was subsequently completed after retrying Docker BuildKit with the required host access.

