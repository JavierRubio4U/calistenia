"""
receptor.py - Agente Receptor (Agente 1)

╔══════════════════════════════════════════════════════════════════╗
║  RESPONSABILIDAD ÚNICA: Entender el reporte y guardarlo         ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Este agente es ESPECIALISTA en una sola cosa:                  ║
║  Tomar texto libre ("hoy he hecho 3 series de australianas      ║
║  y estaba reventado") y convertirlo en datos estructurados      ║
║  que se guardan en la base de datos.                            ║
║                                                                  ║
║  ¿POR QUÉ UN AGENTE SEPARADO?                                  ║
║  Porque si el Entrenador también tuviera que parsear reportes,  ║
║  su prompt sería enorme y cometería más errores. Cada agente    ║
║  hace UNA cosa bien → principio de responsabilidad única.       ║
║                                                                  ║
║  ¿POR QUÉ HAIKU?                                               ║
║  Usamos claude-haiku (el modelo más rápido y barato) porque     ║
║  extraer datos estructurados de texto es una tarea simple.      ║
║  No necesitas el modelo más potente para esto → ahorro de       ║
║  costes y latencia.                                             ║
╚══════════════════════════════════════════════════════════════════╝
"""

from .base import Agent
from database import save_session

# ─── SYSTEM PROMPT ─────────────────────────────────────────────
# El system prompt define la "personalidad" y reglas del agente.
# Es la pieza más importante: un buen prompt = un buen agente.
SYSTEM_PROMPT = """Eres el Agente Receptor de un sistema de entrenamiento de calistenia.

Tu ÚNICA responsabilidad es:
1. Recibir el reporte del usuario sobre su sesión de entrenamiento
2. Extraer datos estructurados: ejercicios, series, repeticiones, peso, fatiga, notas
3. Guardar los datos usando la herramienta save_session

REGLAS:
- Si no menciona la fecha, usa HOY: {today}
- El dato MÍNIMO son los ejercicios. Si no menciona ninguno, pide aclaración.
- fatigue_level: 1 (fresco) a 10 (destrozado)
- difficulty por ejercicio: 1 (fácil) a 10 (al fallo)
- "Al fallo" = difficulty 9-10
- "Me costó" = difficulty 7-8
- "Bien" / "cómodo" = difficulty 4-6
- Si dice el peso corporal, guárdalo en weight
- Responde SIEMPRE en español
- Tras guardar, da un resumen breve de lo que has guardado
- NO des consejos de entrenamiento (eso es trabajo del Entrenador)
"""

# ─── TOOLS ─────────────────────────────────────────────────────
# Las tools se definen en formato JSON Schema.
# El LLM lee esta definición y decide cuándo y cómo usarlas.
# Piensa en ellas como "las manos" del agente.
TOOLS = [
    {
        "name": "save_session",
        "description": "Guarda el reporte de una sesión de entrenamiento en la base de datos",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Fecha en formato YYYY-MM-DD"
                },
                "weight": {
                    "type": "number",
                    "description": "Peso corporal en kg"
                },
                "fatigue_level": {
                    "type": "integer",
                    "description": "Nivel de fatiga general 1-10"
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Duración de la sesión en minutos"
                },
                "notes": {
                    "type": "string",
                    "description": "Notas generales de la sesión"
                },
                "exercises": {
                    "type": "array",
                    "description": "Lista de ejercicios realizados",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Nombre del ejercicio"
                            },
                            "sets": {
                                "type": "integer",
                                "description": "Número de series"
                            },
                            "reps": {
                                "type": "string",
                                "description": "Repeticiones por serie (ej: '10', '8-10', 'al fallo')"
                            },
                            "weight": {
                                "type": "number",
                                "description": "Peso adicional/lastre en kg"
                            },
                            "difficulty": {
                                "type": "integer",
                                "description": "Dificultad percibida 1-10"
                            },
                            "notes": {
                                "type": "string",
                                "description": "Notas sobre el ejercicio"
                            }
                        },
                        "required": ["name"]
                    }
                }
            },
            "required": ["date", "exercises"]
        }
    }
]

# ─── TOOL HANDLERS ─────────────────────────────────────────────
# Conectamos el nombre de cada tool con su función Python.
# Cuando el LLM diga "quiero usar save_session({...})",
# el bucle agéntico (base.py) ejecutará database.save_session(**args).
TOOL_HANDLERS = {
    "save_session": save_session
}


def create_receptor_agent():
    """Crea una instancia del Agente Receptor."""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")

    return Agent(
        name="Receptor",
        system_prompt=SYSTEM_PROMPT.format(today=today),
        tools=TOOLS,
        tool_handlers=TOOL_HANDLERS,
        model="claude-haiku-4-5-20251001"  # Rápido y barato para parsing
    )
