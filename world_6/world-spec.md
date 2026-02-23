# World 6 — Coupled Hidden Oscillator

## State
- x (float, observable, see projection rule below)
- θ (theta, float, hidden, reset: 0.0) — angle on a hidden circle
- ω (omega, float, hidden, reset: 0.0) — angular velocity
- r (float, hidden, reset: 1.0) — radius / amplitude
- t (int, observable, reset: 0)

## Time Evolution
Per tick:
1. Apply pending actions: ω += pending_A (default 0), r += pending_B (default 0)
2. Clamp r to [0.1, 10.0]
3. θ += ω
4. x = r * sin(θ)
5. t += 1
6. Clear pending actions

Key: actions modify hidden oscillator parameters BEFORE the angle advances and x is computed.

## Actions
- "A" — value in [-1.0, 1.0], effect: adds to angular velocity ω
- "B" — value in [-2.0, 2.0], effect: adds to radius r (clamped to [0.1, 10.0])

Pending actions are consumed and cleared after each tick within an /advance call. Same as World 5: if agent calls /advance with steps > 1, only the first tick uses pending actions; remaining ticks have no action input.

## Reset
- θ = 0.0, ω = 0.0, r = 1.0 (fixed, hidden)
- x = r * sin(θ) = 0.0 (always starts at 0 after reset)
- t = 0

Note: x always starts at 0 after reset because sin(0) = 0 and the hidden state is deterministic. This is intentional — there's nothing to randomize since all hidden state is fixed on reset.

## Observable behavior
- With no actions, x stays at 0 forever (ω = 0, so θ stays at 0)
- A single A action starts oscillation at that angular velocity
- Larger |ω| means faster oscillation
- B changes amplitude (visible as larger swings)
- The oscillation period is 2π/|ω| ticks
- x is bounded by [-r, r]

## Goals
1. (action): Reach x = 5.0 (±0.2) at t = 50. Max 50 /act calls per action name.
2. (prediction): After reset, apply A = 0.2 at t = 0, then no further actions. Predict x at t = 30. Submit via /predict with body {"x": <float>}.
3. (action): Reach x = 0.0 (±0.1) at t = 40 AND x = 3.0 (±0.2) at t = 50. Max 50 /act calls per action name.
