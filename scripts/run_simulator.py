"""
run_simulator.py - ARP Simulator (multi-usuario)

Genera sesiones ficticias de entrenamiento y las guarda en Supabase.
Estrategia: Gemini genera los datos de CADA sesión → Python los guarda directamente.

Uso:
    python scripts/run_simulator.py
    python scripts/run_simulator.py --user-email javi@ejemplo.com
    python scripts/run_simulator.py --start 2026-03-01 --days 28 --user-email javi@ejemplo.com

Por defecto usa carthagonova@gmail.com (perfil de Javi).
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

import os
from google import genai
from google.genai import types
from database import save_session, get_all_sessions, get_user_profile


WEEK_PROFILES_DEFAULT = [
    {"weight": 135.0, "hang_s": 5,  "push_reps": 8,  "row_reps": 8,  "label": "Semana 1 - inicio conservador"},
    {"weight": 134.5, "hang_s": 7,  "push_reps": 10, "row_reps": 10, "label": "Semana 2 - pequeñas mejoras"},
    {"weight": 134.0, "hang_s": 8,  "push_reps": 12, "row_reps": 12, "label": "Semana 3 - consolidación"},
    {"weight": 133.5, "hang_s": 10, "push_reps": 14, "row_reps": 14, "label": "Semana 4 - progresión notable"},
]


def build_week_profiles(profile: dict) -> list:
    """Construye perfiles de progresión semanales a partir del perfil real del usuario."""
    base_weight = float(profile.get("current_weight") or profile.get("initial_weight") or 75.0)
    return [
        {"weight": base_weight,        "hang_s": 5,  "push_reps": 8,  "row_reps": 8,  "label": "Semana 1 - inicio conservador"},
        {"weight": base_weight - 0.5,  "hang_s": 7,  "push_reps": 10, "row_reps": 10, "label": "Semana 2 - pequeñas mejoras"},
        {"weight": base_weight - 1.0,  "hang_s": 8,  "push_reps": 12, "row_reps": 12, "label": "Semana 3 - consolidación"},
        {"weight": base_weight - 1.5,  "hang_s": 10, "push_reps": 14, "row_reps": 14, "label": "Semana 4 - progresión notable"},
    ]


def generate_session_data(client, date: str, week: int, week_profile: dict,
                          session_num: int, user_profile: dict) -> dict:
    """Pide a Gemini los datos de UNA sesión concreta. Sin tools."""

    name = user_profile.get("name", "el usuario")
    age = user_profile.get("age", 40)
    injuries = user_profile.get("injuries", "sin lesiones")
    goals = user_profile.get("goals", "mejorar condición física")

    prompt = f"""Genera los datos de UNA sesión de entrenamiento de calistenia para {name}.

PERFIL: {age} años, {week_profile['weight']} kg, {injuries}.
OBJETIVO: {goals}
FECHA: {date} ({week_profile['label']}, sesión {session_num} de la semana)
VALORES BASE: Colgado {week_profile['hang_s']}s, Flexiones {week_profile['push_reps']} reps, Remo {week_profile['row_reps']} reps

VARIACIÓN REALISTA:
- Con un 25% de probabilidad: dolor leve → reduce volumen un 20%, añade nota
- Con un 15% de probabilidad: día con mucha energía → añade una serie extra
- La fatiga debe estar entre 3 y 8
- Elige 3-5 ejercicios de: Colgado en barra, Flexiones inclinadas en banco, Remo australiano, Sentadilla al banco, Plancha, Sentadilla isométrica pared

Devuelve SOLO un JSON válido con esta estructura exacta:
{{
  "exercises": [
    {{"name": "Colgado en barra", "sets": 3, "reps": 0, "seconds": 8, "difficulty": 5, "notes": "buen agarre"}},
    {{"name": "Flexiones inclinadas en banco", "sets": 3, "reps": 12, "seconds": 0, "difficulty": 5, "notes": ""}}
  ],
  "weight": {week_profile['weight']},
  "fatigue_level": 5,
  "notes": "buena sesión",
  "duration_minutes": 40
}}"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return json.loads(response.text)


def build_dates(start_date: str, num_days: int) -> list:
    """Genera 12 fechas de entrenamiento distribuidas en 4 semanas (3 sesiones/semana)."""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    offsets = [1, 3, 5, 8, 10, 12, 15, 17, 19, 22, 24, 26]
    return [
        (start + timedelta(days=off)).strftime("%Y-%m-%d")
        for off in offsets
        if off <= num_days
    ]


def main():
    parser = argparse.ArgumentParser(description="Simulador de sesiones de entrenamiento")
    parser.add_argument("--start", default="2026-03-01", help="Fecha de inicio (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=28, help="Número de días a simular")
    parser.add_argument("--user-email", default="carthagonova@gmail.com",
                        help="Email del usuario a simular (debe tener perfil en la DB)")
    args = parser.parse_args()

    user_email = args.user_email

    # Cargar perfil real del usuario
    user_profile = get_user_profile(user_email=user_email)
    if not user_profile:
        print(f"❌ No se encontró perfil para '{user_email}'.")
        print("   Crea el perfil primero accediendo a la app o ejecutando el onboarding.")
        sys.exit(1)

    week_profiles = build_week_profiles(user_profile)

    print(f"\n{'='*60}")
    print(f"  ARP SIMULATOR")
    print(f"  Usuario: {user_profile.get('name')} ({user_email})")
    print(f"  Periodo: {args.start} -> {args.days} dias")
    print(f"{'='*60}\n")

    existing = {s["date"] for s in get_all_sessions(user_email=user_email)}
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    dates = build_dates(args.start, args.days)

    saved = 0
    skipped = 0

    for i, date in enumerate(dates):
        if date in existing:
            print(f"  [{date}] ya existe, omitiendo")
            skipped += 1
            continue

        week_idx = i // 3
        wp = week_profiles[min(week_idx, 3)]
        session_num = (i % 3) + 1

        try:
            data = generate_session_data(client, date, week_idx + 1, wp, session_num, user_profile)
            result = save_session(
                date=date,
                exercises=data["exercises"],
                weight=data.get("weight"),
                fatigue_level=data.get("fatigue_level"),
                notes=data.get("notes"),
                duration_minutes=data.get("duration_minutes", 40),
                user_email=user_email,
            )
            if result.get("status") == "ok":
                print(f"  [{date}] guardada (id={result['session_id']}, {result['ejercicios_guardados']} ejercicios)")
                saved += 1
            else:
                print(f"  [{date}] ERROR: {result}")
        except Exception as e:
            print(f"  [{date}] EXCEPCIÓN: {e}")

    print(f"\n{'='*60}")
    print(f"  Guardadas: {saved} | Omitidas: {skipped} | Total: {saved + skipped}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
