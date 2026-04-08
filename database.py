"""
database.py - Capa de persistencia (SQLite) para Javi

Incluye gestión de perfil de usuario para personalización extrema.
Optimizado con tipado estático para Function Calling de Google Gemini.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any

# Base de datos local
DB_PATH = Path(__file__).parent / "data" / "calistenia.db"

def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Inicializa tablas y si no hay perfil, crea el de Javi."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age INTEGER,
            birthday TEXT,
            initial_weight REAL,
            current_weight REAL,
            injuries TEXT,
            goals TEXT,
            last_updated TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            weight REAL,
            duration_minutes INTEGER DEFAULT 40,
            fatigue_level INTEGER,
            general_notes TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            name TEXT NOT NULL,
            sets INTEGER,
            reps TEXT,
            weight REAL,
            difficulty INTEGER,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS planned_workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            focus TEXT,
            total_duration_minutes INTEGER DEFAULT 40,
            exercises_json TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS analyst_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    
    # Sembrado inicial para Javi si la tabla está vacía
    cursor = conn.execute("SELECT COUNT(*) as count FROM user_profile")
    if cursor.fetchone()["count"] == 0:
        conn.execute("""
            INSERT INTO user_profile (name, age, birthday, initial_weight, current_weight, injuries, goals)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("Javi", 56, "1970-05-22", 135.0, 135.0, "Fascitis plantar, forma física deplorable", 
              "Perder peso, colgarse en barra 10s, hacer el pino (largo plazo)"))
    
    conn.commit()
    conn.close()

# --- TOOLS PARA LOS AGENTES ---

def get_user_profile() -> Dict[str, Any]:
    """Obtiene el perfil actual del usuario (Javi) incluyendo edad, peso actual, lesiones y objetivos."""
    conn = get_connection()
    profile = conn.execute("SELECT * FROM user_profile ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return dict(profile) if profile else {}

def update_user_weight(new_weight: float) -> Dict[str, Any]:
    """Actualiza el peso actual (en kilogramos) en el perfil del usuario."""
    conn = get_connection()
    conn.execute("UPDATE user_profile SET current_weight = ?, last_updated = datetime('now')", (new_weight,))
    conn.commit()
    conn.close()
    return {"status": "ok", "new_weight": new_weight}

def save_session(date: str, exercises: List[Dict[str, Any]], weight: Optional[float] = None, fatigue_level: Optional[int] = None, notes: Optional[str] = None, duration_minutes: int = 40) -> Dict[str, Any]:
    """
    Guarda un reporte de una sesión de entrenamiento realizada.
    
    Args:
        date: Fecha en formato YYYY-MM-DD.
        exercises: Lista de diccionarios con {'name': str, 'sets': int, 'reps': str, 'weight': float, 'difficulty': int, 'notes': str}.
        weight: Peso actual del usuario hoy en kg.
        fatigue_level: Nivel de cansancio de 1 a 10.
        notes: Comentarios generales de la sesión.
        duration_minutes: Duración en minutos.
    """
    conn = get_connection()
    if weight:
        update_user_weight(weight)
        
    cursor = conn.execute(
        "INSERT INTO sessions (date, weight, duration_minutes, fatigue_level, general_notes) VALUES (?, ?, ?, ?, ?)",
        (date, weight, duration_minutes, fatigue_level, notes)
    )
    session_id = cursor.lastrowid
    for ex in exercises:
        conn.execute(
            "INSERT INTO exercises (session_id, name, sets, reps, weight, difficulty, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_id, ex.get("name"), ex.get("sets"), ex.get("reps"), ex.get("weight"), ex.get("difficulty"), ex.get("notes"))
        )
    conn.commit()
    conn.close()
    return {"status": "ok", "session_id": session_id}

def get_recent_sessions(limit: int = 10) -> List[Dict[str, Any]]:
    """Obtiene las últimas N sesiones de entrenamiento realizadas, con sus ejercicios."""
    conn = get_connection()
    sessions = conn.execute("SELECT * FROM sessions ORDER BY date DESC LIMIT ?", (limit,)).fetchall()
    result = []
    for s in sessions:
        exercises = conn.execute("SELECT * FROM exercises WHERE session_id = ?", (s["id"],)).fetchall()
        result.append({**dict(s), "exercises": [dict(e) for e in exercises]})
    conn.close()
    return result

def get_week_frequency() -> Dict[str, Any]:
    """Calcula cuántas sesiones se han realizado en la semana actual."""
    conn = get_connection()
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    sessions = conn.execute("SELECT COUNT(*) as count FROM sessions WHERE date >= ?", (start_of_week.strftime("%Y-%m-%d"),)).fetchone()
    conn.close()
    return {"sessions_this_week": sessions["count"], "week_start": start_of_week.strftime("%Y-%m-%d")}

def get_days_since_last_session() -> Dict[str, Any]:
    """Obtiene el número de días transcurridos desde el último entrenamiento."""
    conn = get_connection()
    last = conn.execute("SELECT date FROM sessions ORDER BY date DESC LIMIT 1").fetchone()
    conn.close()
    if last:
        last_date = datetime.strptime(last["date"], "%Y-%m-%d")
        days = (datetime.now() - last_date).days
        return {"days_since_last": days, "last_date": last["date"]}
    return {"days_since_last": None, "last_date": None}

def save_planned_workout(exercises: List[Dict[str, Any]], total_duration_minutes: int = 40, focus: str = "") -> Dict[str, Any]:
    """Guarda la rutina que el entrenador ha planeado para hoy."""
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    conn.execute("INSERT INTO planned_workouts (date, focus, total_duration_minutes, exercises_json) VALUES (?, ?, ?, ?)",
                (today, focus, total_duration_minutes, json.dumps(exercises, ensure_ascii=False)))
    conn.commit()
    conn.close()
    return {"status": "ok"}

def get_all_sessions() -> List[Dict[str, Any]]:
    """Obtiene el historial completo de todas las sesiones realizadas."""
    conn = get_connection()
    sessions = conn.execute("SELECT * FROM sessions ORDER BY date DESC").fetchall()
    result = []
    for s in sessions:
        exercises = conn.execute("SELECT * FROM exercises WHERE session_id = ?", (s["id"],)).fetchall()
        result.append({**dict(s), "exercises": [dict(e) for e in exercises]})
    conn.close()
    return result

def get_exercise_history(exercise_name: str) -> List[Dict[str, Any]]:
    """Obtiene el histórico de progreso de un ejercicio específico (ej: 'Colgado en barra')."""
    conn = get_connection()
    exercises = conn.execute("""SELECT e.*, s.date, s.weight as body_weight, s.fatigue_level 
                               FROM exercises e JOIN sessions s ON e.session_id = s.id 
                               WHERE LOWER(e.name) LIKE LOWER(?) ORDER BY s.date DESC""", (f"%{exercise_name}%",)).fetchall()
    conn.close()
    return [dict(e) for e in exercises]

def save_recommendation(recommendation: str) -> Dict[str, Any]:
    """Guarda un consejo o recomendación del Agente Analista."""
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    conn.execute("INSERT INTO analyst_recommendations (date, recommendation) VALUES (?, ?)", (today, recommendation))
    conn.commit()
    conn.close()
    return {"status": "ok"}

def get_recent_recommendations(limit: int = 5) -> List[Dict[str, Any]]:
    """Obtiene las últimas N recomendaciones del analista."""
    conn = get_connection()
    recs = conn.execute("SELECT * FROM analyst_recommendations ORDER BY date DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in recs]
