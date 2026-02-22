"""World 2 server — ball in a jar (1D elastic bouncing)."""

from __future__ import annotations

import math
import os
import random
import time

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

# --- State ---
x: float = 0.0
v: float = 0.0
t: int = 0
pending_action: float | None = None

X_RESET_MIN, X_RESET_MAX = 5.0, 45.0
A_MIN, A_MAX = -5.0, 5.0
WALL_LO, WALL_HI = 0.0, 50.0
DT = 1.0

api_log: list[dict] = []


def _log(endpoint: str, payload=None):
    api_log.append({"endpoint": endpoint, "payload": payload, "time": time.time()})


def _tick():
    global x, v, t
    x += v * DT
    if x >= WALL_HI:
        x = 2 * WALL_HI - x
        v = -v
    elif x <= WALL_LO:
        x = -x
        v = -v
    t += 1
    print(f"  t={t} x={x:.6f} v={v:.6f}")


class ActRequest(BaseModel):
    action: str
    value: float


class AdvanceRequest(BaseModel):
    steps: int


class PredictRequest(BaseModel):
    x: float


@app.post("/reset", status_code=204)
def reset():
    global x, v, t, pending_action
    x = random.uniform(X_RESET_MIN, X_RESET_MAX)
    v = 0.0
    t = 0
    pending_action = None
    api_log.clear()
    _log("/reset")
    print(f"RESET x={x:.6f}")


@app.post("/act", status_code=204)
def act(req: ActRequest):
    global pending_action
    if req.action != "A":
        return JSONResponse(status_code=422, content={"detail": f"Unknown action: {req.action}"})
    if not math.isfinite(req.value):
        return JSONResponse(status_code=422, content={"detail": "value must be finite"})
    clamped = max(A_MIN, min(A_MAX, req.value))
    pending_action = clamped
    _log("/act", {"action": req.action, "value": clamped})
    print(f"ACT action={req.action} value={clamped:.6f}")


@app.post("/advance", status_code=204)
def advance(req: AdvanceRequest):
    global v, pending_action
    if req.steps < 1:
        return JSONResponse(status_code=422, content={"detail": "steps must be >= 1"})
    _log("/advance", {"steps": req.steps})
    if pending_action is not None:
        v = pending_action
        pending_action = None
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


_static = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


@app.get("/")
def dashboard():
    return FileResponse(os.path.join(_static, "index.html"))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
