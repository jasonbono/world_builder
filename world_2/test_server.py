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


# --- Reset ---


def test_reset_returns_204_no_body():
    r = client.post("/reset")
    assert r.status_code == 204
    assert r.content == b""


def test_reset_sets_t_zero():
    reset()
    assert observe()["t"] == 0


def test_reset_randomizes_x():
    values = set()
    for _ in range(20):
        reset()
        values.add(observe()["x"])
    assert len(values) > 1


def test_reset_x_within_bounds():
    for _ in range(50):
        reset()
        x = observe()["x"]
        assert 5.0 <= x <= 45.0


# --- Act ---


def test_act_returns_204_no_body():
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
    assert act("Z", 1.0).status_code == 422


def test_act_clamps_high():
    reset()
    x0 = observe()["x"]
    act("A", 100.0)
    advance(1)
    assert abs(observe()["x"] - (x0 + 5.0)) < 1e-9


def test_act_clamps_low():
    reset()
    x0 = observe()["x"]
    act("A", -100.0)
    advance(1)
    assert abs(observe()["x"] - (x0 - 5.0)) < 1e-9


def test_act_overwrites_pending():
    reset()
    x0 = observe()["x"]
    act("A", 1.0)
    act("A", 3.0)
    advance(1)
    assert abs(observe()["x"] - (x0 + 3.0)) < 1e-9


# --- Advance ---


def test_advance_returns_204_no_body():
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


def test_pending_action_cleared_after_advance():
    reset()
    x0 = observe()["x"]
    act("A", 2.0)
    advance(1)
    x1 = observe()["x"]
    advance(1)
    x2 = observe()["x"]
    assert abs(x1 - x0 - 2.0) < 1e-9
    assert abs(x2 - x1 - 2.0) < 1e-9


# --- Observe ---


def test_observe_returns_x_and_t():
    reset()
    s = observe()
    assert "x" in s and "t" in s


def test_observe_is_idempotent():
    reset()
    act("A", 2.0)
    advance(3)
    assert observe() == observe()


# --- Predict ---


def test_predict_returns_204_no_body():
    reset()
    r = client.post("/predict", json={"x": 42.0})
    assert r.status_code == 204
    assert r.content == b""


# --- Physics: basic motion ---


def test_constant_velocity_no_bounce():
    """With a small velocity, the ball moves linearly without hitting walls."""
    reset()
    x0 = observe()["x"]
    act("A", 1.0)
    positions = [x0]
    for _ in range(5):
        advance(1)
        positions.append(observe()["x"])
    for i in range(1, len(positions)):
        assert abs(positions[i] - positions[i - 1] - 1.0) < 1e-9


def test_zero_velocity_default():
    reset()
    x0 = observe()["x"]
    advance(5)
    assert abs(observe()["x"] - x0) < 1e-9


def test_velocity_persists_across_advances():
    reset()
    x0 = observe()["x"]
    act("A", 1.0)
    advance(1)
    x1 = observe()["x"]
    advance(1)
    x2 = observe()["x"]
    assert abs(x1 - x0 - 1.0) < 1e-9
    assert abs(x2 - x1 - 1.0) < 1e-9


# --- Physics: bouncing ---


def _sim(x0, v, steps):
    """Pure-Python simulation of bouncing for test verification."""
    x = x0
    for _ in range(steps):
        x += v
        if x >= 50.0:
            x = 100.0 - x
            v = -v
        elif x <= 0.0:
            x = -x
            v = -v
    return x


def test_bounce_right_wall():
    """Ball moving right should reflect off the right wall."""
    reset()
    from server import x as _, WALL_HI
    import server

    server.x = 47.0
    server.v = 0.0
    server.t = 0
    server.pending_action = None

    act("A", 5.0)
    advance(1)
    s = observe()
    assert abs(s["x"] - 48.0) < 1e-9

    advance(1)
    s = observe()
    assert abs(s["x"] - 43.0) < 1e-9


def test_bounce_left_wall():
    """Ball moving left should reflect off the left wall."""
    reset()
    import server

    server.x = 3.0
    server.v = 0.0
    server.t = 0
    server.pending_action = None

    act("A", -5.0)
    advance(1)
    s = observe()
    assert abs(s["x"] - 2.0) < 1e-9

    advance(1)
    s = observe()
    assert abs(s["x"] - 7.0) < 1e-9


def test_multi_bounce_trajectory():
    """Run a long trajectory and verify against pure-Python sim."""
    reset()
    import server

    server.x = 10.0
    server.v = 0.0
    server.t = 0
    server.pending_action = None

    act("A", 4.0)
    advance(30)
    expected = _sim(10.0, 4.0, 30)
    actual = observe()["x"]
    assert abs(actual - expected) < 1e-9


def test_multi_bounce_negative_velocity():
    """Long trajectory with negative velocity."""
    reset()
    import server

    server.x = 40.0
    server.v = 0.0
    server.t = 0
    server.pending_action = None

    act("A", -3.5)
    advance(40)
    expected = _sim(40.0, -3.5, 40)
    actual = observe()["x"]
    assert abs(actual - expected) < 1e-9


def test_ball_stays_in_bounds():
    """x should always remain within [0, 50] regardless of velocity."""
    reset()
    import server

    for v_val in [-5.0, -3.0, -1.0, 1.0, 3.0, 5.0]:
        for x0 in [1.0, 10.0, 25.0, 40.0, 49.0]:
            server.x = x0
            server.v = 0.0
            server.t = 0
            server.pending_action = None
            act("A", v_val)
            advance(100)
            s = observe()
            assert 0.0 <= s["x"] <= 50.0, f"Out of bounds: x={s['x']} for x0={x0}, v={v_val}"


def test_velocity_reversal_on_bounce():
    """After bouncing off a wall, subsequent motion reverses direction."""
    reset()
    import server

    server.x = 48.0
    server.v = 0.0
    server.t = 0
    server.pending_action = None

    act("A", 5.0)
    advance(1)
    x1 = observe()["x"]
    assert abs(x1 - 47.0) < 1e-9

    advance(1)
    x2 = observe()["x"]
    assert x2 < x1


def test_exact_wall_hit():
    """Ball landing exactly on a wall should reflect."""
    reset()
    import server

    server.x = 45.0
    server.v = 0.0
    server.t = 0
    server.pending_action = None

    act("A", 5.0)
    advance(1)
    s = observe()
    assert abs(s["x"] - 50.0) < 1e-9 or abs(s["x"] - 50.0) < 1e-9

    advance(1)
    s2 = observe()
    assert s2["x"] < 50.0


def test_goal1_exact_targeting():
    """Verify the Goal 1 scenario: from any start, v = (25 - x0)/10 reaches 25 at t=10."""
    import server

    for _ in range(20):
        reset()
        x0 = observe()["x"]
        v_needed = (25.0 - x0) / 10.0
        act("A", v_needed)
        advance(10)
        s = observe()
        assert abs(s["x"] - 25.0) < 1e-9
        assert s["t"] == 10
