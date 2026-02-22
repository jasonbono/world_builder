"""World 4 server — coupled 2D with mode switching."""

from __future__ import annotations

import io
import json
import math
import os
import random
import time
import zipfile

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

# --- State ---
x: float = 0.0
y: float = 0.0
vx: float = 0.0
vy: float = 0.0
t: int = 0
pending_a: float | None = None
pending_b: float | None = None

X_RESET_MIN, X_RESET_MAX = 0.0, 20.0
Y_RESET_MIN, Y_RESET_MAX = 0.0, 20.0
V_MIN, V_MAX = -5.0, 5.0
DT = 1.0
DAMP = 0.5

api_log: list[dict] = []
_done_log_start: int = 0


def _log(endpoint: str, payload=None):
    api_log.append({"endpoint": endpoint, "payload": payload, "time": time.time()})


def _mode() -> str:
    return "ALPHA" if x >= y else "BETA"


def _tick():
    global x, y, t
    m = _mode()
    if m == "ALPHA":
        x += vx * DT
        y += vy * DAMP * DT
    else:
        x += vx * DAMP * DT
        y += vy * DT
    t += 1
    print(f"  t={t} x={x:.6f} y={y:.6f} vx={vx:.6f} vy={vy:.6f} mode={m}")


class ActRequest(BaseModel):
    action: str
    value: float


class AdvanceRequest(BaseModel):
    steps: int


class PredictRequest(BaseModel):
    x: float
    y: float


class DoneRequest(BaseModel):
    goal: int
    agent_id: str
    solver: str
    command: str
    report: str


@app.post("/reset", status_code=204)
def reset():
    global x, y, vx, vy, t, pending_a, pending_b
    x = random.uniform(X_RESET_MIN, X_RESET_MAX)
    y = random.uniform(Y_RESET_MIN, Y_RESET_MAX)
    vx = 0.0
    vy = 0.0
    t = 0
    pending_a = None
    pending_b = None
    _log("/reset")
    print(f"RESET x={x:.6f} y={y:.6f}")


@app.post("/act", status_code=204)
def act(req: ActRequest):
    global pending_a, pending_b
    if req.action not in ("A", "B"):
        return JSONResponse(status_code=422, content={"detail": f"Unknown action: {req.action}"})
    if not math.isfinite(req.value):
        return JSONResponse(status_code=422, content={"detail": "value must be finite"})
    clamped = max(V_MIN, min(V_MAX, req.value))
    if req.action == "A":
        pending_a = clamped
    else:
        pending_b = clamped
    _log("/act", {"action": req.action, "value": clamped})
    print(f"ACT action={req.action} value={clamped:.6f}")


@app.post("/advance", status_code=204)
def advance(req: AdvanceRequest):
    global vx, vy, pending_a, pending_b
    if req.steps < 1:
        return JSONResponse(status_code=422, content={"detail": "steps must be >= 1"})
    _log("/advance", {"steps": req.steps})
    if pending_a is not None:
        vx = pending_a
        pending_a = None
    if pending_b is not None:
        vy = pending_b
        pending_b = None
    for _ in range(req.steps):
        _tick()


@app.get("/observe")
def observe():
    _log("/observe")
    return {"x": round(x, 10), "y": round(y, 10), "t": t}


@app.post("/predict", status_code=204)
def predict(req: PredictRequest):
    _log("/predict", {"x": req.x, "y": req.y})
    print(f"PREDICT x={req.x:.6f} y={req.y:.6f}")


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
    """Return a zip of agent_instructions.md and agent_briefing.md."""
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
