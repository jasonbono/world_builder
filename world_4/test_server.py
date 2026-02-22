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


def set_state(sx, sy, svx=0.0, svy=0.0):
    """Helper to force a deterministic state for testing."""
    import server
    reset()
    server.x = sx
    server.y = sy
    server.vx = svx
    server.vy = svy
    server.t = 0
    server.pending_a = None
    server.pending_b = None


# --- Reset ---


def test_reset_returns_204_no_body():
    r = client.post("/reset")
    assert r.status_code == 204
    assert r.content == b""


def test_reset_sets_t_zero():
    reset()
    assert observe()["t"] == 0


def test_reset_randomizes_x_and_y():
    xs, ys = set(), set()
    for _ in range(20):
        reset()
        s = observe()
        xs.add(s["x"])
        ys.add(s["y"])
    assert len(xs) > 1
    assert len(ys) > 1


def test_reset_within_bounds():
    for _ in range(50):
        reset()
        s = observe()
        assert 0.0 <= s["x"] <= 20.0
        assert 0.0 <= s["y"] <= 20.0


# --- Act ---


def test_act_a_returns_204():
    reset()
    r = act("A", 1.0)
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
    act("A", 2.0)
    act("B", 1.0)
    assert observe() == s1


def test_act_unknown_action_422():
    reset()
    assert act("Z", 1.0).status_code == 422


def test_act_clamps_high():
    set_state(10.0, 0.0)
    act("A", 100.0)
    advance(1)
    # ALPHA mode (x>=y): x += 5.0*1 = 15.0
    assert abs(observe()["x"] - 15.0) < 1e-9


def test_act_clamps_low():
    set_state(10.0, 0.0)
    act("A", -100.0)
    advance(1)
    # ALPHA mode: x += -5.0*1 = 5.0
    assert abs(observe()["x"] - 5.0) < 1e-9


def test_act_overwrites_pending():
    set_state(10.0, 0.0)
    act("A", 1.0)
    act("A", 3.0)
    advance(1)
    # ALPHA mode: x += 3.0 = 13.0
    assert abs(observe()["x"] - 13.0) < 1e-9


def test_both_actions_set_independently():
    set_state(10.0, 0.0)
    act("A", 2.0)
    act("B", 3.0)
    advance(1)
    s = observe()
    # ALPHA mode: x += 2.0 = 12.0, y += 3.0 * 0.5 = 1.5
    assert abs(s["x"] - 12.0) < 1e-9
    assert abs(s["y"] - 1.5) < 1e-9


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


def test_pending_cleared_after_advance():
    set_state(10.0, 0.0)
    act("A", 2.0)
    advance(1)
    # vx=2 persists, but no new pending
    advance(1)
    s = observe()
    # Two steps in ALPHA: x = 10 + 2 + 2 = 14
    assert abs(s["x"] - 14.0) < 1e-9


# --- Observe ---


def test_observe_returns_x_y_t():
    reset()
    s = observe()
    assert "x" in s and "y" in s and "t" in s


def test_observe_is_idempotent():
    reset()
    act("A", 2.0)
    advance(3)
    assert observe() == observe()


# --- Predict ---


def test_predict_returns_204():
    reset()
    r = client.post("/predict", json={"x": 1.0, "y": 2.0})
    assert r.status_code == 204
    assert r.content == b""


# --- Physics: mode switching ---


def _sim(x0, y0, vx, vy, steps):
    """Pure-Python reference simulation."""
    cx, cy = x0, y0
    for _ in range(steps):
        if cx >= cy:
            cx += vx
            cy += vy * 0.5
        else:
            cx += vx * 0.5
            cy += vy
    return cx, cy


def test_alpha_mode_basic():
    """When x >= y, vx applies fully, vy is damped."""
    set_state(10.0, 0.0)
    act("A", 2.0)
    act("B", 4.0)
    advance(1)
    s = observe()
    # ALPHA: x += 2 = 12, y += 4*0.5 = 2
    assert abs(s["x"] - 12.0) < 1e-9
    assert abs(s["y"] - 2.0) < 1e-9


def test_beta_mode_basic():
    """When x < y, vx is damped, vy applies fully."""
    set_state(0.0, 10.0)
    act("A", 4.0)
    act("B", 2.0)
    advance(1)
    s = observe()
    # BETA: x += 4*0.5 = 2, y += 2 = 12
    assert abs(s["x"] - 2.0) < 1e-9
    assert abs(s["y"] - 12.0) < 1e-9


def test_mode_switches_mid_trajectory():
    """Trajectory that crosses from ALPHA to BETA."""
    # Start x=10, y=5. vx=-2, vy=3.
    # t=0: ALPHA (10>=5): x=10-2=8, y=5+3*0.5=6.5
    # t=1: ALPHA (8>=6.5): x=8-2=6, y=6.5+1.5=8
    # t=2: BETA (6<8): x=6-1=5, y=8+3=11
    # t=3: BETA (5<11): x=5-1=4, y=11+3=14
    set_state(10.0, 5.0)
    act("A", -2.0)
    act("B", 3.0)
    advance(4)
    s = observe()
    assert abs(s["x"] - 4.0) < 1e-9
    assert abs(s["y"] - 14.0) < 1e-9
    assert s["t"] == 4


def test_mode_switch_boundary_exact():
    """When x == y, mode is ALPHA (x >= y is true)."""
    set_state(5.0, 5.0)
    act("A", 1.0)
    act("B", 1.0)
    advance(1)
    s = observe()
    # ALPHA: x += 1 = 6, y += 0.5 = 5.5
    assert abs(s["x"] - 6.0) < 1e-9
    assert abs(s["y"] - 5.5) < 1e-9


def test_zero_velocity_default():
    reset()
    s0 = observe()
    advance(5)
    s1 = observe()
    assert abs(s1["x"] - s0["x"]) < 1e-9
    assert abs(s1["y"] - s0["y"]) < 1e-9


def test_long_trajectory_matches_sim():
    """30-step trajectory verified against reference sim."""
    set_state(5.0, 12.0)
    act("A", 3.0)
    act("B", -1.5)
    advance(30)
    ex, ey = _sim(5.0, 12.0, 3.0, -1.5, 30)
    s = observe()
    assert abs(s["x"] - ex) < 1e-9
    assert abs(s["y"] - ey) < 1e-9


def test_long_trajectory_negative():
    set_state(15.0, 3.0)
    act("A", -2.0)
    act("B", 4.0)
    advance(30)
    ex, ey = _sim(15.0, 3.0, -2.0, 4.0, 30)
    s = observe()
    assert abs(s["x"] - ex) < 1e-9
    assert abs(s["y"] - ey) < 1e-9


def test_multi_step_equals_singles():
    """advance(N) == N * advance(1)."""
    set_state(7.0, 3.0)
    act("A", 1.5)
    act("B", -0.5)
    advance(10)
    bulk = observe()

    set_state(7.0, 3.0)
    act("A", 1.5)
    act("B", -0.5)
    for _ in range(10):
        advance(1)
    singles = observe()

    assert abs(bulk["x"] - singles["x"]) < 1e-9
    assert abs(bulk["y"] - singles["y"]) < 1e-9


def test_velocity_persists_across_advances():
    set_state(10.0, 0.0)
    act("A", 1.0)
    act("B", 0.0)
    advance(3)
    # All ALPHA (x stays ahead): x = 10+1+1+1 = 13, y = 0
    s = observe()
    assert abs(s["x"] - 13.0) < 1e-9
    assert abs(s["y"] - 0.0) < 1e-9


def test_only_action_a_sets_vx():
    """Action B should not affect vx."""
    set_state(10.0, 0.0)
    act("B", 5.0)
    advance(3)
    s = observe()
    # vx=0, vy=5, ALPHA for all: x stays 10, y grows 0 + 2.5 + 2.5 + 2.5 = 7.5
    assert abs(s["x"] - 10.0) < 1e-9
    assert abs(s["y"] - 7.5) < 1e-9


def test_only_action_b_sets_vy():
    """Action A should not affect vy."""
    set_state(0.0, 10.0)
    act("A", 5.0)
    advance(3)
    # BETA for t=0: x += 5*0.5=2.5, y stays 10 → x=2.5, y=10
    # BETA for t=1: x += 2.5=5, y=10 → x=5, y=10
    # BETA for t=2: x += 2.5=7.5, y=10 → x=7.5, y=10
    s = observe()
    assert abs(s["x"] - 7.5) < 1e-9
    assert abs(s["y"] - 10.0) < 1e-9


def test_repeated_mode_switches():
    """Trajectory that oscillates between modes."""
    # vx=-1, vy=2. Start x=10, y=9.
    # t=0: ALPHA (10>=9):   x=9,  y=10
    # t=1: BETA  (9<10):    x=8.5, y=12
    # t=2: BETA  (8.5<12):  x=8,  y=14
    # t=3: BETA  (8<14):    x=7.5, y=16
    set_state(10.0, 9.0)
    act("A", -1.0)
    act("B", 2.0)
    advance(4)
    s = observe()
    assert abs(s["x"] - 7.5) < 1e-9
    assert abs(s["y"] - 16.0) < 1e-9


def test_sim_many_random_trajectories():
    """Fuzz: many random starting conditions verified against sim."""
    import random as rnd
    rng = rnd.Random(42)

    for _ in range(100):
        sx = rng.uniform(0, 20)
        sy = rng.uniform(0, 20)
        svx = rng.uniform(-5, 5)
        svy = rng.uniform(-5, 5)
        steps = rng.randint(1, 50)

        set_state(sx, sy)
        act("A", svx)
        act("B", svy)
        advance(steps)
        s = observe()

        ex, ey = _sim(sx, sy, svx, svy, steps)
        assert abs(s["x"] - ex) < 1e-6, f"x mismatch: {s['x']} vs {ex} (start {sx},{sy} v={svx},{svy} steps={steps})"
        assert abs(s["y"] - ey) < 1e-6, f"y mismatch: {s['y']} vs {ey} (start {sx},{sy} v={svx},{svy} steps={steps})"
