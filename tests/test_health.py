from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class FakeMqtt:
    def __init__(self, connected):
        self._connected = connected

    def is_connected(self):
        return self._connected


def test_health_ok(monkeypatch):
    monkeypatch.setattr("app.main.influx.ping", lambda: True)
    monkeypatch.setattr(app.state, "mqtt", FakeMqtt(True), raising=False)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "influxdb": True, "mqtt": True}


def test_health_degraded_when_influx_down(monkeypatch):
    monkeypatch.setattr("app.main.influx.ping", lambda: False)
    monkeypatch.setattr(app.state, "mqtt", FakeMqtt(True), raising=False)
    response = client.get("/health")
    body = response.json()
    assert body["status"] == "degraded"
    assert body["influxdb"] is False
