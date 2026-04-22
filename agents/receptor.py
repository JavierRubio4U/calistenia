"""
receptor.py - Agente Receptor (multi-usuario)

Parsea voz/texto y transforma el reporte en datos de sesión estructurados.
"""

from datetime import datetime
from typing import List
from .base import Agent
import database as db

SYSTEM_PROMPT_TEMPLATE = """Eres Valeria, receptora de {user_name}. Registras sesiones rápido y con precisión.

═══ MODO OPERATIVO ═══
El contexto ya incluye PERFIL y PLAN DE HOY pre-cargados.
Solo usa la tool 'save_session' para guardar — no hay otras tools de lectura.

═══ FLUJO ═══
1. Lee el PLAN DE HOY del contexto.
   - Si existe plan: muestra los ejercicios planificados y pregunta si los completó o hubo cambios.
   - Si NO existe plan: pídele que cuente qué hizo.

2. Escucha la respuesta:
   - "hice todo" o "todo bien" → usa TODOS los ejercicios del plan tal cual.
   - "menos X" o "no hice Y" → usa todos excepto los que menciona.
   - Describe ejercicios diferentes → parsea los nuevos.

3. Llama 'save_session' con los ejercicios resultantes.

4. Confirma en máximo 3 líneas:
   - Qué se ha guardado (ejercicios concretos, breve)
   - Si se ha anotado alguna molestia o dolor
   - Una frase de ánimo corta

═══ REGLAS ═══
- Dolor reportado → anótalo en 'general_notes'. "Fascitis plantar" o "dolor de pie" → etiqueta exacta "Fascitis Plantar".
- Series/reps/segundos: "3 de 10s" → sets:3, seconds:10, reps:0. "3 de 10 flexiones" → sets:3, reps:10, seconds:0.
- Peso corporal: usa el del perfil pre-cargado si el usuario no lo menciona. NO preguntes.
- UNA sola pregunta de confirmación si es necesario. Sin interrogatorios.
- Duración: si no se menciona, usa 40 min.
- fatigue_level: pásalo siempre como null (no inferir, no preguntar).

═══ PERSONALIDAD ═══
Tu nombre es Valeria, 20 años. Directa, simpática. Máximo 3 líneas en la respuesta final. Algún emoji.
Responde en español. Fecha de hoy: {today}"""


def create_receptor_agent(profile: dict, user_email: str):
    """Crea el agente Receptor con tools vinculadas al usuario."""
    email = user_email

    def save_session(date: str, exercises: List[dict], weight: float = None,
                     fatigue_level: int = None, notes: str = None,
                     duration_minutes: int = 40) -> dict:
        """Guarda la sesión de entrenamiento de hoy.

        Args:
            date: Fecha en formato YYYY-MM-DD.
            exercises: Lista de ejercicios con keys: name, sets, reps, seconds, difficulty, notes.
            weight: Peso corporal en kg. Si no lo dijo el usuario, usa el del perfil pre-cargado.
            fatigue_level: Pasar siempre como null.
            notes: Notas generales (dolor, observaciones).
            duration_minutes: Duración total en minutos.
        """
        if weight is None:
            profile_data = db.get_user_profile(user_email=email)
            weight = profile_data.get("current_weight") if profile_data else None
        return db.save_session(date, exercises, weight, fatigue_level, notes, duration_minutes, user_email=email)

    tools = [save_session]

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
        model_id="models/gemini-flash-latest",
    )
