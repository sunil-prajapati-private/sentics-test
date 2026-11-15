# Phase 5 context

`onprem/app/execution.py` now handles validated job commands only for approved enrollments, records inbox deduplication, queues jobs per robot, enforces one active job per robot, permits Robot 1 and Robot 2 concurrency, claims durable executions, and emits received/queued/running/done/failed/rejected events. `always_fail` and `fail_once` are deterministic failure controls; the current scheduler treats both as a controlled failure outcome.

Verification: `python3 -m unittest discover -s tests -v` — 16 tests passed. Runtime MQTT integration and real-time duration simulation remain unverified.
