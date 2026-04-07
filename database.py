"""
database.py - Capa de persistencia (SQLite)

Este módulo es el "mundo real" al que los agentes acceden a través
de herramientas (tools). Sin esta capa, los agentes no tendrían memoria
entre sesiones.

Cada función aquí se conecta a una herramienta (tool) de algún agente:
  - save_session()         → Receptor usa esta tool para guardar reportes
  - get_recent_sessions()  → Entrenador consulta historial reciente
  - get_week_frequency()   → Entrenador sabe cuántos días entrenas/semana
  - get_all_sessions()     → Analista revisa todo el historial
  - etc.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path


# La base de datos vive en data/calistenia.db (carpeta ignorada por git)
DB_PATH = Path(__file__).parent / "data" / "calistenia.db"


def get_connection():
    """Crea conexión a SQLite. Crea la carpeta data/ si no existe."""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # Permite acceder a columnas por nombre
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Crea las tablas si no existen. Se llama al arrancar la app."""
    conn = get_connection()
    conn.executescript("""
        -- Cada vez que entrenas, se crea una sesión
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,              -- YYYY-MM-DD
            weight REAL,                     -- Peso corporal en kg
            duration_minutes INTEGER DEFAULT 40,
            fatigue_level INTEGER,           -- 1-10 (percibido)
            general_notes TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Ejercicios individuales dentro de cada sesión
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            name TEXT NOT NULL,
            sets INTEGER,
            reps TEXT,                       -- "10", "8-10", "al fallo"
            weight REAL,                     -- Peso adicional (lastre)
            difficulty INTEGER,              -- 1-10 percibido
            notes TEXT
        );

        -- Rutinas que el Entrenador genera (para comparar plan vs realidad)
        CREATE TABLE IF NOT EXISTS planned_workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            focus TEXT,                      -- "tren superior", "full body", etc.
            total_duration_minutes INTEGER DEFAULT 40,
            exercises_json TEXT NOT NULL,     -- JSON con la rutina
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Recomendaciones del Analista (las lee el Entrenador)
        CREATE TABLE IF NOT EXISTS analyst_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════
# HERRAMIENTAS (TOOLS) - Funciones que los agentes pueden llamar
# ═══════════════════════════════════════════════════════════════

def save_session(date, exercises, weight=None, fatigue_level=None,
                 notes=None, duration_minutes=40):
    """Tool del Agente Receptor: guarda un reporte de sesión."""
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO sessions (date, weight, duration_minutes, fatigue_level, general_notes) "
        "VALUES (?, ?, ?, ?, ?)",
        (date, weight, duration_minutes, fatigue_level, notes)
    )
    session_id = cursor.lastrowid

    for ex in exercises:
        conn.execute(
            "INSERT INTO exercises (session_id, name, sets, reps, weight, difficulty, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_id, ex.get("name"), ex.get("sets"), ex.get("reps"),
             ex.get("weight"), ex.get("difficulty"), ex.get("notes"))
        )

    conn.commit()
    conn.close()
    return {"status": "ok", "session_id": session_id}


def get_recent_sessions(limit=10):
    """Tool del Entrenador: obtiene las últimas N sesiones con ejercicios."""
    conn = get_connection()
    sessions = conn.execute(
        "SELECT * FROM sessions ORDER BY date DESC LIMIT ?", (limit,)
    ).fetchall()

    result = []
    for s in sessions:
        exercises = conn.execute(
            "SELECT * FROM exercises WHERE session_id = ?", (s["id"],)
        ).fetchall()
        result.append({
            **dict(s),
            "exercises": [dict(e) for e in exercises]
        })

    conn.close()
    return result


def get_week_frequency():
    """Tool del Entrenador: cuántas sesiones lleva esta semana."""
    conn = get_connection()
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())  # Lunes
    sessions = conn.execute(
        "SELECT COUNT(*) as count FROM sessions WHERE date >= ?",
        (start_of_week.strftime("%Y-%m-%d"),)
    ).fetchone()
    conn.close()
    return {
        "sessions_this_week": sessions["count"],
        "week_start": start_of_week.strftime("%Y-%m-%d")
    }


def get_days_since_last_session():
    """Tool del Entrenador: días desde la última sesión."""
    conn = get_connection()
    last = conn.execute(
        "SELECT date FROM sessions ORDER BY date DESC LIMIT 1"
    ).fetchone()
    conn.close()

    if last:
        last_date = datetime.strptime(last["date"], "%Y-%m-%d")
        days = (datetime.now() - last_date).days
        return {"days_since_last": days, "last_date": last["date"]}
    return {"days_since_last": None, "last_date": None}


def save_planned_workout(exercises, total_duration_minutes=40, focus=""):
    """Tool del Entrenador: guarda la rutina planificada."""
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    conn.execute(
        "INSERT INTO planned_workouts (date, focus, total_duration_minutes, exercises_json) "
        "VALUES (?, ?, ?, ?)",
        (today, focus, total_duration_minutes,
         json.dumps(exercises, ensure_ascii=False))
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


def get_all_sessions():
    """Tool del Analista: todas las sesiones para análisis de progreso."""
    conn = get_connection()
    sessions = conn.execute(
        "SELECT * FROM sessions ORDER BY date DESC"
    ).fetchall()

    result = []
    for s in sessions:
        exercises = conn.execute(
            "SELECT * FROM exercises WHERE session_id = ?", (s["id"],)
        ).fetchall()
        result.append({
            **dict(s),
            "exercises": [dict(e) for e in exercises]
        })

    conn.close()
    return result


def get_exercise_history(exercise_name):
    """Tool del Analista: historial de un ejercicio específico."""
    conn = get_connection()
    exercises = conn.execute(
        """SELECT e.*, s.date, s.weight as body_weight, s.fatigue_level
           FROM exercises e
           JOIN sessions s ON e.session_id = s.id
           WHERE LOWER(e.name) LIKE LOWER(?)
           ORDER BY s.date DESC""",
        (f"%{exercise_name}%",)
    ).fetchall()
    conn.close()
    return [dict(e) for e in exercises]


def save_recommendation(recommendation):
    """Tool del Analista: guarda recomendaciones para el Entrenador."""
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    conn.execute(
        "INSERT INTO analyst_recommendations (date, recommendation) VALUES (?, ?)",
        (today, recommendation)
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


def get_recent_recommendations(limit=5):
    """Tool del Entrenador: lee recomendaciones del Analista."""
    conn = get_connection()
    recs = conn.execute(
        "SELECT * FROM analyst_recommendations ORDER BY date DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in recs]
