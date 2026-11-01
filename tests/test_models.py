import pytest
from pydantic import ValidationError

from app.models import Telemetry

INVALID_PAYLOADS = [
    {"temperature": 500, "humidity": 50},
    {"temperature": 20, "humidity": 101},
    {"temperature": 20},
    {"temperature": "abc", "humidity": 50},
]


def test_valid_payload():
    reading = Telemetry(temperature=23.4, humidity=55.2)
    assert reading.temperature == 23.4
    assert reading.humidity == 55.2


@pytest.mark.parametrize("payload", INVALID_PAYLOADS)
def test_invalid_payloads(payload):
    with pytest.raises(ValidationError):
        Telemetry(**payload)
