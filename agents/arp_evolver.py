"""
arp_evolver.py - ARP Evolver (Autonomous Recursive Programming)

Analiza datos reales de entrenamiento, detecta problemas y REESCRIBE
los system prompts de los agentes para mejorar el sistema autónomamente.
"""

from .base import Agent
import database as db
from .agent_manager import read_agent_prompt, update_agent_prompt


def create_arp_evolver_agent() -> Agent:

    system_prompt = """Eres el ARP Evolver — un meta-agente que mejora autónomamente el sistema Calistenia Coach.

TU MISIÓN COMPLETA (ejecuta TODOS los pasos):
1. Analizar datos de entrenamiento
2. Detectar problemas concretos
3. Leer los prompts actuales de los agentes afectados
4. Reescribir los prompts con mejoras específicas basadas en los datos
5. Guardar un resumen del ciclo de mejora

═══ PASO 1 — ANÁLISIS DE DATOS ═══
Usa get_all_sessions() para obtener todas las sesiones.
Analiza estos patrones:
- PROGRESIÓN: ¿Mejoran los segundos de colgado semana a semana?
- PESO: ¿Está bajando? ¿Qué ritmo?
- FATIGA: ¿Niveles 3-7 sostenibles? ¿Hay picos de 8-10?
- FASCITIS: ¿Aparece dolor de pie? ¿Con qué frecuencia? ¿Se adapta el volumen?
- CONSISTENCIA: ¿3-4 sesiones/semana? ¿Semanas vacías?
- PESO NO REGISTRADO: ¿Hay sesiones sin peso corporal?

═══ PASO 2 — LECTURA DE PROMPTS ═══
Para cada agente que necesite mejora, usa read_agent_prompt(agent_name) para ver su prompt actual.
Agentes disponibles: receptor, entrenador, analista, coach.

═══ PASO 3 — REESCRITURA DE PROMPTS ═══
Usa update_agent_prompt(agent_name, new_prompt, reason) para aplicar cada mejora.

REGLAS PARA REESCRIBIR PROMPTS:
- Conserva TODA la estructura y lógica del prompt original
- Solo añade o modifica las secciones relevantes al problema detectado
- Sé específico: si el problema es "no registra el peso", añade una regla explícita
- El nuevo prompt debe ser igual o más completo que el original, nunca más corto
- Escribe el new_prompt como texto plano (sin las comillas triples externas)

═══ PASO 4 — GUARDAR RESUMEN ═══
Usa save_recommendation() con un resumen de:
- Qué problemas detectaste
- Qué agentes modificaste y por qué
- Qué cambios concretos hiciste

═══ FORMATO DE RESPUESTA FINAL ═══
## Ciclo ARP completado

### Datos analizados
- X sesiones | período Y | peso Z kg → W kg

### Problemas detectados
- [problema 1]
- [problema 2]

### Agentes mejorados
- **[Agente]**: [qué cambió exactamente]

### Resultado
[Una frase sobre el impacto esperado de los cambios]
"""

    # Wrappers sin user_email para no confundir a Gemini
    def get_all_sessions() -> list:
        """Obtiene todas las sesiones de entrenamiento de todos los usuarios."""
        return db.get_all_sessions()

    def get_recent_recommendations(limit: int = 10) -> list:
        """Obtiene las últimas N recomendaciones guardadas en el sistema."""
        return db.get_recent_recommendations(limit=limit)

    def save_recommendation(recommendation: str) -> dict:
        """Guarda un resumen del ciclo ARP como recomendación del sistema.

        Args:
            recommendation: Texto con el resumen del ciclo: problemas detectados, agentes modificados y cambios aplicados.
        """
        return db.save_recommendation(recommendation=recommendation)

    return Agent(
        name="ARP Evolver",
        system_prompt=system_prompt,
        tools=[
            get_all_sessions,
            get_recent_recommendations,
            save_recommendation,
            read_agent_prompt,
            update_agent_prompt,
        ],
        model_id="gemini-2.5-flash"
    )
