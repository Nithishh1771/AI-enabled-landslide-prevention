import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
from config import Config

def get_connection():
    Config.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        schema = (Path(__file__).with_name("schema.sql")).read_text(encoding="utf-8")
        conn.executescript(schema)
        conn.commit()

def insert_environment(reading):
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO environmental_readings
            (timestamp, latitude, longitude, rainfall_1h, rainfall_3h,
             rainfall_24h, soil_moisture, temperature, humidity, elevation,
             slope, aspect, land_cover, historical_landslide_density)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            reading["timestamp"], reading["latitude"], reading["longitude"],
            reading["rainfall_1h"], reading["rainfall_3h"], reading["rainfall_24h"],
            reading["soil_moisture"], reading["temperature"], reading["humidity"],
            reading["elevation"], reading["slope"], reading["aspect"],
            reading["land_cover"], reading["historical_landslide_density"]
        ))
        conn.commit()
        return cur.lastrowid

def insert_risk(timestamp, latitude, longitude, risk_score, category):
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO risk_history
            (timestamp, latitude, longitude, risk_score, risk_category)
            VALUES (?, ?, ?, ?, ?)
        """, (timestamp, latitude, longitude, risk_score, category))
        conn.commit()
        return cur.lastrowid

def insert_alert(timestamp, severity, message, latitude, longitude, status="OPEN"):
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO alerts
            (timestamp, severity, message, latitude, longitude, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (timestamp, severity, message, latitude, longitude, status))
        conn.commit()
        return cur.lastrowid

def get_latest_environment():
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM environmental_readings ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

def get_risk_history(limit=20):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM risk_history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

def get_alerts(limit=10):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

def clear_demo_data():
    with get_connection() as conn:
        conn.execute("DELETE FROM environmental_readings")
        conn.execute("DELETE FROM risk_history")
        conn.execute("DELETE FROM alerts")
        conn.execute("DELETE FROM risk_zones")
        conn.commit()


def create_user(email, password_hash):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, password_hash)
        )
        conn.commit()
        return cur.lastrowid

def get_user_by_email(email):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ? LIMIT 1",
            (email,)
        ).fetchone()
        return dict(row) if row else None
