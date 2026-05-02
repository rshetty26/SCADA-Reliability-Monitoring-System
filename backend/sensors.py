import random
import math
from datetime import datetime, timezone
from models import SensorStatus

SENSOR_CONFIGS = {
    "pressure_1": {
        "name": "Inlet Pressure",
        "unit": "PSI",
        "base_value": 65.0,
        "noise": 1.5,
        "min_normal": 0.0,
        "max_normal": 100.0,
        "warning_low": 20.0,
        "critical_low": 10.0,
        "warning_high": 80.0,
        "critical_high": 95.0,
    },
    "pressure_2": {
        "name": "Outlet Pressure",
        "unit": "PSI",
        "base_value": 45.0,
        "noise": 1.2,
        "min_normal": 0.0,
        "max_normal": 100.0,
        "warning_low": 15.0,
        "critical_low": 8.0,
        "warning_high": 75.0,
        "critical_high": 90.0,
    },
    "temperature_1": {
        "name": "Reactor Temperature",
        "unit": "°C",
        "base_value": 85.0,
        "noise": 2.0,
        "min_normal": 0.0,
        "max_normal": 150.0,
        "warning_low": 30.0,
        "critical_low": 20.0,
        "warning_high": 120.0,
        "critical_high": 140.0,
    },
    "temperature_2": {
        "name": "Coolant Temperature",
        "unit": "°C",
        "base_value": 42.0,
        "noise": 1.0,
        "min_normal": 0.0,
        "max_normal": 100.0,
        "warning_low": 10.0,
        "critical_low": 5.0,
        "warning_high": 70.0,
        "critical_high": 85.0,
    },
    "flow_1": {
        "name": "Main Flow Rate",
        "unit": "L/min",
        "base_value": 280.0,
        "noise": 8.0,
        "min_normal": 0.0,
        "max_normal": 500.0,
        "warning_low": 50.0,
        "critical_low": 20.0,
        "warning_high": 450.0,
        "critical_high": 490.0,
    },
    "flow_2": {
        "name": "Bypass Flow Rate",
        "unit": "L/min",
        "base_value": 95.0,
        "noise": 4.0,
        "min_normal": 0.0,
        "max_normal": 200.0,
        "warning_low": 20.0,
        "critical_low": 8.0,
        "warning_high": 170.0,
        "critical_high": 190.0,
    },
}

_sensor_state: dict = {}


def _init_state():
    for sid, cfg in SENSOR_CONFIGS.items():
        _sensor_state[sid] = {
            "value": cfg["base_value"],
            "status": SensorStatus.ONLINE,
            "failure_mode": None,
            "failure_ticks": 0,
            "drift": 0.0,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def tick_sensors() -> list[dict]:
    if not _sensor_state:
        _init_state()

    readings = []
    t = datetime.now(timezone.utc).timestamp()

    for sid, cfg in SENSOR_CONFIGS.items():
        state = _sensor_state[sid]
        failure = state["failure_mode"]

        if failure == "offline":
            state["status"] = SensorStatus.OFFLINE
            readings.append(_build_reading(sid, cfg, state))
            continue

        if failure == "stale":
            state["status"] = SensorStatus.STALE
            readings.append(_build_reading(sid, cfg, state))
            continue

        if failure == "spike":
            state["value"] = cfg["critical_high"] * 1.15
            state["status"] = SensorStatus.FAULT
            state["last_updated"] = _now()
            readings.append(_build_reading(sid, cfg, state))
            continue

        # Normal: random walk + sine drift
        noise = random.gauss(0, cfg["noise"] * 0.3)
        drift = math.sin(t / 60.0) * cfg["noise"] * 0.5
        state["value"] = cfg["base_value"] + drift + noise
        state["value"] = max(cfg["min_normal"], min(cfg["max_normal"], state["value"]))
        state["status"] = SensorStatus.ONLINE
        state["last_updated"] = _now()
        readings.append(_build_reading(sid, cfg, state))

    return readings


def _build_reading(sid: str, cfg: dict, state: dict) -> dict:
    return {
        "sensor_id": sid,
        "name": cfg["name"],
        "value": round(state["value"], 2),
        "unit": cfg["unit"],
        "status": state["status"],
        "min_normal": cfg["min_normal"],
        "max_normal": cfg["max_normal"],
        "warning_low": cfg["warning_low"],
        "critical_low": cfg["critical_low"],
        "warning_high": cfg["warning_high"],
        "critical_high": cfg["critical_high"],
        "last_updated": state["last_updated"],
    }


def set_failure(sensor_id: str, mode: str | None):
    """mode: 'offline' | 'stale' | 'spike' | None (clear)"""
    if sensor_id not in _sensor_state:
        _init_state()
    _sensor_state[sensor_id]["failure_mode"] = mode
    if mode is None:
        cfg = SENSOR_CONFIGS[sensor_id]
        _sensor_state[sensor_id]["value"] = cfg["base_value"]
        _sensor_state[sensor_id]["status"] = SensorStatus.ONLINE


def get_sensor_ids() -> list[str]:
    return list(SENSOR_CONFIGS.keys())
