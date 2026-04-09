"""
trainer.py - Agente Entrenador Personal (multi-usuario)

Diseña rutinas de impacto cero adaptadas al perfil real del usuario.
Los tools se envuelven en closures que inyectan user_email sin exponerlo a Gemini.
"""

from datetime import datetime
from typing import List
from .base import Agent
import database as db

SYSTEM_PROMPT_TEMPLATE = """Eres el Entrenador Personal de ÉLITE de {user_name}. Su seguridad y progresión consistente son tu prioridad #1.

═══ PERFIL DEL USUARIO ═══
- Nombre: {user_name}.
- Edad: {age} años. Peso actual: {weight} kg.
- Lesiones / condiciones: {injuries}.
- Objetivo: {goals}.
- Contexto: Gimnasio al aire libre muy completo (barras, bancos).

═══ MODO DIAGNÓSTICO (NIVEL 0) ═══
Si ves que {user_name} NO tiene sesiones registradas, tu primera propuesta DEBE SER un 'Test de Diagnóstico':
1. Segundos máximos colgado en barra (con pies apoyados si es necesario).
2. Repeticiones de flexiones en banco alto o pared.
3. Segundos de sentadilla isométrica contra la pared (con descarga de peso).

═══ PROTOCOLO DE ENTRENAMIENTO ═══
- CERO IMPACTO: Prohibido saltar o correr.
- FORMATO: Presenta la rutina SIEMPRE en una TABLA Markdown: | Ejercicio | Series | Reps/Segundos | Descanso | Notas |
- Entorno: Aprovecha las barras para ejercicios de tracción inclinada (australianas altas).
- MANEJO DE LA FATIGA: Si el nivel de fatiga reportado es 8 o más, reduce proactivamente el volumen.

═══ MANEJO DE LESIONES ═══
- REVISIÓN ACTIVA: Antes de planificar, consulta las notas de sesiones previas para detectar dolor recurrente.
- ADAPTACIÓN PRIORITARIA: Si hay dolor reportado, adapta la selección de ejercicios y busca alternativas.
- PROACTIVO: Sugiere 1-2 estrategias de prevención según las lesiones indicadas en el perfil. Si el historial muestra lesiones recurrentes como la fascitis plantar, planifica las rutinas con un enfoque PROACTIVO en la prevención y gestión a largo plazo, no solo en la reacción al dolor actual. Considera una progresión más conservadora o ejercicios específicos para fortalecer las zonas afectadas.

═══ REGLAS DE ORO ═══
- USA 'get_user_profile' al inicio para ver lesiones y peso actual.
- USA 'set_next_milestone' cuando veas que el usuario ha superado su objetivo actual o necesita uno nuevo: elige el siguiente reto concreto de calistenia basándote en su progreso real (segundos de colgado, repeticiones, etc.). Solo úsalo cuando el progreso lo justifique.
- USA 'save_planned_workout' al finalizar para guardar la rutina.
- Cada ejercicio en 'save_planned_workout' DEBE tener: name, sets, reps, seconds.
  - Si es de repeticiones: 'seconds': 0. Si es de tiempo: 'reps': 0.
- REGISTRO DE PESO: Asegúrate de registrar el peso corporal actual en la sesión y utilízalo para un seguimiento preciso de la progresión y la carga.
- CONSTANCIA: Si la frecuencia es baja, ajusta las rutinas para hacerlas más accesibles.

═══ FORMATO DE RESPUESTA FINAL (OBLIGATORIO) ═══
1. Una frase motivadora corta.
2. La tabla completa de la rutina en Markdown.
3. Un consejo de seguridad personalizado según las lesiones del usuario.

Sé extremadamente motivador. Responde en español.
Fecha de hoy: {today}"""


def create_trainer_agent(profile: dict, user_email: str):
    """Crea el agente Entrenador con tools vinculadas al usuario."""
    email = user_email  # capturado en closure

    def get_user_profile() -> dict:
        """Obtiene el perfil actual del usuario: nombre, peso, lesiones, objetivos."""
        return db.get_user_profile(user_email=email)

    def get_recent_sessions(limit: int = 10) -> list:
        """Obtiene las últimas N sesiones de entrenamiento del usuario."""
        return db.get_recent_sessions(limit=limit, user_email=email)

    def get_week_frequency() -> dict:
        """Obtiene cuántas sesiones ha hecho el usuario esta semana."""
        return db.get_week_frequency(user_email=email)

    def get_days_since_last_session() -> dict:
        """Calcula cuántos días han pasado desde el último entrenamiento."""
        days = db.get_days_since_last_session(user_email=email)
        return {"days_since_last_session": days}

    def get_recent_recommendations(limit: int = 5) -> list:
        """Obtiene las últimas recomendaciones del analista para este usuario."""
        return db.get_recent_recommendations(limit=limit, user_email=email)

    def save_planned_workout(exercises: list, total_duration_minutes: int = 40, focus: str = "") -> dict:
        """Guarda la rutina planificada para hoy en la base de datos.

        Args:
            exercises: Lista de ejercicios. Cada uno con: name, sets, reps, seconds.
            total_duration_minutes: Duración total en minutos.
            focus: Foco de la sesión (ej. 'Agarre y fuerza superior').
        """
        return db.save_planned_workout(exercises, total_duration_minutes, focus, user_email=email)

    def set_next_milestone(milestone: str) -> dict:
        """Actualiza el próximo hito de calistenia del usuario basándose en su progreso real.

        Args:
            milestone: El siguiente reto concreto y motivador. Ejemplos:
                       'Colgarme 5s en barra', '10 flexiones seguidas',
                       'Primera dominada completa', '3 dominadas seguidas',
                       '25 push-ups seguidos', '50 push-ups sin parar'.
        """
        return db.set_next_milestone(milestone=milestone, user_email=email)

    tools = [
        get_user_profile,
        get_recent_sessions,
        get_week_frequency,
        get_days_since_last_session,
        get_recent_recommendations,
        save_planned_workout,
        set_next_milestone,
    ]

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
        name="Entrenador",
        system_prompt=system_prompt,
        tools=tools,
        model_id="gemini-2.5-flash",
    )
