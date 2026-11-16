import asyncio
import json
import os
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from shared.contracts import Envelope, cloud_cancel_topic, cloud_job_topic, cloud_safety_topic, decode, encode
from .service import SITE_ID, store, create_job_data, ingest_status_data
from .auth import current_user, issue_token, user_store

try:
    import paho.mqtt.client as mqtt
except ImportError:  # pragma: no cover
    mqtt = None

app = FastAPI(title="Remote Robot Cell Cloud API", version="0.3.0")
subscribers = []
mqtt_client = None
broker_connected = False


class JobRequest(BaseModel):
    robot_id: str
    source_station: str
    destination_station: str
    failure_mode: str | None = None

class SafetyRequest(BaseModel):
    cell_id: str
    event: str
    event_id: str | None = None

class LoginRequest(BaseModel):
    username: str
    password: str


def now():
    return datetime.now(timezone.utc).isoformat()


def publish_update(job):
    for queue in list(subscribers):
        try:
            queue.put_nowait(job)
        except asyncio.QueueFull:
            continue


def publish_outbox():
    if mqtt_client is None or not broker_connected:
        return
    for message_id, job_id, payload in store.pending_outbox():
        envelope = decode(payload)
        if envelope["event_type"] == "job.command":
            target = cloud_job_topic(SITE_ID, job_id)
        elif envelope["event_type"] == "job.cancel":
            target = cloud_cancel_topic(SITE_ID, job_id)
        elif envelope["event_type"] == "safety.event":
            target = cloud_safety_topic(SITE_ID, envelope["payload"]["cell_id"])
        else:
            continue
        result = mqtt_client.publish(target, payload.encode(), qos=1)
        if result.rc == mqtt.MQTT_ERR_SUCCESS and envelope["event_type"] != "job.command":
            store.mark_published(message_id, now())


def handle_message(_client, _userdata, message):
    try:
        envelope = decode(message.payload)
        if envelope["event_type"] == "job.status":
            if ingest_status_data(message.payload):
                publish_update(store.get_job(envelope.get("job_id")))
        elif envelope["event_type"] == "enrollment.response":
            payload = envelope["payload"]
            store.upsert_robot(
                SITE_ID,
                payload["robot_id"],
                payload["cell_id"],
                ",".join(payload["stations"]),
                payload.get("state", "approved"),
            )
        elif envelope["event_type"] == "robot.state":
            payload = envelope["payload"]
            store.update_robot_state(SITE_ID, payload["robot_id"], payload["state"], payload.get("reason"), payload.get("last_seen", envelope["occurred_at"]))
        elif envelope["event_type"] == "heartbeat":
            for robot_id in envelope["payload"].get("robots", []):
                store.touch_robot(SITE_ID, robot_id, envelope["occurred_at"])
            # A heartbeat is also an on-prem liveness signal; use it to retry
            # cloud commands that were created while the on-prem session was down.
            publish_outbox()
    except (KeyError, ValueError):
        return


def _set_broker(value):
    global broker_connected
    broker_connected = value


def _on_connect(client):
    _set_broker(True)
    client.subscribe(f"rrc/v1/{SITE_ID}/onprem/#", qos=1)
    publish_outbox()


def connect_mqtt():
    global mqtt_client
    if mqtt is None:
        return
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"cloud-{SITE_ID}", clean_session=False)
    mqtt_client.on_connect = lambda client, _userdata, _flags, _reason, _properties=None: _on_connect(client)
    mqtt_client.on_disconnect = lambda *_args: _set_broker(False)
    mqtt_client.on_message = handle_message
    mqtt_client.reconnect_delay_set(min_delay=1, max_delay=30)
    try:
        mqtt_client.connect(os.getenv("MQTT_HOST", "mqtt"), int(os.getenv("MQTT_PORT", "1883")), 60)
        mqtt_client.loop_start()
    except (OSError, ValueError):
        mqtt_client = None


@app.on_event("startup")
def startup():
    connect_mqtt()


@app.on_event("shutdown")
def shutdown():
    if mqtt_client is not None:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()


@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "cloud", "broker_connected": broker_connected}


@app.post("/auth/login")
def login(request: LoginRequest, response: Response):
    user = user_store.authenticate(request.username, request.password)
    if not user:
        raise HTTPException(401, "invalid credentials or inactive user")
    response.set_cookie("access_token", issue_token(user), httponly=True, samesite="lax", secure=False, max_age=8 * 3600)
    return user


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"logged_out": True}


@app.get("/auth/me")
def me(user=Depends(current_user)):
    return user


@app.get("/api/robots")
def robots(_user=Depends(current_user)):
    return store.list_robots()


@app.get("/api/jobs")
def jobs(_user=Depends(current_user)):
    return store.list_jobs()


@app.get("/api/jobs/{job_id}")
def job(job_id: str, _user=Depends(current_user)):
    result = store.get_job(job_id)
    if not result:
        raise HTTPException(404, "job not found")
    return result


@app.post("/api/jobs", status_code=202)
def create_job(request: JobRequest, _user=Depends(current_user)):
    try:
        result, _envelope = create_job_data(
            request.robot_id,
            request.source_station,
            request.destination_station,
            request.failure_mode,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    publish_outbox()
    publish_update(result)
    return result


@app.post("/api/safety/events", status_code=202)
def safety_event(request: SafetyRequest, _user=Depends(current_user)):
    if request.event not in {"person_entered", "person_left"}:
        raise HTTPException(422, "event must be person_entered or person_left")
    envelope = Envelope("1", request.event_id or str(uuid4()), "safety.event", "cloud", SITE_ID, now(), {"cell_id": request.cell_id, "event": request.event, "event_id": request.event_id})
    store.add_outbox(envelope.message_id, request.cell_id, encode(envelope).decode())
    publish_outbox()
    return {"accepted": True, "event_id": envelope.message_id}


@app.delete("/api/jobs/{job_id}", status_code=202)
def cancel_job(job_id: str, _user=Depends(current_user)):
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    if job["status"] != "queued":
        raise HTTPException(409, "only queued jobs can be cancelled")
    envelope = Envelope("1", str(uuid4()), "job.cancel", "cloud", SITE_ID, now(), {"job_id": job_id, "robot_id": job["robot_id"]}, robot_id=job["robot_id"], job_id=job_id, correlation_id=job_id)
    store.add_outbox(envelope.message_id, job_id, encode(envelope).decode())
    publish_outbox()
    return {"accepted": True, "job_id": job_id}


@app.get("/api/events")
async def events(_user=Depends(current_user)):
    queue = asyncio.Queue(maxsize=100)
    subscribers.append(queue)

    async def stream():
        try:
            for item in store.list_jobs():
                yield f"data: {json.dumps(item)}\n\n"
            while True:
                yield f"data: {json.dumps(await queue.get())}\n\n"
        finally:
            if queue in subscribers:
                subscribers.remove(queue)

    return StreamingResponse(stream(), media_type="text/event-stream")
