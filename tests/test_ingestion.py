import json

from fastapi.testclient import TestClient

from app.main import app
from app.mqtt_client import handle_message

client = TestClient(app)
TOPIC = "devices/esp32-01/telemetry"


def test_handle_message_valid(monkeypatch):
    saved = []
    monkeypatch.setattr("app.mqtt_client.write_reading", lambda d, r: saved.append(d))
    payload = json.dumps({"temperature": 23.4, "humidity": 55.2}).encode()
    assert handle_message(TOPIC, payload) is True
    assert saved == ["esp32-01"]


def test_handle_message_invalid_values(monkeypatch):
    saved = []
    monkeypatch.setattr("app.mqtt_client.write_reading", lambda d, r: saved.append(d))
    assert handle_message(TOPIC, b'{"temperature": 500}') is False
    assert saved == []


def test_handle_message_not_json(monkeypatch):
    monkeypatch.setattr("app.mqtt_client.write_reading", lambda d, r: None)
    assert handle_message(TOPIC, b"pas du json") is False


def test_handle_message_bad_topic(monkeypatch):
    monkeypatch.setattr("app.mqtt_client.write_reading", lambda d, r: None)
    payload = b'{"temperature": 20, "humidity": 50}'
    assert handle_message("devices/telemetry", payload) is False


def test_handle_message_influx_error(monkeypatch):
    def boom(device_id, reading):
        raise RuntimeError("influx down")

    monkeypatch.setattr("app.mqtt_client.write_reading", boom)
    payload = b'{"temperature": 20, "humidity": 50}'
    assert handle_message(TOPIC, payload) is False


def test_post_reading_stores(monkeypatch):
    saved = []
    monkeypatch.setattr("app.main.influx.write_reading", lambda d, r: saved.append(d))
    response = client.post(
        "/devices/esp32-01/readings",
        json={"temperature": 21.5, "humidity": 40},
    )
    assert response.status_code == 201
    assert saved == ["esp32-01"]


def test_post_reading_invalid_payload():
    response = client.post("/devices/esp32-01/readings", json={"temperature": 500})
    assert response.status_code == 422
