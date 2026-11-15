# Phase 6 context

Offline recovery persists queue state and reconstructs queued work on scheduler startup. A persisted running job is marked failed with `restart_recovery_ambiguous` to avoid duplicate simulated execution after a crash. Duplicate command IDs remain ignored. Safety state is persisted per cell; person-entered events block starts and emit a pause for an active job, while person-left emits clearance/resume and repeated events are idempotent.

Verification: `python3 -m unittest discover -s tests -v` — 22 tests passed. Docker/Mosquitto and browser checks remain unavailable.
