"""
orchestrator.py - El Orquestador

╔══════════════════════════════════════════════════════════════════╗
║  PATRONES DE ORQUESTACIÓN EN SISTEMAS MULTI-AGENTE             ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Hay dos formas principales de coordinar agentes:               ║
║                                                                  ║
║  1. ORQUESTACIÓN DETERMINISTA (la que usamos aquí)              ║
║     → Lógica Python decide quién se ejecuta y cuándo            ║
║     → Predecible, fácil de debuggear                            ║
║     → Ideal cuando el flujo es conocido                         ║
║                                                                  ║
║  2. ORQUESTACIÓN CON LLM                                        ║
║     → Otro LLM decide a qué agente llamar                       ║
║     → Más flexible (entiende lenguaje natural)                  ║
║     → Útil cuando el flujo es ambiguo                           ║
║     → Más caro y menos predecible                               ║
║                                                                  ║
║  Para este proyecto usamos la opción 1 porque el flujo es       ║
║  claro: o pides rutina, o reportas sesión, o ves progreso.     ║
║  No necesitamos un LLM para decidir eso.                       ║
║                                                                  ║
║  EN EL FUTURO: si quisieras un chatbot que entienda "oye,      ║
║  ayer fui al parque e hice unas cuantas cosas, ah y dame       ║
║  la rutina de mañana", necesitarías orquestación con LLM.      ║
╚══════════════════════════════════════════════════════════════════╝
"""

from .receptor import create_receptor_agent
from .trainer import create_trainer_agent
from .analyst import create_analyst_agent
from database import get_all_sessions


class Orchestrator:
    """
    Coordina los 3 agentes del sistema.

    Flujos principales:
      get_workout_plan()  → Entrenador genera rutina
      report_session()    → Receptor guarda datos → Analista evalúa (si hay datos)
      analyze_progress()  → Analista hace informe completo
    """

    def __init__(self):
        # Creamos los agentes al iniciar.
        # Cada uno tiene su propio system prompt, tools y modelo.
        self.receptor = create_receptor_agent()
        self.trainer = create_trainer_agent()
        self.analyst = create_analyst_agent()

    def get_workout_plan(self):
        """
        Flujo: Pedir rutina de hoy

        Entrenador → [consulta DB] → [razona] → [genera rutina] → [guarda plan]

        El Entrenador automáticamente consultará el historial, la frecuencia
        semanal, y las recomendaciones del Analista antes de diseñar la rutina.
        No necesitamos decirle explícitamente qué hacer — su system prompt
        le da la autonomía para decidir.
        """
        return self.trainer.run(
            "Diseña la rutina de entrenamiento de calistenia para hoy. "
            "Consulta mi historial y adapta la rutina."
        )

    def report_session(self, report_text):
        """
        Flujo: Reportar sesión de entrenamiento

        Paso 1: Receptor → parsea texto → guarda en DB
        Paso 2: Si hay >= 3 sesiones → Analista evalúa → guarda recomendaciones

        Este flujo muestra ENCADENAMIENTO DE AGENTES:
        La salida del Receptor (datos guardados) habilita al Analista
        (que necesita datos para analizar).
        """
        # Paso 1: Receptor procesa el reporte
        receptor_response = self.receptor.run(report_text)

        # Paso 2: ¿Suficientes datos para análisis?
        sessions = get_all_sessions()
        analyst_response = None

        if len(sessions) >= 3:
            # El Analista se activa solo cuando hay datos suficientes.
            # Esto evita análisis vacíos y ahorra llamadas API.
            analyst_response = self.analyst.run(
                "Analiza el progreso del usuario con los datos disponibles "
                "y genera recomendaciones actualizadas."
            )

        return receptor_response, analyst_response

    def analyze_progress(self):
        """
        Flujo: Ver progreso (bajo demanda)

        Analista → [lee todo el historial] → [detecta patrones] → [recomienda]
        """
        sessions = get_all_sessions()
        if not sessions:
            return "No hay sesiones registradas todavía. Reporta tu primera sesión."

        return self.analyst.run(
            "Haz un análisis COMPLETO del progreso del usuario. "
            "Revisa todas las sesiones, identifica tendencias y genera "
            "recomendaciones detalladas."
        )
