# World 3 — Time-Dependent Multiplier

## State
- x (float, observable, reset: uniform [-10.0, 10.0])
- v (float, hidden, reset: 0.0)
- t (int, observable, reset: 0)

## Time Evolution
Per tick:
1. m = (t % 3) + 1
2. x += v * m * dt  (dt = 1.0)
3. t += 1

The multiplier cycles: m = 1 at t=0, m = 2 at t=1, m = 3 at t=2, m = 1 at t=3, ...

v is unchanged unless modified by an action.

## Actions
- "A" — value in [-5.0, 5.0], effect: sets v to the given value

## Goals
1. (action): Reach x = 50.0 (±0) at t = 9. Max 1 /act call in scored run.
2. (prediction): Predict x at t = 12 after applying A = 1.5 at t = 0, no further actions. Submit via /predict with body {"x": <float>}.
