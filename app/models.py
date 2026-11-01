from pydantic import BaseModel, Field


class Telemetry(BaseModel):
    temperature: float = Field(ge=-50, le=100)
    humidity: float = Field(ge=0, le=100)
