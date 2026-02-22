# World Server Specification

## Context
You are building a simulated world that will be explored by an AI agent
in a separate project. Your job is ONLY to build the world server.
You are not the agent. Do not build agent logic, goal-seeking behavior,
or any intelligence. Build a dumb physics server that accepts actions
and returns state.

The world is frozen between API calls. Nothing evolves unless the agent
calls an endpoint that advances time.

## State
- position x (float, initial value: 0.0)
- hidden velocity v (float, initial value: 0.0)
- time t (int, initial value: 0)

## Time Evolution
On each tick:
- x(t+1) = x(t) + v(t) * dt
- v is unchanged unless modified by an action
- dt = 1.0

## Actuator
- one action called "A"
- takes a float value in [-5.0, 5.0]
- effect: sets v to the given value (the agent does not know this)

## Observable
The agent can see:
- x (exact, no noise)
- t

The agent CANNOT see:
- v
- the name or meaning of action "A"
- any internal state or source code

## API Endpoints

POST /act
  Request body: {"action": "A", "value": <float>}
  Behavior: applies the action, then advances one tick
  Response: {
    "before": {"x": <float>, "t": <int>},
    "after": {"x": <float>, "t": <int>}
  }
  Clamp value to [-5.0, 5.0].

POST /observe
  Request body: {"steps": <int>}
  Behavior: advances the world by the requested number of ticks, no action applied
  Response: {
    "states": [{"x": <float>, "t": <int>}, ...]
  }
  Returns one entry per tick, in order.

POST /advance
  Request body: {"steps": <int>}
  Behavior: advances the world by the requested number of ticks, no action applied
  Response: {"x": <float>, "t": <int>}
  Returns only the final state. Use when the agent wants to skip ahead
  without paying token cost for intermediate states.

POST /reset
  Behavior: resets x=0.0, v=0.0, t=0, clears history
  Response: {"x": 0.0, "t": 0}

GET /history
  Response: [{"t": <int>, "x": <float>, "action": {"name": "A", "value": <float>} or null}, ...]
  Full log of every tick since last reset.

## Implementation
- Python, FastAPI, single file: server.py
- Minimal dependencies: fastapi, uvicorn
- Print each tick to console: "t={t} x={x} v={v} action={action}"
- Store full history in memory (list of dicts)
- Run on localhost:8080

