# Playbook

Reference for building world servers and agent briefings. This document is written for the **world builder** (you, the AI assistant in this Cursor project). Read it at the start of any new session.

## Roles

- **User** — the human running both projects. Decides on world designs, approves plans, ships files between projects.
- **Agent** — an LLM-based AI in a separate Cursor project. Receives a briefing and instructions, experiments with the API, discovers dynamics, and solves goals. Cannot see source code.
- **World builder** (you) — builds the server, writes the briefing, designs goals with the user. Never modify `agent_instructions.md` or `agent_briefing.md` without the user's explicit approval in chat. When building a world, only create/edit files inside that world's folder.

## What This Project Is

A framework for testing AI agents' ability to discover unknown world dynamics through experimentation. The setup has two sides:

1. **World builder** (this project) — builds and hosts physics simulations exposed via REST API. Each world lives in its own subfolder.
2. **Agent** (separate Cursor project) — receives a briefing and instructions, experiments with the API, discovers the dynamics, and solves goals.

## Isolation Rule

When building world N, **only create and edit files inside `world_N/`**. Never modify files outside that folder without explicit user approval. Each world folder is self-contained.

## File Structure

```
world_builder/                # this project
  playbook.md                 # this file — shared, read at session start
  agent_instructions.md       # shared across worlds, rarely changes
  enhancements.md             # shared notes / future ideas
  world_1/                    # one folder per world
    agent_briefing.md         # what the agent sees (API shapes + goals, no physics)
    world-spec.md             # internal spec of the dynamics (agent never sees this)
    server.py                 # the world server (FastAPI, single file)
    static/index.html         # dashboard UI for manual testing
    requirements.txt          # Python deps: fastapi, uvicorn, pytest, httpx
    test_server.py            # pytest tests for the server
  world_2/
    ...
```

## Workflow for a New World

### 0. Create the world folder

Create `world_N/` in the project root. All files for this world go inside it. Do not touch anything outside this folder.

### 1. Design the world

Agree on the dynamics with the user:
- State variables (observable and hidden)
- Time evolution rules
- Actions (names, value ranges, effects)
- Initial conditions

Write `world_N/world-spec.md` capturing all of this. This is the internal blueprint — the agent never sees it.

### 2. Build the server

Single file `server.py` using FastAPI. Follow the API contract:

| Endpoint | Method | Purpose | Returns |
|----------|--------|---------|---------|
| /reset | POST | Reset to initial conditions | Nothing |
| /act | POST | Set pending action (no time advance) | Nothing |
| /advance | POST | Advance time by N steps | Nothing |
| /observe | GET | Read current state | Observable state |

Key principles:
- Three orthogonal primitives: control (act), evolve (advance), measure (observe)
- No endpoint does double duty
- `/observe` is the ONLY way to get information from the world
- The pending action is consumed and cleared after each `/advance`. This is an API-level invariant across all worlds. Persistent effects (e.g., constant force) are modeled via hidden state in the world's update equations, not by making actions persist in the API.
- Return 422 for invalid requests (malformed JSON, missing fields, bad types). Never leak internals in error messages.
- Disable `/docs`, `/redoc`, `/openapi.json` (pass `docs_url=None, redoc_url=None, openapi_url=None` to FastAPI)
- Print each tick to console for debugging: `t={t} x={x} ...`
- Run on `localhost:8080`
- Include a `static/index.html` dashboard for manual testing (slider for actions, chart for state, buttons for endpoints)

Dependencies: `fastapi`, `uvicorn`. For tests: `pytest`, `httpx`.

### 3. Write tests

`test_server.py` using FastAPI's TestClient. Cover:
- Each endpoint's basic behavior
- Edge cases (clamping, invalid actions)
- Physics consistency (model equations hold across sequences)

Run: `python3 -m pytest test_server.py -v`

### 4. Design goals

Design all 3 goals upfront with the user. Hitting them should require a complete and accurate world model. Goals should escalate in difficulty:
- Goal 1: achievable with a partial or approximate model
- Goal 2: requires a more complete model (e.g., understanding persistence, hidden state)
- Goal 3: requires the full correct model, or includes constraints that break incorrect models

All 3 goals are agreed on before the agent starts. Only Goal 1 goes in the initial briefing. Goals 2 and 3 are added after the agent completes the previous one.

### 5. Write the briefing

`agent_briefing.md` — the only world-specific document the agent sees. Contains:
- API base URL
- Observable state (names and types, no semantics)
- Endpoint documentation (shapes only, no physics hints)
- Action name and value range (but NOT what the action does)
- Goal 1 only (Goals 2 and 3 are held back)

Use the existing briefing as a template. Change the observable state, action names/ranges, and goals to match the new world.

### 6. Check agent_instructions.md

This file should NOT change between worlds. It contains:
- General rules (don't cheat, don't edit instructions/briefing)
- Working files convention (artifacts/ folder)
- Approach (experiment, model, solve, report)
- Report template
- Solver versioning guidance

If the new world requires instruction changes, flag for the user's attention. Do not modify without explicit approval.

### 7. Ship to the agent

The agent's project gets exactly two files:
- `agent_instructions.md`
- `agent_briefing.md`

The agent creates its own working folders (`artifacts/`, `reports/`) as needed.

Start the server in this project, then inform the user so they can start the agent.

### 8. Between rounds

After the agent completes a goal, add the next goal to `agent_briefing.md` and inform the user so they can pass it to the agent. The agent picks it up on the next round.

Monitor the server console to see what the agent is doing (tick logs).

## Design Principles

### API design
- Act/advance/observe are orthogonal: control, evolve, measure
- Only observe returns information — this makes observation count the natural metric
- No free information leaks (no /history, no /docs, reset/act/advance return nothing)

### Goal design
- All 3 goals designed upfront, delivered sequentially
- Escalate to test the model (multi-waypoint, act budgets, timing constraints)
- Use constraints that are impossible under incorrect models to force model revision
- Each goal specifies a tolerance (e.g., `±0` for exact, `±0.5` for approximate). Default to `±0` unless the dynamics make exact targeting unreasonable.
- Example from world_1: "reach x=50 with at most 1 act call" breaks the additive model, forces discovery of velocity persistence

### What the agent should NOT know
- Source code
- Hidden state variables or their values
- What actions do
- The evolution equations
- The implementation language or framework

### Naming conventions
- Action names should be non-descriptive (e.g., `"A"`, `"B"`). Never use names that hint at semantics (e.g., `"thrust"`, `"force"`, `"temperature"`).
- Observable state names should be generic (e.g., `x`, `y`, `p`). Avoid names like `position`, `velocity`, `energy`.
