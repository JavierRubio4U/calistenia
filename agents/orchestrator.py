"""
orchestrator.py - El Orquestador (multi-usuario)

Coordina el flujo entre Valeria (agente unificado) y el Analista.
Cada instancia está vinculada a un usuario específico mediante user_email.
Mantiene historial de conversación por usuario (máx 20 items).
"""

import json
import time
import logging
from typing import Union, List, Optional
from .valeria import create_valeria_agent
from .analyst import create_analyst_agent
import database as db

logger = logging.getLogger(__name__)

_MAX_HISTORY = 20


class Orchestrator:
    """
    Coordina los agentes del sistema Calistenia Coach para un usuario concreto.
    """

    def __init__(self, user_email: str, profile: dict):
        self.user_email = user_email
        self.profile = profile

        self.valeria = create_valeria_agent(profile=profile, user_email=user_email)
        self.analyst = create_analyst_agent(profile=profile, user_email=user_email)

        # Historial de conversación por usuario: email → lista de types.Content
        self._history: dict = {}

    def _full_context(self) -> str:
        """Pre-fetcha TODOS los datos relevantes para Valeria, eliminando tool calls de lectura."""
        t0 = time.time()
        profile    = db.get_user_profile(user_email=self.user_email)
        t1 = time.time()
        sessions   = db.get_recent_sessions(limit=20, user_email=self.user_email)
        t2 = time.time()
        week_freq  = db.get_week_frequency(user_email=self.user_email)
        t3 = time.time()
        days_since = db.get_days_since_last_session(user_email=self.user_email)
        t4 = time.time()
        recs       = db.get_recent_recommendations(limit=5, user_email=self.user_email)
        t5 = time.time()
        planned    = db.get_planned_workout(user_email=self.user_email)
        t6 = time.time()
        logger.info(
            f"[DB] profile={t1-t0:.2f}s sessions={t2-t1:.2f}s week_freq={t3-t2:.2f}s "
            f"days_since={t4-t3:.2f}s recs={t5-t4:.2f}s planned={t6-t5:.2f}s "
            f"TOTAL_DB={t6-t0:.2f}s"
        )
        return (
            "═══ DATOS PRE-CARGADOS ═══\n"
            f"PERFIL: {json.dumps(profile, ensure_ascii=False, default=str)}\n"
            f"SESIONES COMPLETADAS (últimas 20, fuente de verdad para esfuerzo y variedad): {json.dumps(sessions, ensure_ascii=False, default=str)}\n"
            f"FRECUENCIA SEMANAL: {json.dumps(week_freq, ensure_ascii=False)}\n"
            f"DÍAS DESDE ÚLTIMA SESIÓN: {days_since}\n"
            f"RECOMENDACIONES ANALISTA: {json.dumps(recs, ensure_ascii=False, default=str)}\n"
            f"ÚLTIMA RUTINA PLANIFICADA (solo es un plan generado, NO implica que se haya realizado — lo realmente hecho está en SESIONES COMPLETADAS): {json.dumps(planned, ensure_ascii=False, default=str)}\n"
        )

    def chat(self, user_input: Union[str, List], context: str = "") -> str:
        """
        Punto de entrada unificado para toda interacción con Valeria.
        Pre-fetcha todos los datos, pasa historial y actualiza el historial tras la respuesta.

        Args:
            user_input: Texto o contenido multimodal del usuario.
            context: Contexto adicional (ej. lugar+tiempo para rutinas).
        """
        t0 = time.time()
        data_ctx = self._full_context()
        t1 = time.time()
        full_ctx = (context + "\n" if context else "") + data_ctx

        current_history = self._history.get(self.user_email, [])

        text, new_history = self.valeria.run(
            user_input,
            context=full_ctx,
            history=current_history,
            return_history=True,
        )
        t2 = time.time()
        logger.info(f"[Orchestrator] DB={t1-t0:.2f}s  Gemini={t2-t1:.2f}s  TOTAL={t2-t0:.2f}s")

        # Truncar historial a los últimos _MAX_HISTORY items
        self._history[self.user_email] = new_history[-_MAX_HISTORY:]

        return text

    def get_workout_plan(self, context: str = "") -> str:
        """
        Flujo: Generar rutina del día.
        Construye el mensaje con lugar+tiempo y lo pasa a chat().

        Args:
            context: Info de hoy — lugar, tiempo disponible, estado del usuario.
        """
        msg = f"Quiero rutina. {context}" if context else "Quiero rutina."
        return self.chat(msg)

    def analyze_progress(self) -> str:
        """
        Flujo: Análisis de progreso bajo demanda (Analyst — modelo Pro).
        """
        sessions = db.get_all_sessions(user_email=self.user_email)
        if not sessions:
            return "Aún no hay sesiones registradas. ¡Empieza a entrenar hoy!"

        return self.analyst.run(
            "Haz un análisis pormenorizado de mi evolución. Compara volumen, "
            "intensidad y fatiga. Dame un reporte de progreso completo."
        )
