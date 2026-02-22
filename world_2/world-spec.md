# World 2 — Ball in a Jar (1D Elastic Bouncing)

## State
- x (float, observable, reset: uniform [5.0, 45.0])
- v (float, hidden, reset: 0.0)
- t (int, observable, reset: 0)

## Boundaries
- Hard walls at x = 0 and x = 50
- Elastic reflection at both walls

## Time Evolution
Per tick:
1. x += v * dt  (dt = 1.0)
2. If x >= 50: x = 100 - x, v = -v
3. Else if x <= 0: x = -x, v = -v
4. t += 1

v is unchanged unless modified by an action.

## Actions
- "A" — value in [-5.0, 5.0], effect: sets v to the given value

## Goals
1. (action): Reach x = 25.0 (±0) at t = 10. Max 1 /act call in scored run.
2. (prediction): Predict x at t = 25 after applying A = 3.0 at t = 0, no further actions. Submit via /predict with body {"x": <float>}.
3. (prediction): Predict x at t = 35 after applying A = -2.5 at t = 0, no further actions. Submit via /predict with body {"x": <float>}.
