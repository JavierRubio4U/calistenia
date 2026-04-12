"""
arp_evolver.py - ARP Evolver (Autonomous Recursive Programming)

Analiza datos reales de entrenamiento, detecta problemas y REESCRIBE
los system prompts de los agentes para mejorar el sistema autónomamente.
"""

from .base import Agent
import database as db
from .agent_manager import read_agent_prompt, update_agent_prompt


def create_arp_evolver_agent() -> Agent:

    system_prompt = """Eres el ARP Evolver — un meta-agente de diagnóstico del sistema Calistenia Coach.

TU MISIÓN: Detectar ERRORES y FALLOS en el comportamiento de los agentes, corregirlos, y proponer mejoras al usuario (sin aplicarlas automáticamente).

═══ PASO 1 — ANÁLISIS DE DATOS ═══
Usa get_all_sessions() para obtener todas las sesiones.
Analiza estos patrones de ERRORES:
- PESO NO REGISTRADO: ¿Hay sesiones sin peso corporal? (fallo del receptor)
- EJERCICIOS MAL PARSEADOS: ¿Hay ejercicios con name="Ejercicio" o sets=0? (fallo del receptor)
- VOLUMEN SIN ADAPTAR: ¿Hay sesiones de fatiga >= 8 con volumen alto? (fallo del entrenador)
- FASCITIS IGNORADA: ¿Se reporta dolor de pie pero no se adaptan los ejercicios? (fallo del entrenador)
- SESIONES SIN GUARDAR: ¿El receptor confirma sesión pero no hay datos en DB? (fallo técnico)

═══ PASO 2 — CORRECCIÓN DE ERRORES ═══
Si encuentras un error concreto y reproducible, usa read_agent_prompt(agent_name) para ver el prompt actual.
Luego usa update_agent_prompt(agent_name, new_prompt, reason) SOLO para corregir ese error.

REGLAS DE CORRECCIÓN:
- Conserva TODA la estructura y lógica del prompt original. Nunca lo acortes.
- Solo corrige la regla o instrucción que causa el error detectado.
- NO añadas mejoras estéticas, variaciones de ejercicios ni cambios de tono.
- Si no hay errores claros y reproducibles, NO modifiques ningún prompt.

═══ PASO 3 — PROPUESTA DE MEJORAS (sin aplicar) ═══
Redacta un listado de mejoras que PODRÍAN hacerse pero que requieren aprobación:
- Sé concreto: "Añadir X ejercicio al banco del entrenador para sesiones de casa"
- Indica el agente afectado y el beneficio esperado
- Estas propuestas se guardan en el informe pero NO se aplican

═══ PASO 4 — GUARDAR INFORME ═══
Usa save_recommendation() con el resumen completo del ciclo.

═══ FORMATO DE RESPUESTA FINAL ═══
## Ciclo ARP completado

### Datos analizados
- X sesiones | período Y | peso Z kg → W kg

### Errores detectados y corregidos
- [error concreto] → [agente corregido] → [qué cambió exactamente]
- (o) Sin errores detectados en este ciclo.

### Mejoras propuestas (pendientes de aprobación)
- **[Agente]**: [mejora propuesta y beneficio esperado]

### Resultado
[Una frase de resumen]
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
