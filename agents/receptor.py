"""
receptor.py - Agente Receptor (multi-usuario)

Parsea voz/texto y transforma el reporte en datos de sesión estructurados.
"""

from datetime import datetime
from typing import List
from .base import Agent
import database as db

SYSTEM_PROMPT_TEMPLATE = """Eres el Agente Receptor de {user_name}. Tu misión es ser sus ojos y oídos digitales.

═══ PERFIL DEL USUARIO ═══
- Nombre: {user_name}. Peso inicial: {weight} kg.
- Lesiones: {injuries}.
- Objetivo: {goals}.

═══ REGLAS DE PARSEO ═══
1. Si {user_name} dice que le duele algo, anótalo siempre en 'general_notes'.
1.5. Si detectas la mención "fascitis plantar" o "dolor de pie" en las notas generales, etiquétalo específicamente como "Fascitis Plantar" en 'general_notes'.
2. Identifica claramente el trío: SERIES, REPETICIONES y SEGUNDOS.
3. Si dice "3 de 10 segundos", asigna sets: 3, seconds: 10, reps: 0.
4. Si dice "2 de 15 flexiones", asigna sets: 2, seconds: 0, reps: 15.
5. PESO CORPORAL: Si el usuario lo menciona, úsalo. Si no lo menciona, NO preguntes — el sistema usará automáticamente el último peso registrado. Solo pregunta si nunca se ha registrado ningún peso.
6. Al finalizar, invoca 'save_session' con la lista estructurada de ejercicios.

Confirma a {user_name} qué has guardado (ej: "¡Guardado! 3 series de colgado...").
Fecha de hoy: {today}"""


def create_receptor_agent(profile: dict, user_email: str):
    """Crea el agente Receptor con tools vinculadas al usuario."""
    email = user_email

    def get_user_profile() -> dict:
        """Obtiene el perfil actual del usuario: nombre, peso, lesiones, objetivos."""
        return db.get_user_profile(user_email=email)

    def save_session(date: str, exercises: List[dict], weight: float = None,
                     fatigue_level: int = None, notes: str = None,
                     duration_minutes: int = 40) -> dict:
        """Guarda la sesión de entrenamiento de hoy.

        Args:
            date: Fecha en formato YYYY-MM-DD.
            exercises: Lista de ejercicios con keys: name, sets, reps, seconds, difficulty, notes.
            weight: Peso corporal en kg. Si no se proporcionó, se usa el último peso conocido.
            fatigue_level: Nivel de fatiga 1-10.
            notes: Notas generales de la sesión.
            duration_minutes: Duración total en minutos.
        """
        if weight is None:
            profile = db.get_user_profile(user_email=email)
            weight = profile.get("current_weight") if profile else None
        return db.save_session(date, exercises, weight, fatigue_level, notes, duration_minutes, user_email=email)

    tools = [get_user_profile, save_session]

    user_name = profile.get("name", "Usuario")
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        user_name=user_name,
        weight=profile.get("current_weight", "?"),
        injuries=profile.get("injuries", "Sin lesiones conocidas"),
        goals=profile.get("goals", "Mejorar condición física"),
        today=datetime.now().strftime("%Y-%m-%d"),
    )

    return Agent(
        name="Receptor",
        system_prompt=system_prompt,
        tools=tools,
        model_id="gemini-2.5-flash",
    )
