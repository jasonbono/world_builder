# World 4 — Coupled 2D with Mode Switching

## State
- x (float, observable, reset: uniform [0.0, 20.0])
- y (float, observable, reset: uniform [0.0, 20.0])
- vx (float, hidden, reset: 0.0)
- vy (float, hidden, reset: 0.0)
- t (int, observable, reset: 0)

## Mode
- mode = ALPHA if x >= y, else BETA
- Mode is recomputed at the START of each tick (before position update).
- Mode is NOT observable.

## Time Evolution
Per tick:
1. Compute mode from current x, y.
2. If ALPHA: x += vx * dt, y += vy * 0.5 * dt
3. If BETA:  x += vx * 0.5 * dt, y += vy * dt
4. t += 1

dt = 1.0

vx and vy are unchanged unless modified by actions.

## Actions
- "A" — value in [-5.0, 5.0], effect: sets vx to the given value
- "B" — value in [-5.0, 5.0], effect: sets vy to the given value

Both can be set before a single /advance call. Only the last value per action name takes effect. Pending actions are consumed on advance.

## Goals
1. (action): Reach x = 40.0 (±0.5) AND y = 10.0 (±0.5) at t = 12. Max 1 /act call per action (i.e. at most one "A" and one "B") in the scored run.
2. (prediction): After reset, apply A = 2.0 and B = -1.0 at t = 0, no further actions. Predict x and y at t = 20. Submit via /predict with body {"x": <float>, "y": <float>}.
