import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "scada.db")


async def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return await aiosqlite.connect(DB_PATH)


async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_id TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS alarms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_id TEXT NOT NULL,
                alarm_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                value REAL,
                acknowledged INTEGER DEFAULT 0,
                resolved INTEGER DEFAULT 0,
                triggered_at TEXT NOT NULL,
                resolved_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                sensor_id TEXT,
                description TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        await db.commit()
