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
        assert -10.0 <= x <= 10.0


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
    import server
    server.x = 0.0
    server.v = 0.0
    server.t = 0
    server.pending_action = None

    act("A", 100.0)
    advance(1)
    # t=0: m=1, x += 5.0*1 = 5.0
    assert abs(observe()["x"] - 5.0) < 1e-9


def test_act_clamps_low():
    reset()
    import server
    server.x = 0.0
    server.v = 0.0
    server.t = 0
    server.pending_action = None

    act("A", -100.0)
    advance(1)
    # t=0: m=1, x += -5.0*1 = -5.0
    assert abs(observe()["x"] - (-5.0)) < 1e-9


def test_act_overwrites_pending():
    reset()
    import server
    server.x = 0.0
    server.v = 0.0
    server.t = 0
    server.pending_action = None

    act("A", 1.0)
    act("A", 3.0)
    advance(1)
    # t=0: m=1, x += 3.0*1 = 3.0
    assert abs(observe()["x"] - 3.0) < 1e-9


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
    import server
    server.x = 0.0
    server.v = 0.0
    server.t = 0
    server.pending_action = None

    act("A", 2.0)
    advance(1)
    x1 = observe()["x"]
    # t=0: m=1, x += 2*1 = 2.0
    assert abs(x1 - 2.0) < 1e-9

    advance(1)
    x2 = observe()["x"]
    # t=1: m=2, x += 2*2 = 4.0 → x = 6.0
    assert abs(x2 - 6.0) < 1e-9


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


# --- Physics: multiplier cycle ---


def _sim(x0, v, steps):
    """Pure-Python simulation for test verification."""
    x = x0
    for step in range(steps):
        m = (step % 3) + 1
        x += v * m
    return x


def test_multiplier_cycle_three_steps():
    """First three steps should use multipliers 1, 2, 3."""
    import server
    reset()
    server.x = 0.0
    server.v = 0.0
    server.t = 0
    server.pending_action = None

    act("A", 1.0)

    advance(1)
    assert abs(observe()["x"] - 1.0) < 1e-9   # m=1

    advance(1)
    assert abs(observe()["x"] - 3.0) < 1e-9   # m=2, +2 → 3

    advance(1)
    assert abs(observe()["x"] - 6.0) < 1e-9   # m=3, +3 → 6


def test_multiplier_cycle_repeats():
    """Steps 3-5 should repeat the 1, 2, 3 cycle."""
    import server
    reset()
    server.x = 0.0
    server.v = 0.0
    server.t = 0
    server.pending_action = None

    act("A", 1.0)
    advance(3)
    assert abs(observe()["x"] - 6.0) < 1e-9

    advance(1)
    assert abs(observe()["x"] - 7.0) < 1e-9   # m=1

    advance(1)
    assert abs(observe()["x"] - 9.0) < 1e-9   # m=2

    advance(1)
    assert abs(observe()["x"] - 12.0) < 1e-9  # m=3


def test_same_action_different_effect_by_time():
    """The same velocity produces different displacements depending on t."""
    import server
    reset()
    server.x = 0.0
    server.v = 0.0
    server.t = 0
    server.pending_action = None

    act("A", 2.0)
    advance(1)
    d0 = observe()["x"]  # t=0: m=1, d=2

    advance(1)
    d1 = observe()["x"] - d0  # t=1: m=2, d=4

    advance(1)
    d2 = observe()["x"] - d0 - d1  # t=2: m=3, d=6

    assert abs(d0 - 2.0) < 1e-9
    assert abs(d1 - 4.0) < 1e-9
    assert abs(d2 - 6.0) < 1e-9


def test_zero_velocity_default():
    reset()
    x0 = observe()["x"]
    advance(5)
    assert abs(observe()["x"] - x0) < 1e-9


def test_negative_velocity():
    import server
    reset()
    server.x = 10.0
    server.v = 0.0
    server.t = 0
    server.pending_action = None

    act("A", -1.0)
    advance(3)
    # sum of multipliers for t=0,1,2: 1+2+3 = 6 → x = 10 - 6 = 4
    assert abs(observe()["x"] - 4.0) < 1e-9


def test_long_trajectory():
    """Run 30 steps and verify against pure-Python sim."""
    import server
    reset()
    server.x = 5.0
    server.v = 0.0
    server.t = 0
    server.pending_action = None

    act("A", 2.5)
    advance(30)
    expected = _sim(5.0, 2.5, 30)
    actual = observe()["x"]
    assert abs(actual - expected) < 1e-9


def test_long_trajectory_negative():
    import server
    reset()
    server.x = 100.0
    server.v = 0.0
    server.t = 0
    server.pending_action = None

    act("A", -3.0)
    advance(30)
    expected = _sim(100.0, -3.0, 30)
    actual = observe()["x"]
    assert abs(actual - expected) < 1e-9


def test_velocity_persists_across_advances():
    """v should persist (and keep being multiplied) across separate advance calls."""
    import server
    reset()
    server.x = 0.0
    server.v = 0.0
    server.t = 0
    server.pending_action = None

    act("A", 1.0)
    advance(6)
    # two full cycles: (1+2+3) + (1+2+3) = 12
    assert abs(observe()["x"] - 12.0) < 1e-9


def test_goal1_exact_targeting():
    """From any start, v = (50 - x0) / 18 should reach x=50 at t=9."""
    import server

    for _ in range(20):
        reset()
        x0 = observe()["x"]
        # sum of multipliers for t=0..8: (1+2+3)*3 = 18
        v_needed = (50.0 - x0) / 18.0
        act("A", v_needed)
        advance(9)
        s = observe()
        assert abs(s["x"] - 50.0) < 1e-9
        assert s["t"] == 9


def test_multi_step_advance_equals_single_steps():
    """advance(6) should give same result as six advance(1) calls."""
    import server

    reset()
    server.x = 3.0
    server.v = 0.0
    server.t = 0
    server.pending_action = None
    act("A", 2.0)
    advance(6)
    x_bulk = observe()["x"]

    server.x = 3.0
    server.v = 0.0
    server.t = 0
    server.pending_action = None
    act("A", 2.0)
    for _ in range(6):
        advance(1)
    x_singles = observe()["x"]

    assert abs(x_bulk - x_singles) < 1e-9
