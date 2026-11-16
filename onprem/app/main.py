import os
import threading
import time
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from shared.contracts import (
    CAPABILITIES,
    Envelope,
    JobStatus,
    decode,
    encode,
    onprem_enrollment_topic,
    onprem_heartbeat_topic,
    onprem_robot_topic,
    onprem_status_topic,
)
from .execution import JobCommand
from .persistence import OnPremStore
from .safety import SafetyController

try:
    import paho.mqtt.client as mqtt
except ImportError:  # pragma: no cover
    mqtt = None

SITE_ID = os.getenv("SITE_ID", "site-1")


def now():
    return datetime.now(timezone.utc).isoformat()


class SafetyEvent(BaseModel):
    cell_id: str
    event: str
    event_id: str | None = None


class Runtime:
    def __init__(self):
        self.store = OnPremStore(os.getenv("ONPREM_DB_PATH", ":memory:"))
        self.controller = SafetyController(self.store)
        self.client = None
        self.connected = False
        self.stop = threading.Event()
        self.worker = None
        self.started_at = time.monotonic()
        self.deadlines = {}
        self.duration = float(os.getenv("JOB_DURATION_SECONDS", "3"))
        self.max_retries = int(os.getenv("JOB_MAX_RETRIES", "1"))

    def status(self, job_id, state, reason=None, robot_id=None):
        payload = {"state": state}
        if reason:
            payload["reason"] = reason
        envelope = Envelope(
            "1", str(uuid4()), "job.status", "onprem", SITE_ID, now(), payload,
            robot_id=robot_id, job_id=job_id, correlation_id=job_id,
        )
        self.publish(envelope, onprem_status_topic(SITE_ID, job_id))

    def publish_enrollment(self, robot_id, cell_id, stations):
        payload = {"robot_id": robot_id, "cell_id": cell_id, "stations": sorted(stations), "state": "approved"}
        envelope = Envelope("1", str(uuid4()), "enrollment.response", "onprem", SITE_ID, now(), payload, robot_id=robot_id, cell_id=cell_id)
        self.publish(envelope, onprem_enrollment_topic(SITE_ID, robot_id))

    def publish_robot_state(self, robot_id, state, reason=None):
        cell_id = CAPABILITIES[robot_id][0]
        stamp = now()
        with self.store.db_lock:
            self.store.db.execute("INSERT INTO robot_state(site_id,robot_id,state,cell_id,state_reason,last_seen) VALUES(?,?,?,?,?,?) ON CONFLICT(site_id,robot_id) DO UPDATE SET state=excluded.state,state_reason=excluded.state_reason,last_seen=excluded.last_seen", (SITE_ID, robot_id, state, cell_id, reason, stamp))
            self.store.db.commit()
        payload = {"robot_id": robot_id, "cell_id": cell_id, "state": state, "reason": reason, "last_seen": stamp}
        envelope = Envelope("1", str(uuid4()), "robot.state", "onprem", SITE_ID, stamp, payload, robot_id=robot_id, cell_id=cell_id)
        self.publish(envelope, onprem_robot_topic(SITE_ID, robot_id))

    def publish_heartbeat(self):
        stamp = now()
        envelope = Envelope("1", str(uuid4()), "heartbeat", "onprem", SITE_ID, stamp, {"service": "onprem", "state": "online", "robots": list(CAPABILITIES)})
        self.publish(envelope, onprem_heartbeat_topic(SITE_ID))

    def publish(self, envelope, topic):
        raw = encode(envelope)
        self.store.add_outbound(envelope.message_id, raw.decode())
        if self.client is not None and self.connected:
            result = self.client.publish(topic, raw, qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.store.mark_outbound(envelope.message_id, now())

    def replay_outbound(self):
        if self.client is None or not self.connected:
            return
        for message_id, raw in self.store.pending_outbound():
            envelope = decode(raw)
            if envelope["event_type"] == "job.status":
                topic = onprem_status_topic(SITE_ID, envelope["job_id"])
            elif envelope["event_type"] == "enrollment.response":
                topic = onprem_enrollment_topic(SITE_ID, envelope["robot_id"])
            elif envelope["event_type"] == "robot.state":
                topic = onprem_robot_topic(SITE_ID, envelope["robot_id"])
            elif envelope["event_type"] == "heartbeat":
                topic = onprem_heartbeat_topic(SITE_ID)
            else:
                continue
            result = self.client.publish(topic, raw.encode(), qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.store.mark_outbound(message_id, now())

    def _publish_new_events(self, before, robot_id=None):
        for event in self.controller.events[before:]:
            if event.get("job_id"):
                self.status(event["job_id"], event["state"], event.get("reason"), robot_id)

    def on_message(self, _client, _userdata, message):
        try:
            envelope = decode(message.payload)
            if envelope["event_type"] == "job.command":
                payload = envelope["payload"]
                before = len(self.controller.events)
                self.controller.receive(JobCommand(
                    envelope["message_id"], envelope["job_id"], payload["robot_id"],
                    payload["source_station"], payload["destination_station"],
                    envelope["site_id"], payload.get("failure_mode"),
                ), now())
                self._publish_new_events(before, payload["robot_id"])
            elif envelope["event_type"] == "job.cancel":
                before = len(self.controller.events)
                self.controller.cancel(envelope["job_id"])
                self._publish_new_events(before, envelope.get("robot_id"))
            elif envelope["event_type"] == "safety.event":
                payload = envelope["payload"]
                before = len(self.controller.events)
                event_id = payload.get("event_id") or envelope["message_id"]
                if payload["event"] == "person_entered":
                    self.controller.person_entered(payload["cell_id"], event_id, now())
                elif payload["event"] == "person_left":
                    self.controller.person_left(payload["cell_id"], event_id, now())
                robot_id = next((robot for robot, (cell, _) in CAPABILITIES.items() if cell == payload["cell_id"]), None)
                if robot_id:
                    if payload["event"] == "person_entered":
                        self.publish_robot_state(robot_id, "paused", "person_in_cell")
                    elif payload["event"] == "person_left":
                        self.publish_robot_state(robot_id, "busy" if robot_id in self.controller.active else "idle", "cell_clear")
                self._publish_new_events(before)
        except (KeyError, ValueError):
            return

    def connect(self):
        if mqtt is None:
            return
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"onprem-{SITE_ID}", clean_session=False)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = lambda *_args: setattr(self, "connected", False)
        self.client.on_message = self.on_message
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        try:
            self.client.connect(os.getenv("MQTT_HOST", "mqtt"), int(os.getenv("MQTT_PORT", "1883")), 60)
            self.client.loop_start()
        except (OSError, ValueError):
            self.client = None

    def _on_connect(self, client, _userdata, _flags, _reason, _properties=None):
        self.connected = True
        client.subscribe(f"rrc/v1/{SITE_ID}/cloud/commands/#", qos=1)
        self.replay_outbound()
        for robot_id, (cell_id, stations) in CAPABILITIES.items():
            self.store.enroll(SITE_ID, robot_id, cell_id, ",".join(sorted(stations)), now())
            self.publish_enrollment(robot_id, cell_id, stations)
            self.publish_robot_state(robot_id, "idle")
        self.publish_heartbeat()

    def worker_loop(self):
        robots = list(CAPABILITIES)
        next_heartbeat = time.monotonic()
        while not self.stop.wait(0.1):
            current = time.monotonic()
            if current >= next_heartbeat:
                self.publish_heartbeat()
                for robot_id, (cell_id, stations) in CAPABILITIES.items():
                    self.publish_enrollment(robot_id, cell_id, stations)
                    state = "paused" if self.controller.occupied.get(cell_id, False) else ("busy" if robot_id in self.controller.active else "idle")
                    self.publish_robot_state(robot_id, state)
                next_heartbeat = current + 10
            for robot_id in robots:
                active_job = self.controller.active.get(robot_id)
                if active_job:
                    if self.controller.occupied.get(CAPABILITIES[robot_id][0], False):
                        continue
                    if current >= self.deadlines.get(robot_id, current):
                        row = self.store.db.execute("SELECT failure_mode FROM robot_queue WHERE job_id=?", (active_job,)).fetchone()
                        retry = self.store.db.execute("SELECT retry_count FROM job_executions WHERE job_id=?", (active_job,)).fetchone()
                        if retry and retry[0] < self.max_retries and row and row[0] == "timeout":
                            self.controller.retry_active(robot_id)
                            self.publish_robot_state(robot_id, "idle", "retrying")
                            continue
                        before = len(self.controller.events)
                        self.controller.finish(robot_id, row[0] if row else None)
                        self._publish_new_events(before, robot_id)
                        self.publish_robot_state(robot_id, "idle", "execution_failed" if row and row[0] in {"always_fail", "timeout"} else None)
                    continue
                before = len(self.controller.events)
                job_id = self.controller.run_next(robot_id, now())
                if job_id:
                    self.deadlines[robot_id] = current + self.duration
                    self.publish_robot_state(robot_id, "busy")
                    self._publish_new_events(before, robot_id)

    def start(self):
        self.connect()
        self.worker = threading.Thread(target=self.worker_loop, name="robot-worker", daemon=True)
        self.worker.start()

    def close(self):
        self.stop.set()
        if self.client is not None:
            self.client.loop_stop()
            self.client.disconnect()
        self.store.db.close()


app = FastAPI(title="Remote Robot Cell On-prem Service", version="0.3.0")
runtime = Runtime()


@app.on_event("startup")
def startup():
    runtime.start()


@app.on_event("shutdown")
def shutdown():
    runtime.close()


@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "onprem", "broker_connected": runtime.connected}


@app.get("/diagnostics")
def diagnostics():
    return {
        "status": "ok",
        "service": "onprem",
        "mode": "runtime",
        "broker_connected": runtime.connected,
        "queued_jobs": runtime.store.queued_jobs(),
    }


@app.post("/api/safety/events")
def safety_event(event: SafetyEvent):
    before = len(runtime.controller.events)
    event_id = event.event_id or str(uuid4())
    try:
        if event.event == "person_entered":
            result = runtime.controller.person_entered(event.cell_id, event_id, now())
        elif event.event == "person_left":
            result = runtime.controller.person_left(event.cell_id, event_id, now())
        else:
            raise HTTPException(422, "event must be person_entered or person_left")
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    runtime._publish_new_events(before)
    return result
