# Briefing

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
Sets the pending action. Does NOT advance time. Returns nothing.

Request body:
```json
{"action": <string>, "value": <float>}
```

The only valid action is `"A"`. Its value must be a float in [-5.0, 5.0] (values outside this range are clamped). What the action does is unknown — you must discover its effect through experimentation.

Calling `/act` multiple times before `/advance` overwrites — only the last value before an advance takes effect. The pending action is consumed and cleared after each `/advance` (it does not carry over to subsequent advances).

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

## Goal 1 (action)

Reach x = 25.0 (±0) at t = 10. You may experiment freely, but when you execute your solution (after your final `/reset`), you may call `/act` at most once.
