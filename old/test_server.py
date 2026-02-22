from fastapi.testclient import TestClient

from server import app

client = TestClient(app)


def reset():
    return client.post("/reset").json()


def test_reset():
    data = reset()
    assert data == {"x": 0.0, "t": 0}


def test_act_basic():
    reset()
    data = client.post("/act", json={"action": "A", "value": 2.0}).json()
    assert data["before"] == {"x": 0.0, "t": 0}
    assert data["after"] == {"x": 2.0, "t": 1}


def test_act_clamping():
    reset()
    data = client.post("/act", json={"action": "A", "value": 10.0}).json()
    assert data["after"]["x"] == 5.0

    reset()
    data = client.post("/act", json={"action": "A", "value": -10.0}).json()
    assert data["after"]["x"] == -5.0


def test_act_unknown_action():
    reset()
    data = client.post("/act", json={"action": "B", "value": 1.0}).json()
    assert "error" in data


def test_observe():
    reset()
    client.post("/act", json={"action": "A", "value": 3.0})
    data = client.post("/observe", json={"steps": 3}).json()
    assert len(data["states"]) == 3
    assert data["states"][0] == {"x": 6.0, "t": 2}
    assert data["states"][1] == {"x": 9.0, "t": 3}
    assert data["states"][2] == {"x": 12.0, "t": 4}


def test_advance():
    reset()
    client.post("/act", json={"action": "A", "value": 1.0})
    data = client.post("/advance", json={"steps": 5}).json()
    assert data == {"x": 6.0, "t": 6}
    assert "states" not in data


def test_history():
    reset()
    client.post("/act", json={"action": "A", "value": 2.0})
    client.post("/observe", json={"steps": 2})
    history = client.get("/history").json()
    assert len(history) == 3
    assert history[0]["action"] == {"name": "A", "value": 2.0}
    assert history[1]["action"] is None
    assert history[2]["action"] is None


def test_physics_consistency():
    reset()
    client.post("/act", json={"action": "A", "value": 4.0})
    data = client.post("/observe", json={"steps": 5}).json()
    all_states = [{"x": 4.0, "t": 1}] + data["states"]
    v = 4.0
    dt = 1.0
    for i in range(len(all_states) - 1):
        expected_x = all_states[i]["x"] + v * dt
        assert abs(all_states[i + 1]["x"] - expected_x) < 1e-9
        assert all_states[i + 1]["t"] == all_states[i]["t"] + 1
