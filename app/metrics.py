from prometheus_client import Counter, Histogram

MESSAGES = Counter(
    "mqtt_messages_received_total",
    "Messages MQTT traités, par résultat",
    ["status"],
)

WRITE_LATENCY = Histogram(
    "influx_write_seconds",
    "Durée d'écriture dans InfluxDB",
)
