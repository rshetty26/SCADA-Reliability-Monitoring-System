# SCADA Reliability Monitoring System

A simulated SCADA operations environment focused on real-time monitoring, threshold-based alarming, failure simulation, and system reliability.

## Demo Screenshots

### Healthy System State

<p align="center">
  <img src="images/healthy-dashboard.png" width="1000"/>
</p>

### Critical Alarm State

<p align="center">
  <img src="images/critical-dashboard.png" width="1000"/>
</p>

### Trend Monitoring + Failure Injection

<p align="center">
  <img src="images/trend-view.png" width="1000"/>
</p>

---

## What it does

- **Live sensor monitoring** - 5 field instruments (pressure, temperature, flow) streaming data every second over WebSocket
- **Alarm engine** - evaluates readings against configurable thresholds; raises WARNING and CRITICAL alarms automatically
- **Failure simulation** - inject real-world faults: comms offline, stale data, and value spikes; observe alarm propagation in real time
- **Event log** - timestamped timeline of all alarms, failures, recoveries, and operator acknowledgements
- **System health** - overall status (HEALTHY / DEGRADED / CRITICAL) driven by sensor and alarm state
- **Trend chart** - live rolling time-series for any selected sensor

---

## Architecture

```
frontend/index.html     Single-page dashboard (Tailwind CSS + Chart.js, no build step)
backend/
  main.py               FastAPI server - REST API + WebSocket broadcast loop
  sensors.py            Sensor simulator - random walk with failure injection
  alarms.py             Alarm evaluation engine - threshold + status-based
  database.py           SQLite persistence (sensor readings, alarms, events)
  models.py             Pydantic models
data/scada.db           SQLite database (auto-created on first run)
```

---

## Setup

**Requirements:** Python 3.11+

Double-click `run.bat` - it installs all dependencies and opens the dashboard at `http://localhost:8000` automatically.

To stop the server, press `Ctrl+C` in the terminal window.

---

## Key endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Dashboard UI |
| `GET` | `/api/sensors` | Current sensor readings |
| `GET` | `/api/alarms` | Active alarms |
| `GET` | `/api/events` | Recent event log |
| `GET` | `/api/health` | System health summary |
| `GET` | `/api/history/{sensor_id}` | Historical readings (last 60) |
| `POST` | `/api/simulate/failure` | Inject failure (`offline`, `stale`, `spike`, `clear`) |
| `POST` | `/api/alarms/acknowledge` | Acknowledge an alarm |
| `WS` | `/ws` | Real-time push updates |
| `GET` | `/docs` | Interactive API docs (Swagger UI) |

---

## Simulated sensors

| ID | Name | Unit | Range |
|----|------|------|-------|
| `pressure_1` | Inlet Pressure | PSI | 0–100 |
| `pressure_2` | Outlet Pressure | PSI | 0–100 |
| `temperature_1` | Reactor Temperature | °C | 0–150 |
| `temperature_2` | Coolant Temperature | °C | 0–100 |
| `flow_1` | Main Flow Rate | L/min | 0–500 |
| `flow_2` | Bypass Flow Rate | L/min | 0–200 |

---

## Demo: failure scenarios

```bash
# Trigger comms offline on inlet pressure
curl -X POST "http://localhost:8000/api/simulate/failure?sensor_id=pressure_1&mode=offline"

# Inject stale data on reactor temperature
curl -X POST "http://localhost:8000/api/simulate/failure?sensor_id=temperature_1&mode=stale"

# Spike the main flow rate above critical threshold
curl -X POST "http://localhost:8000/api/simulate/failure?sensor_id=flow_1&mode=spike"

# Clear all failures on a sensor
curl -X POST "http://localhost:8000/api/simulate/failure?sensor_id=pressure_1&mode=clear"
```

All failure scenarios are also injectable directly from the dashboard UI.
