# ADR 0001: bootstrap and boundaries

Status: accepted for Phase 0. We establish FastAPI/React cloud, separate Python on-prem, MQTT-only inter-service communication, separate SQLite persistence, and simulated robots. On-prem is authoritative for safety and execution. QoS plus durable application records provide recoverable at-least-once messaging with exactly-once simulated execution claims; physical exactly-once is explicitly out of scope. This keeps the 6–8 hour assessment focused and reviewable.
