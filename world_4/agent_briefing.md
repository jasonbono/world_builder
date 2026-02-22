# Briefing

World ID: 4

See `agent_instructions.md` for general rules, approach, and report requirements.

API base URL: `http://localhost:8080`

## Observable State

- `x` (float) — an observable quantity
- `y` (float) — an observable quantity
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

Valid actions are `"A"` and `"B"`. Values must be floats in [-5.0, 5.0] (values outside this range are clamped). What each action does is unknown — you must discover their effects through experimentation.

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
{"x": <float>, "y": <float>, "t": <int>}
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
- `command` — the command to run it (e.g. `"python3 world_4/run_1/solvers/solve_goal1.py"`)
- `report` — your full report markdown

## Goal 1 (action)

Reach x = 40.0 (±0.5) AND y = 10.0 (±0.5) at t = 12. You may experiment freely, but when you execute your solution (after your final `/reset`), you may call `/act` at most once per action name (i.e. at most one "A" call and one "B" call).
