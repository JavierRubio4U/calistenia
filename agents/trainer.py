"""
trainer.py - Agente Entrenador Personal (Agente 2)

╔══════════════════════════════════════════════════════════════════╗
║  RESPONSABILIDAD: Diseñar rutinas adaptativas de 40 minutos     ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Este agente demuestra AUTONOMÍA en la toma de decisiones:      ║
║                                                                  ║
║  1. Primero CONSULTA el historial (usa varias tools)            ║
║  2. Luego RAZONA sobre los datos (cuántos días, fatiga, etc.)   ║
║  3. Finalmente DECIDE la rutina y la GUARDA                     ║
║                                                                  ║
║  Nadie le dice qué tools usar ni en qué orden. El LLM lee      ║
║  el system prompt, entiende su objetivo, y decide autónomamente ║
║  qué información necesita y qué herramientas llamar.            ║
║                                                                  ║
║  ESTE ES EL PODER DE LA PROGRAMACIÓN AGÉNTICA:                 ║
║  No programas "si X entonces Y". Le das al agente un objetivo,  ║
║  herramientas, y conocimiento → él decide el camino.            ║
╚══════════════════════════════════════════════════════════════════╝
"""

from .base import Agent
from database import (
    get_recent_sessions, get_week_frequency, get_days_since_last_session,
    save_planned_workout, get_recent_recommendations
)

SYSTEM_PROMPT = """Eres un Entrenador Personal especializado en CALISTENIA.
Tu trabajo es diseñar rutinas de EXACTAMENTE 40 minutos.

═══ ANTES DE DISEÑAR, SIEMPRE HAZ ESTO ═══
1. Consulta get_recent_sessions (para ver qué ha hecho el usuario)
2. Consulta get_week_frequency (para saber cuántos días entrena esta semana)
3. Consulta get_days_since_last_session (para saber el descanso)
4. Consulta get_recent_recommendations (para leer consejos del Analista)

═══ LÓGICA DE ADAPTACIÓN ═══
- +4 días sin entrenar → sesión suave: movilidad + ejercicios base + volumen bajo
- 2 días/semana → full body cada sesión, volumen medio-alto
- 3-4 días/semana → se puede hacer splits (superior/inferior), intensidad media-alta
- 5+ días/semana → MÁS variación, incluir días de movilidad/skill, cuidar volumen
- Fatiga última sesión > 7 → reducir volumen un 20%
- NUNCA repitas la rutina exacta de la última sesión → variedad siempre

═══ PROGRESIONES DE EJERCICIOS (de fácil a difícil) ═══
Tirón horizontal:  australianas pies suelo → pies elevados → con peso
Tirón vertical:    dead hangs → scapular pulls → negativas → dominadas → L-sit pulls
Empuje horizontal: flexiones inclinadas → normales → diamante → archer → pseudo planche
Empuje vertical:   pike push-ups → pike elevadas → HSPU negativas → HSPU
Piernas:           sentadillas → búlgaras → pistol asistidas → pistol → pistol con peso
Core:              plancha → hollow body → L-sit → front lever tucks → dragon flags
Dips:              asistidos → normales → lastrados

═══ FORMATO DE RUTINA (40 min) ═══
1. CALENTAMIENTO (5 min): movilidad articular + activación específica
2. BLOQUE PRINCIPAL (25-30 min): 4-6 ejercicios con series, reps, descanso
3. CORE (5 min): 2-3 ejercicios de core
4. VUELTA A LA CALMA (2-3 min): estiramientos principales

═══ REGLAS ═══
- SIEMPRE guarda la rutina con save_planned_workout
- Incluye TIEMPOS DE DESCANSO entre series (60-120s según intensidad)
- Adapta la progresión al nivel que ves en el historial
- Si no hay historial, empieza con nivel intermedio-bajo
- Responde en español con formato claro y legible

Fecha de hoy: {today}
"""

TOOLS = [
    {
        "name": "get_recent_sessions",
        "description": "Obtiene las últimas N sesiones con todos los ejercicios realizados",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Número de sesiones a obtener (default 10)"
                }
            }
        }
    },
    {
        "name": "get_week_frequency",
        "description": "Cuántas sesiones ha completado esta semana",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_days_since_last_session",
        "description": "Días transcurridos desde la última sesión",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_recent_recommendations",
        "description": "Recomendaciones recientes del Agente Analista de Progreso",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Número de recomendaciones (default 5)"
                }
            }
        }
    },
    {
        "name": "save_planned_workout",
        "description": "Guarda la rutina planificada para que quede registrada",
        "input_schema": {
            "type": "object",
            "properties": {
                "exercises": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "sets": {"type": "integer"},
                            "reps": {"type": "string"},
                            "rest_seconds": {"type": "integer"},
                            "notes": {"type": "string"}
                        },
                        "required": ["name", "sets", "reps"]
                    }
                },
                "total_duration_minutes": {
                    "type": "integer",
                    "description": "Duración total en minutos"
                },
                "focus": {
                    "type": "string",
                    "description": "Foco de la sesión (ej: 'tren superior', 'full body')"
                }
            },
            "required": ["exercises"]
        }
    }
]

TOOL_HANDLERS = {
    "get_recent_sessions": get_recent_sessions,
    "get_week_frequency": get_week_frequency,
    "get_days_since_last_session": get_days_since_last_session,
    "get_recent_recommendations": get_recent_recommendations,
    "save_planned_workout": save_planned_workout,
}


def create_trainer_agent():
    """Crea una instancia del Agente Entrenador."""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")

    return Agent(
        name="Entrenador",
        system_prompt=SYSTEM_PROMPT.format(today=today),
        tools=TOOLS,
        tool_handlers=TOOL_HANDLERS,
        model="claude-sonnet-4-6"  # Modelo potente: necesita razonar sobre datos
    )
