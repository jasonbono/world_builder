import math

from fastapi.testclient import TestClient

from server import app

client = TestClient(app)


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


def set_state(s_theta=0.0, s_omega=0.0, s_r=1.0):
    """Force a deterministic state for testing."""
    import server
    reset()
    server.theta = s_theta
    server.omega = s_omega
    server.r = s_r
    server.x = s_r * math.sin(s_theta)
    server.t = 0
    server.pending_a = None
    server.pending_b = None


def _sim(theta0, omega0, r0, actions):
    """Pure-Python reference simulation.

    actions: list of (a_val_or_none, b_val_or_none) tuples, one per tick.
    """
    theta, omega, r = theta0, omega0, r0
    for a_val, b_val in actions:
        if a_val is not None:
            omega += a_val
        if b_val is not None:
            r += b_val
            r = max(0.1, min(10.0, r))
        theta += omega
        x = r * math.sin(theta)
    return x, theta, omega, r


# --- Reset ---


def test_reset_returns_204_no_body():
    r = client.post("/reset")
    assert r.status_code == 204
    assert r.content == b""


def test_reset_sets_t_zero():
    reset()
    assert observe()["t"] == 0


def test_reset_x_is_zero():
    reset()
    assert observe()["x"] == 0.0


def test_reset_is_deterministic():
    reset()
    s1 = observe()
    reset()
    s2 = observe()
    assert s1 == s2


# --- Act ---


def test_act_a_returns_204():
    reset()
    r = act("A", 0.5)
    assert r.status_code == 204
    assert r.content == b""


def test_act_b_returns_204():
    reset()
    r = act("B", 1.0)
    assert r.status_code == 204
    assert r.content == b""


def test_act_does_not_advance_time():
    reset()
    s1 = observe()
    act("A", 0.5)
    act("B", 1.0)
    assert observe() == s1


def test_act_unknown_action_422():
    reset()
    assert act("C", 1.0).status_code == 422
    assert act("Z", 1.0).status_code == 422


def test_act_a_clamps_high():
    set_state()
    act("A", 100.0)
    advance(1)
    # omega = 0 + 1.0 (clamped), theta = 1.0, x = sin(1.0)
    s = observe()
    assert abs(s["x"] - math.sin(1.0)) < 1e-9


def test_act_a_clamps_low():
    set_state()
    act("A", -100.0)
    advance(1)
    # omega = 0 + (-1.0), theta = -1.0, x = sin(-1.0)
    s = observe()
    assert abs(s["x"] - math.sin(-1.0)) < 1e-9


def test_act_b_clamps_high():
    set_state()
    act("B", 100.0)
    act("A", 0.5)
    advance(1)
    # r = 1.0 + 2.0 (clamped) = 3.0, omega = 0.5, theta = 0.5
    s = observe()
    assert abs(s["x"] - 3.0 * math.sin(0.5)) < 1e-9


def test_act_b_clamps_low():
    set_state()
    act("B", -100.0)
    act("A", 0.5)
    advance(1)
    # r = 1.0 + (-2.0) = -1.0 -> clamped to 0.1
    s = observe()
    assert abs(s["x"] - 0.1 * math.sin(0.5)) < 1e-9


def test_act_a_overwrites_pending():
    set_state()
    act("A", 0.3)
    act("A", 0.7)
    advance(1)
    s = observe()
    assert abs(s["x"] - math.sin(0.7)) < 1e-9


def test_act_b_overwrites_pending():
    set_state()
    act("A", 1.0)
    act("B", 0.5)
    act("B", 1.5)
    advance(1)
    # r = 1.0 + 1.5 = 2.5
    s = observe()
    assert abs(s["x"] - 2.5 * math.sin(1.0)) < 1e-9


def test_both_actions_independent():
    set_state()
    act("A", 0.5)
    act("B", 1.0)
    advance(1)
    # omega = 0.5, r = 2.0, theta = 0.5
    s = observe()
    assert abs(s["x"] - 2.0 * math.sin(0.5)) < 1e-9


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


def test_no_action_no_movement():
    reset()
    advance(10)
    s = observe()
    assert s["x"] == 0.0
    assert s["t"] == 10


def test_pending_consumed_after_first_tick():
    """advance(N) only applies pending action on first tick."""
    set_state()
    act("A", 0.5)
    advance(3)
    # tick 1: omega=0.5, theta=0.5
    # tick 2: theta=1.0 (no new action)
    # tick 3: theta=1.5
    s = observe()
    assert abs(s["x"] - math.sin(1.5)) < 1e-9


# --- Observe ---


def test_observe_returns_x_t():
    reset()
    s = observe()
    assert "x" in s and "t" in s


def test_observe_is_idempotent():
    reset()
    act("A", 0.3)
    advance(5)
    assert observe() == observe()


# --- Predict ---


def test_predict_returns_204():
    reset()
    r = client.post("/predict", json={"x": 1.0})
    assert r.status_code == 204
    assert r.content == b""


# --- Physics: oscillator ---


def test_basic_oscillation():
    """A single A action starts oscillation."""
    set_state()
    act("A", 0.5)
    advance(1)
    s1 = observe()
    assert s1["x"] != 0.0  # now oscillating

    # After many ticks, x oscillates (doesn't stay at initial value)
    advance(5)
    vals = set()
    for _ in range(10):
        advance(1)
        vals.add(round(observe()["x"], 4))
    assert len(vals) > 1  # x takes on different values (oscillating)


def test_omega_accumulates():
    """Multiple A actions add to omega."""
    set_state()
    act("A", 0.3)
    advance(1)
    act("A", 0.2)
    advance(1)
    # omega after tick 1: 0.3, theta = 0.3
    # omega after tick 2: 0.3 + 0.2 = 0.5, theta = 0.3 + 0.5 = 0.8
    s = observe()
    assert abs(s["x"] - math.sin(0.8)) < 1e-9


def test_r_changes_amplitude():
    """B action changes amplitude."""
    set_state()
    act("A", 0.5)
    act("B", 2.0)
    advance(1)
    # r = 3.0, omega = 0.5, theta = 0.5
    s = observe()
    assert abs(s["x"] - 3.0 * math.sin(0.5)) < 1e-9


def test_r_clamped_min():
    set_state(s_r=0.5)
    act("B", -2.0)
    act("A", 1.0)
    advance(1)
    # r = 0.5 + (-2.0) = -1.5 -> clamped to 0.1
    s = observe()
    assert abs(s["x"] - 0.1 * math.sin(1.0)) < 1e-9


def test_r_clamped_max():
    set_state(s_r=9.0)
    act("B", 2.0)
    act("A", 1.0)
    advance(1)
    # r = 9.0 + 2.0 = 11.0 -> clamped to 10.0
    s = observe()
    assert abs(s["x"] - 10.0 * math.sin(1.0)) < 1e-9


def test_x_bounded_by_r():
    """x should always be in [-r, r]."""
    set_state()
    act("A", 0.7)
    act("B", 1.5)
    for _ in range(100):
        advance(1)
        s = observe()
        assert abs(s["x"]) <= 2.5 + 1e-9  # r = 1.0 + 1.5 = 2.5


def test_negative_omega():
    set_state()
    act("A", -0.5)
    advance(1)
    s = observe()
    assert abs(s["x"] - math.sin(-0.5)) < 1e-9


def test_omega_persists():
    """Once set, omega keeps advancing theta each tick."""
    set_state()
    act("A", 0.4)
    advance(1)
    # theta = 0.4
    advance(1)
    # theta = 0.8 (omega=0.4 persists)
    advance(1)
    # theta = 1.2
    s = observe()
    assert abs(s["x"] - math.sin(1.2)) < 1e-9


def test_long_trajectory_matches_sim():
    set_state()
    actions = [(0.3, 1.0)] + [(None, None)] * 9 + [(0.1, -0.5)] + [(None, None)] * 19
    for a_val, b_val in actions:
        if a_val is not None:
            act("A", a_val)
        if b_val is not None:
            act("B", b_val)
        advance(1)
    s = observe()
    ex, _, _, _ = _sim(0.0, 0.0, 1.0, actions)
    assert abs(s["x"] - ex) < 1e-6


def test_advance_multi_vs_singles():
    """advance(N) == N * advance(1) when only first tick has action."""
    set_state()
    act("A", 0.5)
    act("B", 1.0)
    advance(10)
    bulk = observe()

    set_state()
    act("A", 0.5)
    act("B", 1.0)
    advance(1)
    for _ in range(9):
        advance(1)
    singles = observe()

    assert abs(bulk["x"] - singles["x"]) < 1e-9


def test_sim_many_random_trajectories():
    """Fuzz: random action sequences verified against reference sim."""
    import random as rnd
    rng = rnd.Random(42)

    for _ in range(50):
        set_state()
        n_steps = rng.randint(5, 40)
        actions = []
        for _ in range(n_steps):
            a = rng.uniform(-1, 1) if rng.random() < 0.3 else None
            b = rng.uniform(-2, 2) if rng.random() < 0.2 else None
            actions.append((a, b))

        for a_val, b_val in actions:
            if a_val is not None:
                act("A", a_val)
            if b_val is not None:
                act("B", b_val)
            advance(1)
        s = observe()

        ex, _, _, _ = _sim(0.0, 0.0, 1.0, actions)
        assert abs(s["x"] - ex) < 1e-6, (
            f"x mismatch: {s['x']} vs {ex} after {n_steps} steps"
        )


def test_goal1_feasibility():
    """Reaching x=5.0 at t=50 is possible."""
    set_state()
    # Set r=5 (B=4.0, but clamped to 2.0, so need two B actions)
    # First set r to 3.0, then 5.0
    act("B", 2.0)
    advance(1)
    act("B", 2.0)
    advance(1)
    # r=5.0, omega=0, theta=0, t=2
    # Now need theta = pi/2 at t=50, so 48 more ticks
    # omega * 48 = pi/2 -> omega = pi/96
    omega_needed = math.pi / 96
    act("A", omega_needed)
    advance(48)
    s = observe()
    assert s["t"] == 50
    assert abs(s["x"] - 5.0) < 0.2, f"x={s['x']}, expected ~5.0"


def test_goal2_prediction():
    """Run the goal 2 scenario and verify."""
    set_state()
    act("A", 0.2)
    advance(1)
    advance(29)
    s = observe()
    assert s["t"] == 30
    # x = sin(0.2 * 30) = sin(6.0)
    expected = math.sin(6.0)
    assert abs(s["x"] - expected) < 1e-6


def test_goal3_feasibility():
    """Reaching x=0 at t=40 AND x=3 at t=50 is possible."""
    set_state()
    # Need r=3, omega=pi/20
    # B capped at 2.0 per call, so one call gets r to 3.0
    act("B", 2.0)
    act("A", math.pi / 20)
    advance(40)
    s40 = observe()
    assert s40["t"] == 40
    assert abs(s40["x"]) < 0.1, f"x at t=40: {s40['x']}"

    advance(10)
    s50 = observe()
    assert s50["t"] == 50
    assert abs(s50["x"] - 3.0) < 0.2, f"x at t=50: {s50['x']}"
