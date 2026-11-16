#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("CLOUD_DB_PATH", ":memory:")
os.environ.setdefault("ONPREM_DB_PATH", ":memory:")
os.environ.setdefault("MQTT_HOST", "127.0.0.1")

from fastapi.testclient import TestClient
from shared.contracts import Envelope, encode
from cloud.app.main import app as cloud_app, handle_message
from onprem.app.main import runtime


with TestClient(cloud_app) as client:
    assert client.get("/healthz").status_code == 200
    job = client.post("/api/jobs", json={"robot_id": "robot-1", "source_station": "A", "destination_station": "B"}).json()
    for state in ("received", "queued", "running", "done"):
        event = Envelope("1", f"smoke-{state}", "job.status", "onprem", "site-1", "now", {"state": state}, robot_id="robot-1", job_id=job["job_id"])
        handle_message(None, None, SimpleNamespace(payload=encode(event)))
    assert client.get(f"/api/jobs/{job['job_id']}").json()["status"] == "done"

runtime.store.enroll("site-1", "robot-1", "cell-1", "A,B,C", "now")
safety = runtime.controller.person_entered("cell-1", "smoke-safety", "now")
assert safety["state"] == "occupied"
runtime.close()
print("runtime smoke passed: cloud job projection and on-prem safety")
