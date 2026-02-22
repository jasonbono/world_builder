# World 1 — Constant Velocity

## State
- x (float, observable, reset: uniform [-10.0, 10.0])
- v (float, hidden, reset: 0.0)
- t (int, observable, reset: 0)

## Time Evolution
x(t+1) = x(t) + v(t) * dt
dt = 1.0
v is unchanged unless modified by an action.

## Actions
- "A" — value in [-5.0, 5.0], effect: sets v to the given value

## Goals
1. (action): Reach x = 50.0 (±0) at t = 10. Max 1 /act call in scored run.
2. (prediction): Predict x at t = 5 after applying A = 2.0 at t = 0, no further actions. Submit via /predict with body {"x": <float>}.
