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
    assert abs(observe()["x"] - x0 - 5.0) < 1e-9


def test_act_clamps_low():
    reset()
    x0 = observe()["x"]
    act("A", -100.0)
    advance(1)
    assert abs(observe()["x"] - x0 - (-5.0)) < 1e-9


def test_act_overwrites_pending():
    reset()
    x0 = observe()["x"]
    act("A", 1.0)
    act("A", 4.0)
    advance(1)
    assert abs(observe()["x"] - x0 - 4.0) < 1e-9


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


# --- Physics ---


def test_constant_velocity():
    reset()
    x0 = observe()["x"]
    act("A", 2.5)
    positions = [x0]
    for _ in range(5):
        advance(1)
        positions.append(observe()["x"])
    for i in range(1, len(positions)):
        assert abs(positions[i] - positions[i - 1] - 2.5) < 1e-9


def test_zero_velocity_default():
    reset()
    x0 = observe()["x"]
    advance(5)
    assert abs(observe()["x"] - x0) < 1e-9


def test_velocity_persists_across_advances():
    reset()
    x0 = observe()["x"]
    act("A", 3.0)
    advance(1)
    x1 = observe()["x"]
    advance(1)
    x2 = observe()["x"]
    assert abs(x1 - x0 - 3.0) < 1e-9
    assert abs(x2 - x1 - 3.0) < 1e-9


def test_velocity_changes_with_new_action():
    reset()
    x0 = observe()["x"]
    act("A", 2.0)
    advance(1)
    x1 = observe()["x"]
    act("A", -1.0)
    advance(1)
    x2 = observe()["x"]
    assert abs(x1 - x0 - 2.0) < 1e-9
    assert abs(x2 - x1 - (-1.0)) < 1e-9


def test_multi_step_advance():
    reset()
    x0 = observe()["x"]
    act("A", 2.0)
    advance(10)
    assert abs(observe()["x"] - x0 - 20.0) < 1e-9
    assert observe()["t"] == 10
