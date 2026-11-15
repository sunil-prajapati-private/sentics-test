# MQTT contract

Canonical topics are `rrc/v1/{site}/{direction}/{kind}/{resource}/{id}`. Cloud publishes `rrc/v1/{site}/cloud/commands/jobs/{job_id}` and `.../commands/enrollment/{robot_id}`. On-prem publishes `.../onprem/events/jobs/{job_id}`, `.../onprem/state/robots/{robot_id}`, `.../onprem/events/safety/{cell_id}`, `.../onprem/events/enrollment/{robot_id}`, and `.../onprem/events/heartbeat`.

Envelope: `{schema_version,message_id,event_type,source,site_id,robot_id?,cell_id?,job_id?,correlation_id?,occurred_at,payload}`. Version `1`, UUID-like stable IDs, RFC3339 UTC timestamps, and object payloads are required. Unknown versions, malformed JSON, missing fields, and non-object payloads are rejected before business handling.

Commands, enrollment, and status use QoS 1, durable sessions, and broker persistence; telemetry may use QoS 0. Retain last robot/service state only, never commands. Last-will marks service offline when heartbeats are enabled. The implementation currently provides a deterministic in-memory broker for tests and an optional `paho-mqtt` dependency for the later runtime adapter.

Enrollment request payload: `{robot_id,cell_id,stations,request_id}`. Job command: `{robot_id,source_station,destination_station,failure_mode?}`. Status: `{state,reason?,sequence}`. Robot state: `{state,cell_id,stations}`. Safety: `{event: person_entered|person_left,cell_id,event_id}`. Heartbeat: `{service_id,uptime}`.

Consumers persist message IDs and unique execution claims before effects. Repeated delivery is acknowledged without a second effect; stale sequences are ignored; unknown event types are quarantined/reported; malformed messages produce an error outcome. Enrollment requests are accepted only for the known local robot/cell model and persisted on-prem. Reconnect resubscribes to the same patterns; replay remains safe because application deduplication, not MQTT QoS, defines effects.
