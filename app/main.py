import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Path, Query, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app import influx
from app.models import Telemetry
from app.mqtt_client import create_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mqtt = create_client()
    yield
    app.state.mqtt.loop_stop()
    app.state.mqtt.disconnect()
    influx.client.close()


app = FastAPI(title="Cloud-IoT API", lifespan=lifespan)


@app.get("/health")
def health():
    influx_ok = influx.ping()
    mqtt_client = getattr(app.state, "mqtt", None)
    mqtt_ok = bool(mqtt_client and mqtt_client.is_connected())
    return {
        "status": "ok" if influx_ok and mqtt_ok else "degraded",
        "influxdb": influx_ok,
        "mqtt": mqtt_ok,
    }


@app.post("/devices/{device_id}/readings", status_code=201)
def ingest(
    reading: Telemetry,
    device_id: str = Path(pattern=influx.DEVICE_ID_PATTERN),
):
    try:
        influx.write_reading(device_id, reading)
    except Exception:
        logger.exception("Écriture InfluxDB impossible")
        raise HTTPException(status_code=503, detail="InfluxDB indisponible")
    return {"device_id": device_id, "stored": True}


@app.get("/devices/{device_id}/readings")
def readings(
    device_id: str = Path(pattern=influx.DEVICE_ID_PATTERN),
    limit: int = Query(10, ge=1, le=100),
):
    try:
        data = influx.read_readings(device_id, limit)
    except Exception:
        logger.exception("Lecture InfluxDB impossible")
        raise HTTPException(status_code=503, detail="InfluxDB indisponible")
    return {"device_id": device_id, "count": len(data), "readings": data}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
