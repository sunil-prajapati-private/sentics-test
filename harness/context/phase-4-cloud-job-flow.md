# Phase 4 context

Cloud job creation now validates robot capabilities, writes a pending job and durable outbox record, and returns the pending projection. Status ingestion accepts only on-prem/site-matching envelopes, applies legal transitions, deduplicates message IDs, and publishes persisted projections to an SSE subscriber queue. API routes are defined in `cloud/app/main.py`; pure service logic is in `cloud/app/service.py` for dependency-free tests.

Verification: `python3 -m unittest discover -s tests -v` — 12 tests passed. FastAPI runtime checks are pending dependency installation.
