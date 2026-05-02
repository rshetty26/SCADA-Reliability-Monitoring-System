from datetime import datetime, timezone
from models import AlarmSeverity, AlarmType, SensorStatus

# active_alarms[sensor_id][alarm_type] = alarm dict
_active_alarms: dict[str, dict[str, dict]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def evaluate(reading: dict) -> list[dict]:
    """Return list of new alarm dicts triggered by this reading."""
    sid = reading["sensor_id"]
    val = reading["value"]
    status = reading["status"]
    new_alarms = []

    if sid not in _active_alarms:
        _active_alarms[sid] = {}

    # --- Comms / status alarms ---
    if status == SensorStatus.OFFLINE:
        new_alarms += _raise(sid, AlarmType.COMMS_FAILURE, AlarmSeverity.CRITICAL,
                             f"{reading['name']} is OFFLINE — communication lost", None)
        return new_alarms
    else:
        _clear(sid, AlarmType.COMMS_FAILURE)

    if status == SensorStatus.STALE:
        new_alarms += _raise(sid, AlarmType.STALE_DATA, AlarmSeverity.WARNING,
                             f"{reading['name']} data is STALE — no updates received", val)
        return new_alarms
    else:
        _clear(sid, AlarmType.STALE_DATA)

    if status == SensorStatus.FAULT:
        new_alarms += _raise(sid, AlarmType.INVALID_DATA, AlarmSeverity.CRITICAL,
                             f"{reading['name']} reporting INVALID value: {val} {reading['unit']}", val)
        return new_alarms
    else:
        _clear(sid, AlarmType.INVALID_DATA)

    # --- Threshold alarms ---
    if val >= reading["critical_high"]:
        new_alarms += _raise(sid, AlarmType.HIGH, AlarmSeverity.CRITICAL,
                             f"{reading['name']} CRITICAL HIGH: {val} {reading['unit']} (limit {reading['critical_high']})", val)
    elif val >= reading["warning_high"]:
        new_alarms += _raise(sid, AlarmType.HIGH, AlarmSeverity.WARNING,
                             f"{reading['name']} HIGH: {val} {reading['unit']} (limit {reading['warning_high']})", val)
    else:
        _clear(sid, AlarmType.HIGH)

    if val <= reading["critical_low"]:
        new_alarms += _raise(sid, AlarmType.LOW, AlarmSeverity.CRITICAL,
                             f"{reading['name']} CRITICAL LOW: {val} {reading['unit']} (limit {reading['critical_low']})", val)
    elif val <= reading["warning_low"]:
        new_alarms += _raise(sid, AlarmType.LOW, AlarmSeverity.WARNING,
                             f"{reading['name']} LOW: {val} {reading['unit']} (limit {reading['warning_low']})", val)
    else:
        _clear(sid, AlarmType.LOW)

    return new_alarms


def _raise(sid: str, alarm_type: AlarmType, severity: AlarmSeverity, message: str, value) -> list[dict]:
    key = alarm_type.value
    if key in _active_alarms[sid]:
        return []  # already active, don't duplicate
    alarm = {
        "sensor_id": sid,
        "alarm_type": alarm_type.value,
        "severity": severity.value,
        "message": message,
        "value": value,
        "acknowledged": False,
        "resolved": False,
        "triggered_at": _now(),
        "resolved_at": None,
    }
    _active_alarms[sid][key] = alarm
    return [alarm]


def _clear(sid: str, alarm_type: AlarmType):
    key = alarm_type.value
    if key in _active_alarms[sid]:
        del _active_alarms[sid][key]


def get_active_alarms() -> list[dict]:
    result = []
    for sensor_alarms in _active_alarms.values():
        result.extend(sensor_alarms.values())
    return sorted(result, key=lambda a: a["triggered_at"], reverse=True)


def acknowledge_alarm(sensor_id: str, alarm_type: str) -> bool:
    if sensor_id in _active_alarms and alarm_type in _active_alarms[sensor_id]:
        _active_alarms[sensor_id][alarm_type]["acknowledged"] = True
        return True
    return False
