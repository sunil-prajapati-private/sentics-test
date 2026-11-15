# Phase 2 context

Implemented shared envelope and domain rules, explicit robot capability validation, legal job transitions including operational pause, and separate SQLite stores. Cloud status history deduplicates message IDs; on-prem commands and execution claims are unique. Enrollment is persisted on-prem and cloud-side enrollment tables are defined. MQTT transport and enrollment exchange remain Phase 3.

Verification: `python3 -m unittest discover -s tests -v` — 5 tests passed. Runtime integration is pending unavailable Docker/MQTT tooling.
