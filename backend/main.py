import asyncio
import json
from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

import sensors
import alarms
from database import init_db, get_db

TICK_INTERVAL = 1.0  # seconds between sensor readings

_ws_clients: list[WebSocket] = []
_event_log: list[dict] = []  # in-memory ring buffer (last 200 events)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_event(event_type: str, description: str, sensor_id: Optional[str] = None):
    entry = {
        "id": len(_event_log) + 1,
        "event_type": event_type,
        "sensor_id": sensor_id,
        "description": description,
        "timestamp": _now(),
    }
    _event_log.append(entry)
    if len(_event_log) > 200:
        _event_log.pop(0)
    return entry


async def _broadcast(payload: dict):
    dead = []
    for ws in _ws_clients:
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.remove(ws)


async def _scada_loop():
    _log_event("system", "SCADA system started")
    while True:
        readings = sensors.tick_sensors()
        new_alarms_all = []

        for reading in readings:
            new_alarms = alarms.evaluate(reading)
            for alarm in new_alarms:
                _log_event(
                    "alarm",
                    f"[{alarm['severity'].upper()}] {alarm['message']}",
                    alarm["sensor_id"],
                )
            new_alarms_all.extend(new_alarms)

            # Persist reading to DB (fire and forget)
            asyncio.create_task(_persist_reading(reading))

        # Persist new alarms
        for alarm in new_alarms_all:
            asyncio.create_task(_persist_alarm(alarm))

        active = alarms.get_active_alarms()
        online = sum(1 for r in readings if r["status"] == "online")
        critical = sum(1 for a in active if a["severity"] == "critical")

        if online < len(readings) and critical == 0:
            sys_status = "degraded"
        elif critical > 0:
            sys_status = "critical"
        else:
            sys_status = "healthy"

        payload = {
            "type": "update",
            "sensors": readings,
            "alarms": active,
            "events": _event_log[-20:][::-1],
            "health": {
                "status": sys_status,
                "sensors_online": online,
                "sensors_total": len(readings),
                "active_alarms": len(active),
                "critical_alarms": critical,
            },
        }
        await _broadcast(payload)
        await asyncio.sleep(TICK_INTERVAL)


async def _persist_reading(reading: dict):
    try:
        db = await get_db()
        async with db:
            await db.execute(
                "INSERT INTO sensor_readings (sensor_id, value, unit, timestamp) VALUES (?,?,?,?)",
                (reading["sensor_id"], reading["value"], reading["unit"], reading["last_updated"]),
            )
            await db.commit()
    except Exception:
        pass


async def _persist_alarm(alarm: dict):
    try:
        db = await get_db()
        async with db:
            await db.execute(
                """INSERT INTO alarms (sensor_id, alarm_type, severity, message, value,
                   acknowledged, resolved, triggered_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    alarm["sensor_id"], alarm["alarm_type"], alarm["severity"],
                    alarm["message"], alarm["value"],
                    int(alarm["acknowledged"]), int(alarm["resolved"]),
                    alarm["triggered_at"],
                ),
            )
            await db.commit()
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    _log_event("system", "Database initialized")
    task = asyncio.create_task(_scada_loop())
    yield
    task.cancel()


app = FastAPI(title="SCADA Reliability Monitor", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# --- REST endpoints ---

@app.get("/")
async def index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "SCADA Reliability Monitor API", "docs": "/docs"}


@app.get("/api/sensors")
async def get_sensors():
    return sensors.tick_sensors()


@app.get("/api/alarms")
async def get_alarms():
    return alarms.get_active_alarms()


@app.get("/api/events")
async def get_events():
    return list(reversed(_event_log[-50:]))


@app.get("/api/health")
async def get_health():
    readings = sensors.tick_sensors()
    active = alarms.get_active_alarms()
    online = sum(1 for r in readings if r["status"] == "online")
    critical = sum(1 for a in active if a["severity"] == "critical")
    if online < len(readings) and critical == 0:
        status = "degraded"
    elif critical > 0:
        status = "critical"
    else:
        status = "healthy"
    return {
        "status": status,
        "sensors_online": online,
        "sensors_total": len(readings),
        "active_alarms": len(active),
        "critical_alarms": critical,
    }


@app.post("/api/simulate/failure")
async def simulate_failure(sensor_id: str, mode: str):
    """Inject a failure mode. mode: offline | stale | spike | clear"""
    if sensor_id not in sensors.get_sensor_ids():
        raise HTTPException(status_code=404, detail="Unknown sensor")
    if mode not in ("offline", "stale", "spike", "clear"):
        raise HTTPException(status_code=400, detail="mode must be offline|stale|spike|clear")
    sensors.set_failure(sensor_id, None if mode == "clear" else mode)
    action = "cleared" if mode == "clear" else f"set to {mode}"
    _log_event("failure_sim", f"Failure simulation {action} on {sensor_id}", sensor_id)
    return {"sensor_id": sensor_id, "mode": mode}


@app.post("/api/alarms/acknowledge")
async def ack_alarm(sensor_id: str, alarm_type: str):
    ok = alarms.acknowledge_alarm(sensor_id, alarm_type)
    if ok:
        _log_event("ack", f"Alarm acknowledged: {sensor_id}/{alarm_type}", sensor_id)
    return {"acknowledged": ok}


@app.get("/api/history/{sensor_id}")
async def get_history(sensor_id: str, limit: int = 60):
    db = await get_db()
    async with db:
        cursor = await db.execute(
            "SELECT value, timestamp FROM sensor_readings WHERE sensor_id=? ORDER BY id DESC LIMIT ?",
            (sensor_id, limit),
        )
        rows = await cursor.fetchall()
    return [{"value": r[0], "timestamp": r[1]} for r in reversed(rows)]


# --- WebSocket ---

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _ws_clients.append(ws)
    try:
        while True:
            await ws.receive_text()  # keep alive
    except WebSocketDisconnect:
        if ws in _ws_clients:
            _ws_clients.remove(ws)
