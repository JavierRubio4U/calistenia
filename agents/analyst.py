"""
analyst.py - Agente Analista de Progreso (Agente 3)

╔══════════════════════════════════════════════════════════════════╗
║  COMUNICACIÓN ENTRE AGENTES                                     ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Este agente demuestra cómo los agentes se COMUNICAN:           ║
║                                                                  ║
║  El Analista NO habla directamente con el Entrenador.           ║
║  En su lugar, guarda recomendaciones en la base de datos        ║
║  (save_recommendation), y el Entrenador las lee después         ║
║  (get_recent_recommendations).                                  ║
║                                                                  ║
║  Esto es comunicación ASÍNCRONA entre agentes:                  ║
║                                                                  ║
║    Analista ──[guarda recomendación]──→ Base de Datos           ║
║    Entrenador ←──[lee recomendación]──── Base de Datos          ║
║                                                                  ║
║  ¿Por qué no directa? Porque el Analista no se ejecuta         ║
║  siempre. Solo cuando hay suficientes datos (>= 3 sesiones).   ║
║  La BD actúa como "buzón de mensajes" entre agentes.           ║
║                                                                  ║
║  PATRÓN: Shared State / Message Passing via Database            ║
║  Es uno de los patrones más comunes en sistemas multi-agente.   ║
╚══════════════════════════════════════════════════════════════════╝
"""

from .base import Agent
from database import get_all_sessions, get_exercise_history, save_recommendation

SYSTEM_PROMPT = """Eres un Analista de Progreso deportivo especializado en calistenia.

Tu trabajo es evaluar la evolución del usuario y generar RECOMENDACIONES
que el Agente Entrenador usará para diseñar las próximas rutinas.

═══ PROCESO DE ANÁLISIS ═══
1. Consulta todas las sesiones con get_all_sessions
2. Si necesitas detalle de un ejercicio específico, usa get_exercise_history
3. Analiza patrones:
   - ¿Aumentan las repeticiones/series con el tiempo?
   - ¿Ha subido de progresión? (ej: de australianas a dominadas negativas)
   - ¿Hay estancamiento? (mismas reps + difficulty > 3 sesiones seguidas)
   - ¿Fatiga consistentemente alta? (posible sobreentrenamiento)
   - ¿Cambios en peso corporal?
   - ¿Frecuencia semanal consistente o irregular?
4. Guarda tus recomendaciones con save_recommendation

═══ FORMATO DE RECOMENDACIONES ═══
Deben ser ESPECÍFICAS y ACCIONABLES:
  BIEN: "Subir australianas de 3x8 a 4x10. Si completa 4x10 con difficulty < 6, probar pies elevados"
  MAL:  "Hacer más repeticiones"

  BIEN: "Estancamiento detectado en flexiones (3 sesiones a 3x10, difficulty 7). Sugerir: flexiones diamante 3x6"
  MAL:  "Cambiar de ejercicio"

═══ REGLAS ═══
- SIEMPRE guarda al menos una recomendación con save_recommendation
- Si hay pocas sesiones (< 5), indica que necesitas más datos pero da feedback básico
- Si hay estancamiento → sugerir cambio de variante o método (pirámide, tempo, etc.)
- Si hay progreso → sugerir siguiente progresión
- Considera la frecuencia real (no es lo mismo 2 que 5 días/semana)
- Responde en español con un resumen claro del progreso
"""

TOOLS = [
    {
        "name": "get_all_sessions",
        "description": "Obtiene TODAS las sesiones de entrenamiento para análisis completo",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_exercise_history",
        "description": "Historial detallado de un ejercicio específico a lo largo del tiempo",
        "input_schema": {
            "type": "object",
            "properties": {
                "exercise_name": {
                    "type": "string",
                    "description": "Nombre del ejercicio (búsqueda parcial, ej: 'australiana')"
                }
            },
            "required": ["exercise_name"]
        }
    },
    {
        "name": "save_recommendation",
        "description": "Guarda una recomendación que el Entrenador leerá al diseñar la próxima rutina",
        "input_schema": {
            "type": "object",
            "properties": {
                "recommendation": {
                    "type": "string",
                    "description": "Recomendación detallada y accionable"
                }
            },
            "required": ["recommendation"]
        }
    }
]

TOOL_HANDLERS = {
    "get_all_sessions": get_all_sessions,
    "get_exercise_history": get_exercise_history,
    "save_recommendation": save_recommendation,
}


def create_analyst_agent():
    """Crea una instancia del Agente Analista."""
    return Agent(
        name="Analista",
        system_prompt=SYSTEM_PROMPT,
        tools=TOOLS,
        tool_handlers=TOOL_HANDLERS,
        model="claude-sonnet-4-6"  # Necesita razonamiento profundo para análisis
    )
