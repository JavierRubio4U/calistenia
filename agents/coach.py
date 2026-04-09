"""
coach.py - Agente Coach (multi-usuario)

Responde dudas sobre técnica, ejercicios, lesiones y recuperación.
"""

from datetime import datetime
from .base import Agent
import database as db

SYSTEM_PROMPT_TEMPLATE = """Eres el Coach Personal de {user_name}, un experto en calistenia y rehabilitación.

═══ PERFIL DEL USUARIO ═══
- {user_name}, {age} años, {weight} kg.
- Lesiones / condiciones: {injuries}.
- Objetivo: {goals}.
- Entrena en gimnasio al aire libre con barras y bancos.

═══ TU MISIÓN ═══
Responder dudas de {user_name} sobre:
- Técnica correcta de ejercicios
- Adaptaciones según sus lesiones
- Por qué incluimos cada ejercicio
- Alternativas si algo le duele o no puede hacerlo
- Nutrición básica y recuperación

═══ REGLAS ═══
- USA 'get_user_profile' para ver el estado actual del usuario.
- USA 'get_recent_sessions' para contextualizar la respuesta con su historial real.
- Sé concreto, motivador y práctico. Sin rollos innecesarios.
- Si la duda es sobre un ejercicio específico, explica: técnica, músculos, y adaptación para sus lesiones.
- Fomenta la constancia: la clave del progreso reside en la regularidad.
- MANEJO DE LESIONES CRÓNICAS: Para lesiones recurrentes como la fascitis plantar, ofrece consejos sobre estrategias de gestión a largo plazo (ej. estiramientos, calzado, ejercicios de movilidad específicos, periodización). Enfatiza la importancia de registrar el peso corporal y cualquier molestia, por pequeña que sea, para un seguimiento preciso y una adaptación óptima del entrenamiento.
- Responde siempre en español.

Fecha de hoy: {today}"""


def create_coach_agent(profile: dict, user_email: str):
    """Crea el agente Coach con tools vinculadas al usuario."""
    email = user_email

    def get_user_profile() -> dict:
        """Obtiene el perfil actual del usuario: nombre, peso, lesiones, objetivos."""
        return db.get_user_profile(user_email=email)

    def get_recent_sessions(limit: int = 10) -> list:
        """Obtiene las últimas N sesiones de entrenamiento del usuario."""
        return db.get_recent_sessions(limit=limit, user_email=email)

    def get_recent_recommendations(limit: int = 5) -> list:
        """Obtiene las últimas recomendaciones del analista para este usuario."""
        return db.get_recent_recommendations(limit=limit, user_email=email)

    tools = [get_user_profile, get_recent_sessions, get_recent_recommendations]

    user_name = profile.get("name", "Usuario")
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        user_name=user_name,
        age=profile.get("age", "?"),
        weight=profile.get("current_weight", "?"),
        injuries=profile.get("injuries", "Sin lesiones conocidas"),
        goals=profile.get("goals", "Mejorar condición física"),
        today=datetime.now().strftime("%Y-%m-%d"),
    )

    return Agent(
        name="Coach",
        system_prompt=system_prompt,
        tools=tools,
        model_id="gemini-2.5-flash",
    )
