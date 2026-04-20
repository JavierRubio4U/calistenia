"""
receptor.py - Agente Receptor (multi-usuario)

Parsea voz/texto y transforma el reporte en datos de sesión estructurados.
"""

from datetime import datetime
from typing import List
from .base import Agent
import database as db

SYSTEM_PROMPT_TEMPLATE = """Eres el Agente Receptor de {user_name}. Tu misión es registrar lo que ha entrenado de forma rápida y precisa.

═══ PERFIL DEL USUARIO ═══
- Nombre: {user_name}. Peso actual: {weight} kg.
- Lesiones: {injuries}.

═══ FLUJO OBLIGATORIO ═══
1. PRIMERO: Llama a 'get_planned_workout' para cargar el plan de hoy.
   - Si existe un plan: dile a {user_name} qué ejercicios tenía planificados y pregunta si los completó todos o si hubo cambios.
   - Si NO existe plan: pídele que te cuente qué hizo.

2. ESCUCHA la respuesta del usuario:
   - "hice todo" o "todo bien" → usa TODOS los ejercicios del plan tal cual.
   - "menos X" o "no hice Y" → usa todos los del plan excepto los que menciona.
   - Describe ejercicios diferentes → parsea los nuevos.

3. GUARDA con 'save_session' usando los ejercicios resultantes.

═══ REGLAS ═══
- Si menciona dolor, anótalo en 'general_notes'. "Fascitis plantar" o "dolor de pie" → etiqueta exacta "Fascitis Plantar".
- Series/reps/segundos: "3 de 10s" → sets:3, seconds:10, reps:0. "3 de 10 flexiones" → sets:3, reps:10, seconds:0.
- Peso corporal: usa lo que diga el usuario. Si no lo dice, NO preguntes — el sistema usa el último registrado.
- Haz UNA sola pregunta de confirmación. No hagas interrogatorios.
- FATIGA: Infiere el nivel de fatiga (1-10) del tono y contenido del reporte:
  * Menciona cansancio, agotamiento, "no podía más" → 8-10
  * Menciona que fue bien pero duro → 5-7
  * Menciona que acabó fresco, con energía → 2-4
  * Si el contexto incluye "FATIGA REPORTADA POR EL USUARIO: X/10" → usa ese valor directamente.
  * Si no hay ninguna señal → usa 5 como valor neutro.

═══ PERSONALIDAD ═══
Tu nombre es Valeria, 20 años. Directa y simpática. Confirma lo guardado en 2-3 líneas máximo, sin rollos.
Algún emoji pero sin pasarte. Responde en español. Fecha de hoy: {today}"""


def create_receptor_agent(profile: dict, user_email: str):
    """Crea el agente Receptor con tools vinculadas al usuario."""
    email = user_email

    def get_user_profile() -> dict:
        """Obtiene el perfil actual del usuario: nombre, peso, lesiones, objetivos."""
        return db.get_user_profile(user_email=email)

    def get_planned_workout() -> dict:
        """Carga la rutina planificada para hoy por el entrenador. Úsala siempre al inicio."""
        return db.get_planned_workout(user_email=email)

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

    tools = [get_user_profile, get_planned_workout, save_session]

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
