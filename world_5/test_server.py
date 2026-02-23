from fastapi.testclient import TestClient

from server import app

client = TestClient(app)

K = 0.3


def reset():
    r = client.post("/reset")
    assert r.status_code == 204


def observe():
    r = client.get("/observe")
    assert r.status_code == 200
    return r.json()


def act(action, value):
    return client.post("/act", json={"action": action, "value": value})


def advance(steps):
    return client.post("/advance", json={"steps": steps})


def set_state(sx, sv=0.0):
    """Force a deterministic state for testing."""
    import server
    reset()
    server.x = sx
    server.v = sv
    server.t = 0
    server.pending_a = None


def _sim(x0, v0, forces):
    """Pure-Python reference simulation.

    forces: list of floats, one per tick. len(forces) == number of ticks.
    """
    cx, cv = x0, v0
    for f in forces:
        cv = cv + f - K * cv
        cx = cx + cv
    return cx, cv


def _sim_constant(x0, v0, f, steps):
    """Sim with same force every tick (for single act + advance(N) pattern)."""
    forces = [f] + [0.0] * (steps - 1)
    return _sim(x0, v0, forces)


# --- Reset ---


def test_reset_returns_204_no_body():
    r = client.post("/reset")
    assert r.status_code == 204
    assert r.content == b""


def test_reset_sets_t_zero():
    reset()
    assert observe()["t"] == 0


def test_reset_randomizes_x():
    xs = set()
    for _ in range(20):
        reset()
        xs.add(observe()["x"])
    assert len(xs) > 1


def test_reset_within_bounds():
    for _ in range(50):
        reset()
        s = observe()
        assert -10.0 <= s["x"] <= 10.0


# --- Act ---


def test_act_returns_204():
    reset()
    r = act("A", 1.0)
    assert r.status_code == 204
    assert r.content == b""


def test_act_does_not_advance_time():
    reset()
    s1 = observe()
    act("A", 2.0)
    assert observe() == s1


def test_act_unknown_action_422():
    reset()
    assert act("B", 1.0).status_code == 422
    assert act("Z", 1.0).status_code == 422


def test_act_clamps_high():
    set_state(0.0)
    act("A", 100.0)
    advance(1)
    ex, _ = _sim_constant(0.0, 0.0, 5.0, 1)
    assert abs(observe()["x"] - ex) < 1e-9


def test_act_clamps_low():
    set_state(0.0)
    act("A", -100.0)
    advance(1)
    ex, _ = _sim_constant(0.0, 0.0, -5.0, 1)
    assert abs(observe()["x"] - ex) < 1e-9


def test_act_overwrites_pending():
    set_state(0.0)
    act("A", 1.0)
    act("A", 3.0)
    advance(1)
    ex, _ = _sim_constant(0.0, 0.0, 3.0, 1)
    assert abs(observe()["x"] - ex) < 1e-9


# --- Advance ---


def test_advance_returns_204():
    reset()
    r = advance(1)
    assert r.status_code == 204
    assert r.content == b""


def test_advance_increments_time():
    reset()
    advance(5)
    assert observe()["t"] == 5


def test_advance_invalid_steps():
    reset()
    assert advance(0).status_code == 422
    assert advance(-1).status_code == 422


# --- Observe ---


def test_observe_returns_x_t():
    reset()
    s = observe()
    assert "x" in s and "t" in s


def test_observe_is_idempotent():
    reset()
    act("A", 2.0)
    advance(3)
    assert observe() == observe()


# --- Predict ---


def test_predict_returns_204():
    reset()
    r = client.post("/predict", json={"x": 1.0})
    assert r.status_code == 204
    assert r.content == b""


# --- Physics: force + drag ---


def test_single_force_step():
    """One tick with force: v = 0 + f - 0 = f, x = 0 + f."""
    set_state(0.0)
    act("A", 3.0)
    advance(1)
    s = observe()
    assert abs(s["x"] - 3.0) < 1e-9
    assert s["t"] == 1


def test_force_not_persistent():
    """Force only applies on the tick it was set. Second tick has f=0."""
    set_state(0.0)
    act("A", 3.0)
    advance(1)
    # v after tick 1: 0 + 3.0 - 0 = 3.0, x = 3.0
    advance(1)
    # v after tick 2: 3.0 + 0 - 0.3*3.0 = 2.1, x = 3.0 + 2.1 = 5.1
    s = observe()
    ev = 3.0 + 0.0 - K * 3.0  # 2.1
    ex = 3.0 + ev  # 5.1
    assert abs(s["x"] - ex) < 1e-9
    assert s["t"] == 2


def test_force_consumed_within_multi_advance():
    """advance(N) only applies pending force on first tick."""
    set_state(0.0)
    act("A", 3.0)
    advance(3)
    ex, _ = _sim_constant(0.0, 0.0, 3.0, 3)
    assert abs(observe()["x"] - ex) < 1e-9


def test_drag_decelerates():
    """With no force, velocity decays by factor (1-K) each tick."""
    set_state(0.0, 10.0)  # start with v=10
    advance(1)
    # v = 10 + 0 - 0.3*10 = 7.0, x = 0 + 7 = 7
    s = observe()
    assert abs(s["x"] - 7.0) < 1e-9


def test_drag_decay_sequence():
    """Velocity decays: v(n) = v0 * (1-K)^n when f=0."""
    set_state(0.0, 5.0)
    cx, cv = 0.0, 5.0
    for i in range(10):
        advance(1)
        cv = cv - K * cv  # = cv * 0.7
        cx = cx + cv
        s = observe()
        assert abs(s["x"] - cx) < 1e-6, f"tick {i+1}: expected x={cx}, got {s['x']}"


def test_terminal_velocity():
    """Under constant force f, velocity converges to f/K."""
    set_state(0.0)
    f = 3.0
    terminal = f / K  # 10.0
    cv = 0.0
    for _ in range(200):
        act("A", f)
        advance(1)
        cv = cv + f - K * cv
    # After many steps, v should be very close to terminal
    assert abs(cv - terminal) < 0.01


def test_zero_velocity_default():
    """No action → no movement (if v=0)."""
    reset()
    s0 = observe()
    advance(5)
    s1 = observe()
    assert abs(s1["x"] - s0["x"]) < 1e-9


def test_braking():
    """Apply force then reverse to brake."""
    set_state(0.0)
    act("A", 5.0)
    advance(1)
    # v = 5.0, x = 5.0
    act("A", -5.0)
    advance(1)
    # v = 5.0 + (-5.0) - 0.3*5.0 = -1.5, x = 5.0 + (-1.5) = 3.5
    s = observe()
    assert abs(s["x"] - 3.5) < 1e-9


def test_multi_step_act_advance_sequence():
    """Repeated act+advance(1) applies force each tick."""
    set_state(0.0)
    forces = [2.0, 2.0, 2.0, 0.0, 0.0]
    for f in forces:
        act("A", f)
        advance(1)
    ex, _ = _sim(0.0, 0.0, forces)
    assert abs(observe()["x"] - ex) < 1e-9


def test_advance_multi_vs_singles():
    """advance(N) with one act == act + advance(1) then (N-1) x advance(1)."""
    set_state(5.0)
    act("A", 2.0)
    advance(5)
    bulk = observe()

    set_state(5.0)
    act("A", 2.0)
    advance(1)
    for _ in range(4):
        advance(1)
    singles = observe()

    assert abs(bulk["x"] - singles["x"]) < 1e-9


def test_no_act_between_advances():
    """Without /act, each advance tick has f=0."""
    set_state(0.0, 4.0)
    advance(5)
    ex, _ = _sim(0.0, 4.0, [0.0] * 5)
    assert abs(observe()["x"] - ex) < 1e-9


def test_negative_x_start():
    set_state(-8.0)
    act("A", 4.0)
    advance(1)
    ex, _ = _sim(-8.0, 0.0, [4.0])
    assert abs(observe()["x"] - ex) < 1e-9


def test_negative_force():
    set_state(5.0)
    act("A", -3.0)
    advance(1)
    ex, _ = _sim(5.0, 0.0, [-3.0])
    assert abs(observe()["x"] - ex) < 1e-9


def test_sim_many_random_trajectories():
    """Fuzz: random starting conditions and force sequences."""
    import random as rnd
    rng = rnd.Random(42)

    for _ in range(100):
        sx = rng.uniform(-10, 10)
        sv = rng.uniform(-5, 5)
        n_steps = rng.randint(1, 30)
        forces = [rng.uniform(-5, 5) for _ in range(n_steps)]

        set_state(sx, sv)
        for f in forces:
            act("A", f)
            advance(1)
        s = observe()

        ex, _ = _sim(sx, sv, forces)
        assert abs(s["x"] - ex) < 1e-6, (
            f"x mismatch: {s['x']} vs {ex} "
            f"(start x={sx} v={sv} forces={forces[:3]}...)"
        )


def test_goal1_feasibility():
    """Verify that reaching x=50 at t=20 is possible with max force."""
    set_state(0.0)
    for _ in range(20):
        act("A", 5.0)
        advance(1)
    s = observe()
    assert s["x"] > 50.0, f"Max force for 20 steps should exceed 50, got {s['x']}"


def test_prediction_scenario():
    """Run the Goal 3 prediction experiment and verify against sim."""
    set_state(0.0)
    forces = [2.0] * 15 + [0.0] * 15
    for f in forces:
        act("A", f)
        advance(1)
    s = observe()
    ex, _ = _sim(0.0, 0.0, forces)
    assert abs(s["x"] - ex) < 1e-6
    assert s["t"] == 30
