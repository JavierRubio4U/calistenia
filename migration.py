"""
migration.py - Auto-migración al arrancar en Cloud Run

Intenta crear las tablas si no existen usando psycopg2 (conexión directa).
Funciona desde Cloud Run (sin firewall). En local, puede fallar si el
puerto 5432 está bloqueado — en ese caso, usa supabase_schema.sql manualmente.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS public.user_profile (
    id              BIGSERIAL PRIMARY KEY,
    name            TEXT NOT NULL DEFAULT 'Javi',
    age             INTEGER DEFAULT 56,
    initial_weight  DECIMAL(5,1),
    current_weight  DECIMAL(5,1),
    injuries        TEXT,
    goals           TEXT,
    last_updated    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.planned_workouts (
    id                      BIGSERIAL PRIMARY KEY,
    date                    TEXT NOT NULL,
    focus                   TEXT,
    total_duration_minutes  INTEGER DEFAULT 40,
    exercises_json          TEXT,
    status                  TEXT DEFAULT 'PENDING',
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.sessions (
    id                  BIGSERIAL PRIMARY KEY,
    planned_workout_id  BIGINT REFERENCES public.planned_workouts(id),
    date                TEXT NOT NULL,
    weight              DECIMAL(5,1),
    duration_minutes    INTEGER DEFAULT 40,
    fatigue_level       INTEGER,
    general_notes       TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.exercises (
    id          BIGSERIAL PRIMARY KEY,
    session_id  BIGINT NOT NULL REFERENCES public.sessions(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    sets        INTEGER DEFAULT 1,
    reps        INTEGER DEFAULT 0,
    seconds     INTEGER DEFAULT 0,
    weight      DECIMAL(5,1) DEFAULT 0,
    difficulty  INTEGER,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS public.analyst_recommendations (
    id              BIGSERIAL PRIMARY KEY,
    date            TEXT NOT NULL,
    recommendation  TEXT NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.user_profile           DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.planned_workouts       DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions               DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.exercises              DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.analyst_recommendations DISABLE ROW LEVEL SECURITY;

INSERT INTO public.user_profile (name, age, initial_weight, current_weight, injuries, goals)
SELECT 'Javi', 56, 135.0, 135.0,
    'Fascitis plantar crónica (evitar impacto en planta del pie)',
    'Perder peso, colgarse 10 segundos en barra, mejorar agarre'
WHERE NOT EXISTS (SELECT 1 FROM public.user_profile LIMIT 1);
"""


def run_migration():
    """Ejecuta la migración via psycopg2. Silencioso si ya existen las tablas."""
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        print("[migration] SUPABASE_DB_URL no configurada, saltando auto-migración.")
        return

    try:
        import psycopg2
        conn = psycopg2.connect(db_url, connect_timeout=10)
        cur = conn.cursor()
        cur.execute(CREATE_TABLES_SQL)
        conn.commit()
        conn.close()
        print("[migration] Tablas verificadas/creadas correctamente.")
    except ImportError:
        print("[migration] psycopg2 no instalado, saltando auto-migración.")
    except Exception as e:
        print(f"[migration] No se pudo ejecutar (puede ser normal en local): {e}")


if __name__ == "__main__":
    run_migration()
