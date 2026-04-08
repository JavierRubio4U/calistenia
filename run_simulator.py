"""
run_simulator.py - ARP Simulator

Genera sesiones ficticias de entrenamiento para Javi y las guarda en Supabase.
Estrategia: Gemini genera los datos de CADA sesión individualmente → Python los guarda.
Esto evita el problema de Gemini alucinando errores en loops largos de tool calls.

Uso:
    python run_simulator.py
    python run_simulator.py --start 2026-03-01 --days 28
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import os
from google import genai
from google.genai import types
from database import save_session, get_all_sessions


WEEK_PROFILES = [
    {"weight": 135.0,   "hang_s": 5,  "push_reps": 8,  "row_reps": 8,  "label": "Semana 1 - inicio conservador"},
    {"weight": 134.5,   "hang_s": 7,  "push_reps": 10, "row_reps": 10, "label": "Semana 2 - pequeñas mejoras"},
    {"weight": 134.0,   "hang_s": 8,  "push_reps": 12, "row_reps": 12, "label": "Semana 3 - consolidación"},
    {"weight": 133.5,   "hang_s": 10, "push_reps": 14, "row_reps": 14, "label": "Semana 4 - progresión notable"},
]


def generate_session_data(client, date: str, week: int, profile: dict, session_num: int) -> dict:
    """Pide a Gemini los datos de UNA sesión concreta. Sin tools."""

    prompt = f"""Genera los datos de UNA sesión de entrenamiento de calistenia para Javi.

PERFIL DE JAVI: 56 años, {profile['weight']} kg, fascitis plantar.
FECHA: {date} ({profile['label']}, sesión {session_num} de la semana)
VALORES BASE: Colgado {profile['hang_s']}s, Flexiones {profile['push_reps']} reps, Remo {profile['row_reps']} reps

VARIACIÓN REALISTA para esta sesión:
- Con un 25% de probabilidad: dolor leve en pie → reduce volumen un 20%, añade nota sobre el pie
- Con un 15% de probabilidad: día con mucha energía → añade una serie extra
- La fatiga debe estar entre 3 y 8
- Elige 3-5 ejercicios de: Colgado en barra, Flexiones inclinadas en banco, Remo australiano, Sentadilla al banco, Plancha, Sentadilla isométrica pared

Devuelve SOLO un JSON válido con esta estructura exacta:
{{
  "exercises": [
    {{"name": "Colgado en barra", "sets": 3, "reps": 0, "seconds": 8, "difficulty": 5, "notes": "buen agarre"}},
    {{"name": "Flexiones inclinadas en banco", "sets": 3, "reps": 12, "seconds": 0, "difficulty": 5, "notes": ""}}
  ],
  "weight": {profile['weight']},
  "fatigue_level": 5,
  "notes": "buena sesión",
  "duration_minutes": 40
}}"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        )
    )

    data = json.loads(response.text)
    return data


def build_dates(start_date: str, num_days: int) -> list:
    """Genera 12 fechas de entrenamiento distribuidas en 4 semanas."""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    # 3 sesiones/semana × 4 semanas, separadas al menos 1 día
    offsets = [1, 3, 5, 8, 10, 12, 15, 17, 19, 22, 24, 26]
    dates = []
    for off in offsets:
        d = start + timedelta(days=off)
        if off <= num_days:
            dates.append(d.strftime("%Y-%m-%d"))
    return dates


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2026-03-01")
    parser.add_argument("--days", type=int, default=28)
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  ARP SIMULATOR")
    print(f"  Periodo: {args.start} -> {args.days} dias")
    print(f"{'='*60}\n")

    # Ver qué fechas ya existen
    existing = {s["date"] for s in get_all_sessions()}

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    dates = build_dates(args.start, args.days)

    saved = 0
    skipped = 0

    for i, date in enumerate(dates):
        if date in existing:
            print(f"  [{date}] ya existe, omitiendo")
            skipped += 1
            continue

        week_idx = i // 3  # 3 sesiones por semana
        profile = WEEK_PROFILES[min(week_idx, 3)]
        session_num = (i % 3) + 1

        try:
            data = generate_session_data(client, date, week_idx + 1, profile, session_num)
            result = save_session(
                date=date,
                exercises=data["exercises"],
                weight=data.get("weight"),
                fatigue_level=data.get("fatigue_level"),
                notes=data.get("notes"),
                duration_minutes=data.get("duration_minutes", 40)
            )
            if result.get("status") == "ok":
                print(f"  [{date}] guardada (id={result['session_id']}, {result['ejercicios_guardados']} ejercicios)")
                saved += 1
            else:
                print(f"  [{date}] ERROR: {result}")
        except Exception as e:
            print(f"  [{date}] EXCEPCION: {e}")

    print(f"\n{'='*60}")
    print(f"  Guardadas: {saved} | Omitidas: {skipped} | Total: {saved + skipped}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
