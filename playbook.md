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
world_builder/                              # this project
  playbook.md                               # this file — read at session start
  agent_instructions.md                     # shared across worlds, rarely changes
  agent_briefing_simple_world_example.md    # template-by-example for agent briefings
  world_1/                                  # reference implementation (constant velocity)
  world_N/                                  # one folder per world
    agent_briefing.md                       # what the agent sees (API shapes + goals, no physics)
    world-spec.md                           # internal spec of the dynamics (agent never sees this)
    server.py                               # the world server (FastAPI, single file)
    static/index.html                       # dashboard UI for manual testing
    requirements.txt                        # Python deps: fastapi, uvicorn, pytest, httpx
    test_server.py                          # pytest tests for the server
```

## Workflow for a New World

### 0. Create the world folder

Create `world_N/` in the project root. All files for this world go inside it. Do not touch anything outside this folder.

### 1. Design the world

Agree on the dynamics with the user:
- State variables (observable and hidden)
- Time evolution rules
- Actions (names, value ranges, effects)
- Initial conditions (fixed defaults for hidden state)
- Reset bounds for each observable variable (randomization ranges)

Write `world_N/world-spec.md` capturing all of this. This is the internal blueprint — the agent never sees it. See `world_1/world-spec.md` for the format.

### 2. Build the server

Single file `server.py` using FastAPI. Follow the API contract:

| Endpoint | Method | Purpose | Returns |
|----------|--------|---------|---------|
| /reset | POST | Reset to randomized initial conditions | Nothing |
| /act | POST | Set pending action (no time advance) | Nothing |
| /advance | POST | Advance time by N steps | Nothing |
| /observe | GET | Read current state | Observable state |
| /predict | POST | Record a prediction (prediction goals only) | Nothing |

Key principles:
- Three orthogonal primitives: control (act), evolve (advance), measure (observe)
- No endpoint does double duty
- `/observe` is the ONLY way to get information from the world
- `/reset` randomizes observable state within world-builder-defined bounds. Hidden state resets to fixed defaults (typically 0). t resets to 0. The agent discovers its starting state via `/observe`.
- `/predict` records the agent's prediction for prediction goals. Returns nothing. The request shape is defined per goal in the briefing.
- The pending action is consumed and cleared after each `/advance`. This is an API-level invariant across all worlds. Persistent effects (e.g., constant force) are modeled via hidden state in the world's update equations, not by making actions persist in the API.
- Server logs all API calls (endpoint, payload, timestamp) for auditing prediction goals.
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

Design goals upfront with the user. Goals can be **action goals** (reach a target state) or **prediction goals** (predict the outcome of a prescribed experiment). Any number, any mix, decided during world building.

Goals should escalate in difficulty. Early goals should be achievable with a partial model; later goals should require the full correct model or include constraints that break incorrect models.

**Action goals** specify a target state and optional constraints (act budgets, timing). The agent controls the world to hit the target.

**Prediction goals** specify an experiment (action + duration) and ask the agent to predict the outcome before executing. The flow is: reset → observe initial state → predict → execute prescribed experiment → observe outcome. The goal must specify the action so the agent can't reverse-engineer (choose an action that makes its prediction true).

All goals are agreed on before the agent starts. Only Goal 1 goes in the initial briefing. Subsequent goals are added after the agent completes the previous one.

### 5. Write the briefing

`agent_briefing.md` — the only world-specific document the agent sees. Contains:
- API base URL
- Observable state (names and types, no semantics)
- Endpoint documentation (shapes only, no physics hints)
- Action name and value range (but NOT what the action does)
- Goal 1 only (subsequent goals are held back)

Use `agent_briefing_simple_world_example.md` as a template. Change the observable state, action names/ranges, and goals to match the new world.

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
- No free information leaks (no /history, no /docs, reset/act/advance/predict return nothing)
- Reset randomizes observable state within bounds; hidden state and t reset to fixed defaults
- Server logs all API calls for prediction goal audit

### Goal design
- Goals designed upfront, delivered sequentially
- Two types: action goals (reach a target) and prediction goals (predict an outcome)
- Escalate to test the model (multi-waypoint, act budgets, timing constraints, prediction accuracy)
- Use constraints that are impossible under incorrect models to force model revision
- Each action goal specifies a tolerance (e.g., `±0` for exact, `±0.5` for approximate). Default to `±0` unless the dynamics make exact targeting unreasonable.
- Prediction goals must specify the action the agent performs — the agent does not choose
- Prediction goal audit: server log must show reset → observe → predict → act/advance → observe (any deviation is a violation)

### What the agent should NOT know
- Source code
- Hidden state variables or their values
- What actions do
- The evolution equations
- The implementation language or framework

### Naming conventions
- Action names should be non-descriptive (e.g., `"A"`, `"B"`). Never use names that hint at semantics (e.g., `"thrust"`, `"force"`, `"temperature"`).
- Observable state names should be generic (e.g., `x`, `y`, `p`). Avoid names like `position`, `velocity`, `energy`.
