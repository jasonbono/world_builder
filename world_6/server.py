"""World 6 server — coupled hidden oscillator."""

from __future__ import annotations

import io
import json
import math
import os
import time
import zipfile

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

# --- State ---
theta: float = 0.0
omega: float = 0.0
r: float = 1.0
x: float = 0.0
t: int = 0
pending_a: float | None = None
pending_b: float | None = None

A_MIN, A_MAX = -1.0, 1.0
B_MIN, B_MAX = -2.0, 2.0
R_MIN, R_MAX = 0.1, 10.0

api_log: list[dict] = []
_done_log_start: int = 0


def _log(endpoint: str, payload=None):
    api_log.append({"endpoint": endpoint, "payload": payload, "time": time.time()})


def _tick():
    global theta, omega, r, x, t, pending_a, pending_b
    if pending_a is not None:
        omega += pending_a
        pending_a = None
    if pending_b is not None:
        r += pending_b
        r = max(R_MIN, min(R_MAX, r))
        pending_b = None
    theta += omega
    x = r * math.sin(theta)
    t += 1
    print(f"  t={t} x={x:.6f} theta={theta:.6f} omega={omega:.6f} r={r:.6f}")


class ActRequest(BaseModel):
    action: str
    value: float


class AdvanceRequest(BaseModel):
    steps: int


class PredictRequest(BaseModel):
    x: float


class DoneRequest(BaseModel):
    goal: int
    agent_id: str
    solver: str
    command: str
    report: str


@app.post("/reset", status_code=204)
def reset():
    global theta, omega, r, x, t, pending_a, pending_b
    theta = 0.0
    omega = 0.0
    r = 1.0
    x = 0.0
    t = 0
    pending_a = None
    pending_b = None
    _log("/reset")
    print(f"RESET x={x:.6f}")


@app.post("/act", status_code=204)
def act(req: ActRequest):
    global pending_a, pending_b
    if req.action not in ("A", "B"):
        return JSONResponse(status_code=422, content={"detail": f"Unknown action: {req.action}"})
    if not math.isfinite(req.value):
        return JSONResponse(status_code=422, content={"detail": "value must be finite"})
    if req.action == "A":
        clamped = max(A_MIN, min(A_MAX, req.value))
        pending_a = clamped
    else:
        clamped = max(B_MIN, min(B_MAX, req.value))
        pending_b = clamped
    _log("/act", {"action": req.action, "value": clamped})
    print(f"ACT action={req.action} value={clamped:.6f}")


@app.post("/advance", status_code=204)
def advance(req: AdvanceRequest):
    if req.steps < 1:
        return JSONResponse(status_code=422, content={"detail": "steps must be >= 1"})
    _log("/advance", {"steps": req.steps})
    for _ in range(req.steps):
        _tick()


@app.get("/observe")
def observe():
    _log("/observe")
    return {"x": round(x, 10), "t": t}


@app.post("/predict", status_code=204)
def predict(req: PredictRequest):
    _log("/predict", {"x": req.x})
    print(f"PREDICT x={req.x:.6f}")


_world_dir = os.path.dirname(os.path.abspath(__file__))
_submissions_dir = os.path.join(_world_dir, "submissions")


@app.post("/done")
def done(req: DoneRequest):
    global _done_log_start
    os.makedirs(_submissions_dir, exist_ok=True)
    trace = api_log[_done_log_start:]
    _done_log_start = len(api_log)
    submission = {
        "goal": req.goal,
        "agent_id": req.agent_id,
        "solver": req.solver,
        "command": req.command,
        "report": req.report,
        "api_trace": trace,
        "submitted_at": time.time(),
    }
    safe_id = req.agent_id.replace("/", "_").replace(" ", "_")
    filename = f"goal_{req.goal}_{safe_id}.json"
    path = os.path.join(_submissions_dir, filename)
    with open(path, "w") as f:
        json.dump(submission, f, indent=2)
    print(f"DONE goal={req.goal} agent={req.agent_id} -> {filename}")
    return {"status": "received"}


_project_root = os.path.dirname(_world_dir)
_static = os.path.join(_world_dir, "static")


@app.get("/bootstrap")
def bootstrap():
    files = {
        "agent_instructions.md": os.path.join(_project_root, "agent_instructions.md"),
        "agent_briefing.md": os.path.join(_world_dir, "agent_briefing.md"),
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for arcname, path in files.items():
            zf.write(path, arcname)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=bootstrap.zip"},
    )


@app.get("/")
def dashboard():
    return FileResponse(os.path.join(_static, "index.html"))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
