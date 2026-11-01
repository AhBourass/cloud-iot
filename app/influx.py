import re

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from app import config
from app.models import Telemetry

DEVICE_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"
_DEVICE_ID_RE = re.compile(DEVICE_ID_PATTERN)

client = InfluxDBClient(
    url=config.INFLUX_URL,
    token=config.INFLUX_TOKEN,
    org=config.INFLUX_ORG,
)
write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()


def is_valid_device_id(device_id: str) -> bool:
    return bool(_DEVICE_ID_RE.match(device_id))


def write_reading(device_id: str, reading: Telemetry) -> None:
    point = (
        Point("telemetry")
        .tag("device_id", device_id)
        .field("temperature", reading.temperature)
        .field("humidity", reading.humidity)
    )
    write_api.write(bucket=config.INFLUX_BUCKET, record=point)


def read_readings(device_id: str, limit: int = 10) -> list[dict]:
    query = f'''
    from(bucket: "{config.INFLUX_BUCKET}")
      |> range(start: -24h)
      |> filter(fn: (r) => r._measurement == "telemetry"
                           and r.device_id == "{device_id}")
      |> pivot(rowKey: ["_time"], columnKey: ["_field"],
               valueColumn: "_value")
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: {int(limit)})
    '''
    tables = query_api.query(query)
    return [
        {
            "time": record.get_time().isoformat(),
            "temperature": record.values.get("temperature"),
            "humidity": record.values.get("humidity"),
        }
        for table in tables
        for record in table.records
    ]


def ping() -> bool:
    return client.ping()
