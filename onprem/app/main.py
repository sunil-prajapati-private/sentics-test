from fastapi import FastAPI

app = FastAPI(title="Remote Robot Cell On-prem Service", version="0.1.0")

@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "onprem"}

@app.get("/diagnostics")
def diagnostics() -> dict[str, str]:
    return {"status": "ok", "service": "onprem", "mode": "skeleton"}
