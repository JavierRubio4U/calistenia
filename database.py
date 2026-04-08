"""
database.py - Capa de persistencia (Supabase / HTTPS) para Javi

Usa la API REST de Supabase (Port 443) para mayor robustez ante firewalls y DNS.
Sincronización total entre local y móvil.
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

def get_user_profile() -> Dict[str, Any]:
    """Obtiene el perfil actual de Javi."""
    if not supabase: return {}
    response = supabase.table("user_profile").select("*").order("id", desc=True).limit(1).execute()
    return response.data[0] if response.data else {}

def update_user_weight(new_weight: float) -> Dict[str, Any]:
    """Actualiza el peso actual (kg) en el perfil."""
    if not supabase: return {}
    # Obtenemos el ID del ultimo perfil
    profile = get_user_profile()
    if profile:
        supabase.table("user_profile").update({"current_weight": new_weight, "last_updated": "now()"}).eq("id", profile["id"]).execute()
    return {"status": "ok", "new_weight": new_weight}

def save_session(date: str, exercises: List[Dict[str, Any]], weight: Optional[float] = None, fatigue_level: Optional[int] = None, notes: Optional[str] = None, duration_minutes: int = 40) -> Dict[str, Any]:
    """Guarda reporte de sesión y vincula al plan de hoy."""
    if not supabase: return {}
    
    # 1. Buscar rutina planeada PENDING
    planned = supabase.table("planned_workouts").select("id").eq("date", date).eq("status", "PENDING").limit(1).execute()
    planned_id = planned.data[0]["id"] if planned.data else None

    if weight:
        update_user_weight(weight)
            
    # 2. Insertar sesión
    session_data = {
        "planned_workout_id": planned_id,
        "date": date,
        "weight": weight,
        "duration_minutes": duration_minutes,
        "fatigue_level": fatigue_level,
        "general_notes": notes
    }
    session_res = supabase.table("sessions").insert(session_data).execute()
    session_id = session_res.data[0]["id"]
    
    # 3. Insertar ejercicios
    for ex in exercises:
        ex_data = {
            "session_id": session_id,
            "name": ex.get("name"),
            "sets": ex.get("sets", 1),
            "reps": ex.get("reps", 0),
            "seconds": ex.get("seconds", 0),
            "weight": ex.get("weight", 0),
            "difficulty": ex.get("difficulty"),
            "notes": ex.get("notes")
        }
        supabase.table("exercises").insert(ex_data).execute()
    
    # 4. Marcar plan como completado
    if planned_id:
        supabase.table("planned_workouts").update({"status": "COMPLETED"}).eq("id", planned_id).execute()
            
    return {"status": "ok", "session_id": session_id, "linked_to_plan": planned_id is not None}

def get_recent_sessions(limit: int = 10) -> List[Dict[str, Any]]:
    if not supabase: return []
    res = supabase.table("sessions").select("*, exercises(*)").order("date", desc=True).limit(limit).execute()
    return res.data

def get_week_frequency() -> Dict[str, Any]:
    if not supabase: return {}
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    res = supabase.table("sessions").select("id", count="exact").gte("date", start_of_week.isoformat()).execute()
    return {"sessions_this_week": res.count, "week_start": str(start_of_week)}

def save_planned_workout(exercises: List[Dict[str, Any]], total_duration_minutes: int = 40, focus: str = "") -> Dict[str, Any]:
    if not supabase: return {}
    today = datetime.now().strftime("%Y-%m-%d")
    data = {
        "date": today,
        "focus": focus,
        "total_duration_minutes": total_duration_minutes,
        "exercises_json": json.dumps(exercises, ensure_ascii=False),
        "status": "PENDING"
    }
    supabase.table("planned_workouts").insert(data).execute()
    return {"status": "ok"}

def get_all_sessions() -> List[Dict[str, Any]]:
    if not supabase: return []
    res = supabase.table("sessions").select("*, exercises(*)").order("date", desc=True).execute()
    return res.data

def save_recommendation(recommendation: str) -> Dict[str, Any]:
    if not supabase: return {}
    today = datetime.now().strftime("%Y-%m-%d")
    supabase.table("analyst_recommendations").insert({"date": today, "recommendation": recommendation}).execute()
    return {"status": "ok"}

def get_recent_recommendations(limit: int = 5) -> List[Dict[str, Any]]:
    if not supabase: return []
    res = supabase.table("analyst_recommendations").select("*").order("date", desc=True).limit(limit).execute()
    return res.data

def get_days_since_last_session() -> Optional[int]:
    """Calcula cuántos días han pasado desde el último entrenamiento."""
    if not supabase: return None
    res = supabase.table("sessions").select("date").order("date", desc=True).limit(1).execute()
    if not res.data:
        return None
    last_date = datetime.strptime(res.data[0]["date"], "%Y-%m-%d").date()
    delta = datetime.now().date() - last_date
    return delta.days

def get_exercise_history(name: str) -> List[Dict[str, Any]]:
    """Obtiene el historial de progreso de un ejercicio específico."""
    if not supabase: return []
    # Buscamos en la tabla de ejercicios filtrando por nombre
    res = supabase.table("exercises").select("*, sessions(date)").eq("name", name).execute()
    return res.data

def init_db():
    """Inicialización manual recomendada vía Supabase SQL Editor."""
    # Como el cliente Supabase-py es para datos, la creación de tablas 
    # se suele hacer desde el dashboard de Supabase para mayor control de seguridad (RLS).
    # Sin embargo, he preparado el esquema mental para que coincida.
    pass
