-- ============================================================
-- Calistenia Coach - Schema completo para Supabase (multi-usuario)
--
-- INSTRUCCIONES (instalación limpia):
-- 1. Ve a https://supabase.com/dashboard/project/hhqgvccgadthuztwonzu/sql/new
-- 2. Pega todo este contenido y pulsa "Run"
--
-- Si ya tienes la BD con datos de Javi, usa scripts/migration_multiuser.sql
-- ============================================================

-- 1. Perfil de usuario (uno por email de Google)
CREATE TABLE IF NOT EXISTS public.user_profile (
    id              BIGSERIAL PRIMARY KEY,
    user_email      TEXT UNIQUE,
    name            TEXT NOT NULL DEFAULT 'Usuario',
    age             INTEGER DEFAULT 30,
    initial_weight  DECIMAL(5,1),
    current_weight  DECIMAL(5,1),
    injuries        TEXT,
    goals           TEXT,
    last_updated    TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Rutinas planificadas por el Entrenador
CREATE TABLE IF NOT EXISTS public.planned_workouts (
    id                      BIGSERIAL PRIMARY KEY,
    user_email              TEXT,
    date                    TEXT NOT NULL,
    focus                   TEXT,
    total_duration_minutes  INTEGER DEFAULT 40,
    exercises_json          TEXT,
    status                  TEXT DEFAULT 'PENDING',  -- PENDING | COMPLETED
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Sesiones de entrenamiento realizadas
CREATE TABLE IF NOT EXISTS public.sessions (
    id                  BIGSERIAL PRIMARY KEY,
    user_email          TEXT,
    planned_workout_id  BIGINT REFERENCES public.planned_workouts(id),
    date                TEXT NOT NULL,
    weight              DECIMAL(5,1),
    duration_minutes    INTEGER DEFAULT 40,
    fatigue_level       INTEGER,
    general_notes       TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Ejercicios de cada sesión
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

-- 5. Recomendaciones del Agente Analista
CREATE TABLE IF NOT EXISTS public.analyst_recommendations (
    id              BIGSERIAL PRIMARY KEY,
    user_email      TEXT,
    date            TEXT NOT NULL,
    recommendation  TEXT NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Índices por usuario
CREATE INDEX IF NOT EXISTS idx_sessions_user_email ON public.sessions(user_email);
CREATE INDEX IF NOT EXISTS idx_planned_workouts_user_email ON public.planned_workouts(user_email);
CREATE INDEX IF NOT EXISTS idx_analyst_rec_user_email ON public.analyst_recommendations(user_email);

-- Desactivar RLS (autenticación gestionada por Streamlit OAuth)
ALTER TABLE public.user_profile               DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.planned_workouts           DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions                   DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.exercises                  DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.analyst_recommendations    DISABLE ROW LEVEL SECURITY;

-- Datos iniciales de Javi (solo si la tabla está vacía)
INSERT INTO public.user_profile (user_email, name, age, initial_weight, current_weight, injuries, goals)
SELECT
    'carthagonova@gmail.com', 'Javi', 56, 135.0, 135.0,
    'Fascitis plantar crónica (evitar impacto en planta del pie)',
    'Perder peso, colgarse 10 segundos en barra, mejorar agarre'
WHERE NOT EXISTS (SELECT 1 FROM public.user_profile LIMIT 1);
