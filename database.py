"""
database.py - Capa de persistencia (Supabase / HTTPS) para Calistenia Coach

Multi-usuario: todas las funciones filtran por user_email.
Usa la API REST de Supabase (Port 443) para mayor robustez ante firewalls y DNS.
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client, Client

# Cargar entorno
load_dotenv(Path(__file__).parent / ".env")

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("⚠️ SUPABASE_URL o SUPABASE_KEY no configurados.")
    supabase: Client = None
else:
    supabase: Client = create_client(url, key)


# ─── PERFIL DE USUARIO ────────────────────────────────────────────────────────

def get_user_profile(user_email: str = None) -> Dict[str, Any]:
    """Obtiene el perfil del usuario: nombre, peso, lesiones, objetivos."""
    if not supabase:
        return {}
    if user_email:
        res = supabase.table("user_profile").select("*").eq("user_email", user_email).limit(1).execute()
    else:
        res = supabase.table("user_profile").select("*").order("id", desc=True).limit(1).execute()
    return res.data[0] if res.data else {}


def save_user_profile(user_email: str, name: str, weight: float, age: int,
                      injuries: str = "", goals: str = "") -> Dict[str, Any]:
    """Crea o actualiza el perfil de un usuario (onboarding)."""
    if not supabase:
        return {"error": "Supabase no inicializado"}
    try:
        existing = supabase.table("user_profile").select("id").eq("user_email", user_email).execute()
        data = {
            "user_email": user_email,
            "name": name,
            "age": age,
            "initial_weight": weight,
            "current_weight": weight,
            "injuries": injuries,
            "goals": goals,
            "last_updated": "now()",
        }
        if existing.data:
            supabase.table("user_profile").update(data).eq("user_email", user_email).execute()
        else:
            supabase.table("user_profile").insert(data).execute()
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}


def update_user_weight(new_weight: float, user_email: str = None) -> Dict[str, Any]:
    """Actualiza el peso actual (kg) en el perfil."""
    if not supabase:
        return {}
    profile = get_user_profile(user_email)
    if profile:
        supabase.table("user_profile").update(
            {"current_weight": new_weight, "last_updated": "now()"}
        ).eq("id", profile["id"]).execute()
    return {"status": "ok", "new_weight": new_weight}


def get_all_users_admin() -> List[Dict[str, Any]]:
    """[ADMIN] Devuelve todos los perfiles con su última sesión y total de sesiones."""
    if not supabase:
        return []
    profiles = supabase.table("user_profile").select("*").order("id").execute().data
    result = []
    for p in profiles:
        email = p.get("user_email")
        last_session = None
        session_count = 0
        if email:
            sessions = supabase.table("sessions").select("date").eq("user_email", email).order("date", desc=True).limit(1).execute()
            if sessions.data:
                last_session = sessions.data[0]["date"]
            count_res = supabase.table("sessions").select("id", count="exact").eq("user_email", email).execute()
            session_count = count_res.count or 0
        result.append({**p, "last_session": last_session, "session_count": session_count})
    return result


# ─── SESIONES ────────────────────────────────────────────────────────────────

def save_session(date: str, exercises: List[dict], weight: Optional[float] = None,
                 fatigue_level: Optional[int] = None, notes: Optional[str] = None,
                 duration_minutes: int = 40, user_email: str = None) -> dict:
    """Guarda reporte de sesión y vincula al plan de hoy.

    Args:
        date: Fecha en formato YYYY-MM-DD.
        exercises: Lista de ejercicios. Cada uno con keys: name (str),
                   sets (int), reps (int), seconds (int), difficulty (int), notes (str).
        weight: Peso corporal en kg.
        fatigue_level: Nivel de fatiga 1-10.
        notes: Notas generales de la sesión.
        duration_minutes: Duración total en minutos.
    """
    print(f"[save_session] date={date}, user={user_email}, {len(exercises or [])} ejercicios", flush=True)
    if not supabase:
        return {"error": "Supabase no inicializado"}

    try:
        # 0. Evitar duplicados por fecha + usuario
        q = supabase.table("sessions").select("id").eq("date", str(date))
        if user_email:
            q = q.eq("user_email", user_email)
        existing = q.execute()
        if existing.data:
            print(f"[save_session] Ya existe sesión para {date}, omitiendo.", flush=True)
            return {"status": "already_exists", "date": date, "session_id": existing.data[0]["id"]}

        # 1. Buscar rutina planeada PENDING para hoy
        pw_q = supabase.table("planned_workouts").select("id").eq("date", date).eq("status", "PENDING")
        if user_email:
            pw_q = pw_q.eq("user_email", user_email)
        planned = pw_q.limit(1).execute()
        planned_id = planned.data[0]["id"] if planned.data else None

        if weight:
            update_user_weight(float(weight), user_email)

        # 2. Insertar sesión
        session_data = {
            "planned_workout_id": planned_id,
            "date": str(date),
            "weight": float(weight) if weight is not None else None,
            "duration_minutes": int(duration_minutes) if duration_minutes else 40,
            "fatigue_level": int(fatigue_level) if fatigue_level is not None else None,
            "general_notes": str(notes) if notes else None,
            "user_email": user_email,
        }
        session_res = supabase.table("sessions").insert(session_data).execute()
        session_id = session_res.data[0]["id"]
        print(f"[save_session] Sesión creada id={session_id}", flush=True)

        # 3. Insertar ejercicios
        exercises_clean = []
        for ex in (exercises or []):
            if not isinstance(ex, dict):
                ex = dict(ex)
            exercises_clean.append(ex)

        for ex in exercises_clean:
            ex_data = {
                "session_id": session_id,
                "name": str(ex.get("name") or "Ejercicio"),
                "sets": int(ex.get("sets") or 1),
                "reps": int(ex.get("reps") or 0),
                "seconds": int(ex.get("seconds") or 0),
                "weight": float(ex.get("weight") or 0),
                "difficulty": int(ex.get("difficulty")) if ex.get("difficulty") is not None else None,
                "notes": str(ex.get("notes")) if ex.get("notes") else None,
            }
            supabase.table("exercises").insert(ex_data).execute()

        # 4. Marcar plan como completado
        if planned_id:
            supabase.table("planned_workouts").update({"status": "COMPLETED"}).eq("id", planned_id).execute()

        print(f"[save_session] OK — {len(exercises_clean)} ejercicios guardados", flush=True)
        return {"status": "ok", "session_id": session_id, "ejercicios_guardados": len(exercises_clean)}

    except Exception as e:
        print(f"[save_session] EXCEPCIÓN: {type(e).__name__}: {e}", flush=True)
        return {"error": str(e)}


def get_recent_sessions(limit: int = 10, user_email: str = None) -> List[Dict[str, Any]]:
    """Obtiene las últimas N sesiones de entrenamiento del usuario."""
    if not supabase:
        return []
    q = supabase.table("sessions").select("*, exercises(*)")
    if user_email:
        q = q.eq("user_email", user_email)
    return q.order("date", desc=True).limit(limit).execute().data


def get_all_sessions(user_email: str = None) -> List[Dict[str, Any]]:
    """Obtiene todas las sesiones del usuario."""
    if not supabase:
        return []
    q = supabase.table("sessions").select("*, exercises(*)")
    if user_email:
        q = q.eq("user_email", user_email)
    return q.order("date", desc=True).execute().data


def get_week_frequency(user_email: str = None) -> Dict[str, Any]:
    """Obtiene la frecuencia de entrenamiento de la semana actual."""
    if not supabase:
        return {}
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    q = supabase.table("sessions").select("id", count="exact").gte("date", start_of_week.isoformat())
    if user_email:
        q = q.eq("user_email", user_email)
    res = q.execute()
    return {"sessions_this_week": res.count, "week_start": str(start_of_week)}


def get_days_since_last_session(user_email: str = None) -> Optional[int]:
    """Calcula cuántos días han pasado desde el último entrenamiento."""
    if not supabase:
        return None
    q = supabase.table("sessions").select("date")
    if user_email:
        q = q.eq("user_email", user_email)
    res = q.order("date", desc=True).limit(1).execute()
    if not res.data:
        return None
    last_date = datetime.strptime(res.data[0]["date"], "%Y-%m-%d").date()
    return (datetime.now().date() - last_date).days


def get_exercise_history(name: str, user_email: str = None) -> List[Dict[str, Any]]:
    """Obtiene el historial de progreso de un ejercicio específico."""
    if not supabase:
        return []
    if user_email:
        sessions_res = supabase.table("sessions").select("id").eq("user_email", user_email).execute()
        session_ids = [s["id"] for s in sessions_res.data]
        if not session_ids:
            return []
        return supabase.table("exercises").select("*, sessions(date)").eq("name", name).in_("session_id", session_ids).execute().data
    return supabase.table("exercises").select("*, sessions(date)").eq("name", name).execute().data


# ─── RUTINAS PLANIFICADAS ────────────────────────────────────────────────────

def save_planned_workout(exercises: List[dict], total_duration_minutes: int = 40,
                         focus: str = "", user_email: str = None) -> dict:
    """Guarda la rutina planificada para hoy en la base de datos.

    Args:
        exercises: Lista de ejercicios planificados. Cada uno con keys: name, sets, reps, seconds.
        total_duration_minutes: Duración total de la sesión en minutos.
        focus: Foco o descripción de la sesión (ej: 'Agarre y fuerza superior').
    """
    print(f"[save_planned_workout] {len(exercises or [])} ejercicios, focus={focus}, user={user_email}", flush=True)
    if not supabase:
        return {"error": "Supabase no inicializado"}
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        exercises_clean = [dict(ex) if not isinstance(ex, dict) else ex for ex in (exercises or [])]
        data = {
            "date": today,
            "focus": str(focus) if focus else "",
            "total_duration_minutes": int(total_duration_minutes) if total_duration_minutes else 40,
            "exercises_json": json.dumps(exercises_clean, ensure_ascii=False),
            "status": "PENDING",
            "user_email": user_email,
        }
        supabase.table("planned_workouts").insert(data).execute()
        print(f"[save_planned_workout] OK — rutina guardada para {today}", flush=True)
        return {"status": "ok"}
    except Exception as e:
        print(f"[save_planned_workout] EXCEPCIÓN: {type(e).__name__}: {e}", flush=True)
        return {"error": str(e)}


# ─── RECOMENDACIONES ─────────────────────────────────────────────────────────

def save_recommendation(recommendation: str, user_email: str = None) -> Dict[str, Any]:
    """Guarda una recomendación del analista."""
    if not supabase:
        return {}
    today = datetime.now().strftime("%Y-%m-%d")
    supabase.table("analyst_recommendations").insert({
        "date": today,
        "recommendation": recommendation,
        "user_email": user_email,
    }).execute()
    return {"status": "ok"}


def get_recent_recommendations(limit: int = 5, user_email: str = None) -> List[Dict[str, Any]]:
    """Obtiene las últimas recomendaciones del analista."""
    if not supabase:
        return []
    q = supabase.table("analyst_recommendations").select("*")
    if user_email:
        q = q.eq("user_email", user_email)
    return q.order("date", desc=True).limit(limit).execute().data


# ─── INICIALIZACIÓN ──────────────────────────────────────────────────────────

def init_db():
    """Inicialización manual recomendada vía Supabase SQL Editor."""
    pass
