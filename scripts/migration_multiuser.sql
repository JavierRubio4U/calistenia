-- ============================================================
-- Migration: Soporte multi-usuario
--
-- Añade user_email a todas las tablas y migra datos existentes
-- de Javi a su email real (carthagonova@gmail.com).
--
-- INSTRUCCIONES:
-- 1. Ve a https://supabase.com/dashboard/project/hhqgvccgadthuztwonzu/sql/new
-- 2. Pega todo este contenido y pulsa "Run"
-- ============================================================

-- 1. Añadir user_email a user_profile
ALTER TABLE public.user_profile
    ADD COLUMN IF NOT EXISTS user_email TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_profile_email
    ON public.user_profile(user_email);

-- 2. Añadir user_email a sessions
ALTER TABLE public.sessions
    ADD COLUMN IF NOT EXISTS user_email TEXT;

CREATE INDEX IF NOT EXISTS idx_sessions_user_email
    ON public.sessions(user_email);

-- 3. Añadir user_email a planned_workouts
ALTER TABLE public.planned_workouts
    ADD COLUMN IF NOT EXISTS user_email TEXT;

CREATE INDEX IF NOT EXISTS idx_planned_workouts_user_email
    ON public.planned_workouts(user_email);

-- 4. Añadir user_email a analyst_recommendations
ALTER TABLE public.analyst_recommendations
    ADD COLUMN IF NOT EXISTS user_email TEXT;

CREATE INDEX IF NOT EXISTS idx_analyst_recommendations_user_email
    ON public.analyst_recommendations(user_email);

-- 5. Migrar datos existentes de Javi
UPDATE public.user_profile
    SET user_email = 'carthagonova@gmail.com'
    WHERE user_email IS NULL;

UPDATE public.sessions
    SET user_email = 'carthagonova@gmail.com'
    WHERE user_email IS NULL;

UPDATE public.planned_workouts
    SET user_email = 'carthagonova@gmail.com'
    WHERE user_email IS NULL;

UPDATE public.analyst_recommendations
    SET user_email = 'carthagonova@gmail.com'
    WHERE user_email IS NULL;
