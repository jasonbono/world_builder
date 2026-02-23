# Briefing

World ID: 6

See `agent_instructions.md` for general rules, approach, and report requirements.

API base URL: `http://localhost:8080`

## Observable State

- `x` (float) — an observable quantity
- `t` (int) — a discrete time step

## Endpoints

### POST /reset
Resets the world to randomized initial conditions. Returns nothing. After resetting, use `/observe` to see your starting state.

Request body: (none)

### POST /act
Sets a pending action. Does NOT advance time. Returns nothing.

Request body:
```json
{"action": <string>, "value": <float>}
```

Valid actions are `"A"` and `"B"`. Action `"A"` accepts values in [-1.0, 1.0]. Action `"B"` accepts values in [-2.0, 2.0]. Values outside these ranges are clamped. What each action does is unknown — you must discover their effects through experimentation.

You may set both `"A"` and `"B"` before a single `/advance` — they are independent. Calling `/act` multiple times with the same action name before `/advance` overwrites — only the last value per action takes effect. Pending actions are consumed and cleared after each `/advance` (they do not carry over to subsequent advances).

### POST /advance
Advances time by the requested number of steps. Returns nothing.

Request body:
```json
{"steps": <int>}
```

### GET /observe
Reads the current state. Does NOT advance time.

Response:
```json
{"x": <float>, "t": <int>}
```

This is the only way to see the world's state. Calling it multiple times without advancing gives the same result.

### POST /predict
Records your prediction. Returns nothing. Only used for prediction goals. The request body format is specified in the goal.

### POST /done
Submit your results after completing a goal. Returns `{"status": "received"}`.

Request body:
```json
{"goal": <int>, "agent_id": <string>, "solver": <string>, "command": <string>, "report": <string>}
```

- `goal` — the goal number you completed
- `agent_id` — your model name from your system prompt (e.g. `"claude-4.6-opus-high"`)
- `solver` — the full source code of your solver script
- `command` — the command to run it (e.g. `"python3 world_6/run_1/solvers/solve_goal1.py"`)
- `report` — your full report markdown

## Goal 1 (action)

Reach x = 5.0 (±0.2) at t = 50. You may experiment freely, but when you execute your solution (after your final `/reset`), you may call `/act` at most 50 times per action name.

## Goal 2 (prediction)

Reset, observe your initial state, then predict what x will be at t = 30 after applying action A = 0.2 at t = 0 with no further actions. Submit your prediction via `/predict` with body `{"x": <float>}` BEFORE executing the experiment. Then perform the experiment (act, advance, observe) and report both your prediction and the actual outcome.

## Goal 3 (action)

Reach x = 0.0 (±0.1) at t = 40 AND x = 3.0 (±0.2) at t = 50. You may experiment freely, but when you execute your solution (after your final `/reset`), you may call `/act` at most 50 times per action name.
