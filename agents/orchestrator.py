"""
orchestrator.py - El Orquestador (multi-usuario)

Coordina el flujo entre los agentes: Receptor, Entrenador y Analista.
Cada instancia está vinculada a un usuario específico mediante user_email.
"""

from typing import Union, List, Tuple, Optional
from .receptor import create_receptor_agent
from .trainer import create_trainer_agent
from .analyst import create_analyst_agent
from .coach import create_coach_agent
import database as db


class Orchestrator:
    """
    Coordina los agentes del sistema Calistenia Coach para un usuario concreto.
    """

    def __init__(self, user_email: str, profile: dict):
        self.user_email = user_email
        self.profile = profile

        self.receptor = create_receptor_agent(profile=profile, user_email=user_email)
        self.trainer = create_trainer_agent(profile=profile, user_email=user_email)
        self.analyst = create_analyst_agent(profile=profile, user_email=user_email)
        self.coach = create_coach_agent(profile=profile, user_email=user_email)

    def get_workout_plan(self, context: str = "") -> str:
        """
        Flujo: Generar rutina del día.
        El Entrenador consulta autónomamente el historial en la DB.

        Args:
            context: Estado del usuario hoy (energía, dolor, tiempo disponible, etc.)
        """
        base_prompt = (
            "Genera una rutina de calistenia adaptada a mi historial actual. "
            "Usa tus herramientas para evaluar mi progreso y frecuencia."
        )
        if context:
            base_prompt = f"ESTADO DE HOY: {context}\n\n{base_prompt}"

        return self.trainer.run(base_prompt)

    def report_session(self, report_input: Union[str, List]) -> Tuple[str, Optional[str]]:
        """
        Flujo: Registrar sesión.
        Acepta texto o contenido multimodal (ej: audio cargado).

        1. El Receptor parsea y guarda en la DB.
        2. El Analista se activa si hay datos suficientes (>= 3 sesiones).
        """
        receptor_response = self.receptor.run(report_input)

        sessions = db.get_all_sessions(user_email=self.user_email)
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
        sessions = db.get_all_sessions(user_email=self.user_email)
        if not sessions:
            return "Aún no hay sesiones registradas. ¡Empieza a entrenar hoy!"

        return self.analyst.run(
            "Haz un análisis pormenorizado de mi evolución. Compara volumen, "
            "intensidad y fatiga. Dame un reporte de progreso completo."
        )
