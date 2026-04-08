"""
orchestrator.py - El Orquestador

Coordina el flujo entre los agentes: Receptor, Entrenador y Analista.
Implementa una orquestación determinista (basada en lógica Python).
"""

from typing import Union, List, Tuple, Optional
from .receptor import create_receptor_agent
from .trainer import create_trainer_agent
from .analyst import create_analyst_agent
from .coach import create_coach_agent
from database import get_all_sessions

class Orchestrator:
    """
    Coordina los agentes del sistema Calistenia Coach.
    """

    def __init__(self):
        # Inicialización de agentes especializados
        self.receptor = create_receptor_agent()
        self.trainer = create_trainer_agent()
        self.analyst = create_analyst_agent()
        self.coach = create_coach_agent()

    def get_workout_plan(self) -> str:
        """
        Flujo: Generar rutina del día.
        El Entrenador consulta autónomamente el historial en la DB.
        """
        return self.trainer.run(
            "Genera una rutina de calistenia de 40 minutos adaptada a mi historial actual. "
            "Usa tus herramientas para evaluar mi progreso y frecuencia."
        )

    def report_session(self, report_input: Union[str, List]) -> Tuple[str, Optional[str]]:
        """
        Flujo: Registrar sesión.
        Acepta texto o contenido multimodal (ej: audio cargado).
        
        1. El Receptor parsea y guarda en la DB.
        2. El Analista se activa si hay datos suficientes para actualizar recomendaciones.
        """
        # Paso 1: Procesar el reporte (Receptor)
        receptor_response = self.receptor.run(report_input)

        # Paso 2: Ejecutar analista si hay historial suficiente (>= 3 sesiones)
        sessions = get_all_sessions()
        analyst_response = None

        if len(sessions) >= 3:
            analyst_response = self.analyst.run(
                "Analiza las últimas sesiones guardadas y genera recomendaciones "
                "técnicas nuevas para mis próximos entrenamientos."
            )

        return receptor_response, analyst_response

    def ask_coach(self, question: Union[str, List]) -> str:
        """
        Flujo: Consulta al Coach.
        Acepta texto o audio con una pregunta sobre ejercicios, técnica, etc.
        """
        return self.coach.run(question)

    def analyze_progress(self) -> str:
        """
        Flujo: Análisis de progreso bajo demanda.
        """
        sessions = get_all_sessions()
        if not sessions:
            return "Aún no hay sesiones registradas. ¡Empieza a entrenar hoy!"

        return self.analyst.run(
            "Haz un análisis pormenorizado de mi evolución. Compara volumen, "
            "intensidad y fatiga. Dame un reporte de progreso completo."
        )
