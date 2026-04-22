"""
orchestrator.py - El Orquestador (multi-usuario)

Coordina el flujo entre los agentes: Receptor, Entrenador y Analista.
Cada instancia está vinculada a un usuario específico mediante user_email.
"""

import json
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

    def _trainer_data_context(self) -> str:
        """Pre-carga todos los datos que el Entrenador necesita, eliminando tool calls de lectura."""
        profile      = db.get_user_profile(user_email=self.user_email)
        sessions     = db.get_recent_sessions(limit=10, user_email=self.user_email)
        week_freq    = db.get_week_frequency(user_email=self.user_email)
        days_since   = db.get_days_since_last_session(user_email=self.user_email)
        recs         = db.get_recent_recommendations(limit=5, user_email=self.user_email)
        return (
            "\n\n═══ DATOS PRE-CARGADOS ═══\n"
            f"PERFIL: {json.dumps(profile, ensure_ascii=False, default=str)}\n"
            f"SESIONES RECIENTES (últimas 10): {json.dumps(sessions, ensure_ascii=False, default=str)}\n"
            f"FRECUENCIA SEMANAL: {json.dumps(week_freq, ensure_ascii=False)}\n"
            f"DÍAS DESDE ÚLTIMA SESIÓN: {days_since}\n"
            f"RECOMENDACIONES ANALISTA: {json.dumps(recs, ensure_ascii=False, default=str)}\n"
        )

    def _receptor_data_context(self) -> str:
        """Pre-carga perfil y plan de hoy para el Receptor, eliminando tool calls de lectura."""
        profile = db.get_user_profile(user_email=self.user_email)
        planned = db.get_planned_workout(user_email=self.user_email)
        return (
            "═══ DATOS PRE-CARGADOS ═══\n"
            f"PERFIL: {json.dumps(profile, ensure_ascii=False, default=str)}\n"
            f"PLAN DE HOY: {json.dumps(planned, ensure_ascii=False, default=str)}\n"
        )

    def get_workout_plan(self, context: str = "") -> str:
        """
        Flujo: Generar rutina del día.
        Pre-carga todos los datos en el contexto para eliminar tool calls de lectura.

        Args:
            context: Info de hoy — lugar, tiempo disponible, estado del usuario.
        """
        data_ctx = self._trainer_data_context()
        full_ctx = (context + "\n" if context else "") + data_ctx
        return self.trainer.run("Genera la rutina de hoy.", context=full_ctx)

    def report_session(self, report_input: Union[str, List]) -> Tuple[str, Optional[str]]:
        """
        Flujo: Registrar sesión.
        Acepta texto o contenido multimodal (ej: audio .ogg).
        El Analista ya NO se ejecuta automáticamente — solo bajo demanda en analyze_progress().
        """
        data_ctx = self._receptor_data_context()
        receptor_response = self.receptor.run(report_input, context=data_ctx)
        return receptor_response, None

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
