"""
analyst.py - Agente Analista de Progreso (multi-usuario)

Evalúa la evolución del usuario y detecta pequeños avances para mantener la motivación.
"""

from .base import Agent
import database as db

SYSTEM_PROMPT_TEMPLATE = """Eres el Analista Deportivo de ÉLITE de {user_name}.
Tu misión es detectar cada pequeño avance para mantener su motivación alta.

═══ PERFIL DEL USUARIO ═══
- Nombre: {user_name}. Peso inicial: {initial_weight} kg.
- Lesiones: {injuries}.
- Objetivo: {goals}.

═══ PROTOCOLO DE ANÁLISIS ═══
1. 'get_user_profile': Para recordar el peso inicial y las metas.
2. 'get_all_sessions' + 'get_exercise_history': Para ver la evolución de sus marcas.

═══ CRITERIOS DE RECONOCIMIENTO ═══
- PÉRDIDA DE PESO: Cualquier reducción desde el peso inicial es una gran victoria.
- FORTALEZA: Detecta mejoras en marcas personales de cada ejercicio.
- HABITUACIÓN: Celebra cada semana que entrene al menos 3 días.
- SEGURIDAD: Si hay dolor recurrente reportado, recomienda bajar la intensidad.

═══ RECOMENDACIONES TÉCNICAS ═══
- Sé extremadamente específico y alentador.
- Si hay estancamiento, sugiere fraccionar las series o variar el ejercicio.
- Guarda tus consejos usando 'save_recommendation'.
- Responde en español."""


def create_analyst_agent(profile: dict, user_email: str):
    """Crea el agente Analista con tools vinculadas al usuario."""
    email = user_email

    def get_user_profile() -> dict:
        """Obtiene el perfil actual del usuario: nombre, peso, lesiones, objetivos."""
        return db.get_user_profile(user_email=email)

    def get_all_sessions() -> list:
        """Obtiene todas las sesiones de entrenamiento del usuario."""
        return db.get_all_sessions(user_email=email)

    def get_exercise_history(name: str) -> list:
        """Obtiene el historial de progreso de un ejercicio específico.

        Args:
            name: Nombre exacto del ejercicio (ej. 'Colgado en barra').
        """
        return db.get_exercise_history(name=name, user_email=email)

    def save_recommendation(recommendation: str) -> dict:
        """Guarda una recomendación o consejo para el usuario.

        Args:
            recommendation: Texto con la recomendación técnica o motivacional.
        """
        return db.save_recommendation(recommendation=recommendation, user_email=email)

    tools = [get_user_profile, get_all_sessions, get_exercise_history, save_recommendation]

    user_name = profile.get("name", "Usuario")
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        user_name=user_name,
        initial_weight=profile.get("initial_weight", profile.get("current_weight", "?")),
        injuries=profile.get("injuries", "Sin lesiones conocidas"),
        goals=profile.get("goals", "Mejorar condición física"),
    )

    return Agent(
        name="Analista",
        system_prompt=system_prompt,
        tools=tools,
        model_id="gemini-2.5-pro",
    )
