import json
import logging

import paho.mqtt.client as mqtt

from app import config
from app.influx import is_valid_device_id, write_reading
from app.metrics import MESSAGES, WRITE_LATENCY
from app.models import Telemetry

logger = logging.getLogger(__name__)


def handle_message(topic: str, payload: bytes) -> bool:
    """Valide un message MQTT et l'écrit dans InfluxDB."""
    parts = topic.split("/")
    if len(parts) != 3 or not is_valid_device_id(parts[1]):
        logger.warning("Topic invalide : %s", topic)
        MESSAGES.labels(status="invalid_topic").inc()
        return False
    device_id = parts[1]

    try:
        reading = Telemetry.model_validate(json.loads(payload))
    except ValueError as exc:
        logger.warning("Payload invalide sur %s : %s", topic, exc)
        MESSAGES.labels(status="invalid_payload").inc()
        return False

    try:
        with WRITE_LATENCY.time():
            write_reading(device_id, reading)
    except Exception:
        logger.exception("Écriture InfluxDB impossible")
        MESSAGES.labels(status="influx_error").inc()
        return False

    MESSAGES.labels(status="ok").inc()
    logger.info("Mesure enregistrée pour %s", device_id)
    return True


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connecté à Mosquitto")
        client.subscribe(config.MQTT_TOPIC, qos=1)
    else:
        logger.error("Connexion MQTT refusée (code %s)", rc)


def on_message(client, userdata, msg):
    handle_message(msg.topic, msg.payload)


def create_client() -> mqtt.Client:
    client = mqtt.Client(client_id="fastapi-ingestor")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect_async(config.MQTT_HOST, config.MQTT_PORT, keepalive=60)
    client.loop_start()
    return client
