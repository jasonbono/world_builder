# World 5 — Force Control with Drag

## State
- x (float, observable, reset: uniform [-10.0, 10.0])
- v (float, hidden, reset: 0.0)
- t (int, observable, reset: 0)

## Constants
- k = 0.3 (drag coefficient, hidden)
- dt = 1.0

## Time Evolution
Per tick:
1. Apply pending force: f = pending_A (default 0.0 if no /act since last tick)
2. v = v + f - k * v
3. x = x + v
4. t += 1
5. Clear pending_A (force does NOT persist — must re-act each tick)

Equivalently: v(t+1) = (1-k)*v(t) + f(t), then x(t+1) = x(t) + v(t+1).

The terminal velocity for constant force f is v_∞ = f / k (where drag balances force).
For f = 5.0 and k = 0.3, terminal velocity ≈ 16.67.

## Actions
- "A" — value in [-5.0, 5.0], effect: sets the force applied on the NEXT tick only.

The pending force is consumed and cleared after each tick within an /advance call. If the agent calls /advance with steps > 1, only the first tick uses the pending force; remaining ticks have f = 0. To apply force on every tick, the agent must call /act then /advance(1) repeatedly.

This is the critical difference from previous worlds: the agent cannot set-and-forget. Multi-step control requires multi-step interaction.

## Goals
1. (action): Reach x = 50.0 (±1.0) at t = 20. Max 20 /act calls in the scored run. The agent must plan a force sequence to accelerate, coast, and/or brake.
2. (action): Reach x = 0.0 (±0.1) at t = 30 AND be nearly stopped (|x(t=31) - x(t=30)| < 0.1, measured by advancing one more step with no action). Max 30 /act calls. Soft-landing problem.
3. (prediction): After reset, apply A = 2.0 every tick for 15 steps, then A = 0.0 for 15 more steps. Predict x at t = 30. Submit via /predict with body {"x": <float>}.
