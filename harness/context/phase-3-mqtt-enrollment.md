# Phase 3 context

Canonical MQTT topics and envelope validation now live in `shared/contracts/mqtt.py`. A deterministic broker supports subscription and duplicate-delivery tests. Enrollment requests validate site, robot, cell, and non-empty capabilities before persisting approval in the on-prem store. The paho dependency is declared for the future runtime adapter; no network client is started in this phase.

Verification: `python3 -m unittest discover -s tests -v` — 9 tests passed. Live Mosquitto and reconnect verification is pending Docker availability.
