from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LogDroneType = Literal["delivery", "queen", "inspector", "agriculture"]

LogServiceType = Literal[
    "delivery",
    "queen",
    "inspector",
    "agriculture",
    "GCS",
    "aggregator",
    "insurance",
    "regulator",
    "dronePort",
    "OrAT_drones",
    "operator",
    "SITL",
    "Gazebo",
    "infopanel",
    "registry",
]

LogSeverityType = Literal[
    "debug",
    "info",
    "notice",
    "warning",
    "error",
    "critical",
    "alert",
    "emergency",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginRequest(StrictModel):
    username: str = Field(min_length=4, max_length=64)
    password: str = Field(min_length=8, max_length=64)


class RefreshTokenRequest(StrictModel):
    refresh_token: str = Field(min_length=16, max_length=1024)


class TokenPairResponse(StrictModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class BasicLogItem(StrictModel):
    timestamp: int = Field(ge=0)
    message: str = Field(min_length=1, max_length=1024)


class TelemetryLogItem(StrictModel):
    apiVersion: str = Field(min_length=5, max_length=8)
    timestamp: int = Field(ge=0)
    drone: LogDroneType
    drone_id: int = Field(ge=1)
    battery: int | None = Field(default=None, ge=0, le=100)
    pitch: float | None = Field(default=None, ge=-90, le=90)
    roll: float | None = Field(default=None, ge=-180, le=180)
    course: float | None = Field(default=None, ge=0, le=360)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    height: float | None = Field(default=None, ge=0, le=500000)


class EventLogItem(StrictModel):
    apiVersion: str = Field(min_length=5, max_length=8)
    timestamp: int = Field(ge=0)
    event_type: Literal["event", "safety_event"] | None = None
    service: LogServiceType
    service_id: int = Field(ge=1)
    severity: LogSeverityType | None = None
    message: str = Field(min_length=1, max_length=1024)


class TelemetryLogResponse(StrictModel):
    timestamp: int = Field(ge=0)
    drone: LogDroneType
    drone_id: int = Field(ge=1)
    battery: int | None = Field(default=None, ge=0, le=100)
    pitch: float | None = Field(default=None, ge=-90, le=90)
    roll: float | None = Field(default=None, ge=-180, le=180)
    course: float | None = Field(default=None, ge=0, le=360)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    height: float | None = Field(default=None, ge=0, le=500000)


class EventLogResponse(StrictModel):
    timestamp: int = Field(ge=0)
    service: LogServiceType
    service_id: int = Field(ge=1)
    severity: LogSeverityType | None = None
    message: str = Field(min_length=1, max_length=1024)
