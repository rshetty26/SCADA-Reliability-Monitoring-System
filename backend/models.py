from pydantic import BaseModel
from typing import Optional
from enum import Enum


class SensorStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    FAULT = "fault"
    STALE = "stale"


class AlarmSeverity(str, Enum):
    WARNING = "warning"
    CRITICAL = "critical"


class AlarmType(str, Enum):
    HIGH = "high"
    LOW = "low"
    STALE_DATA = "stale_data"
    COMMS_FAILURE = "comms_failure"
    INVALID_DATA = "invalid_data"


class SensorReading(BaseModel):
    sensor_id: str
    name: str
    value: float
    unit: str
    status: SensorStatus
    min_normal: float
    max_normal: float
    warning_high: float
    critical_high: float
    warning_low: float
    critical_low: float
    last_updated: str


class AlarmRecord(BaseModel):
    id: int
    sensor_id: str
    alarm_type: str
    severity: str
    message: str
    value: Optional[float]
    acknowledged: bool
    resolved: bool
    triggered_at: str
    resolved_at: Optional[str]


class EventRecord(BaseModel):
    id: int
    event_type: str
    sensor_id: Optional[str]
    description: str
    timestamp: str


class SystemHealth(BaseModel):
    status: str
    sensors_online: int
    sensors_total: int
    active_alarms: int
    critical_alarms: int
