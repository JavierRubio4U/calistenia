-- Migration: añadir home_equipment al perfil de usuario
-- Ejecutar en Supabase SQL Editor

ALTER TABLE user_profile
ADD COLUMN IF NOT EXISTS home_equipment TEXT DEFAULT 'Mancuernas y esterilla';

-- Actualizar usuarios existentes con valor por defecto
UPDATE user_profile
SET home_equipment = 'Mancuernas y esterilla'
WHERE home_equipment IS NULL;
