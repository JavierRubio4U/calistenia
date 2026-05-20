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
from concurrent.futures import ThreadPoolExecutor
from .valeria import create_valeria_agent
from .analyst import create_analyst_agent
import database as db

logger = logging.getLogger(__name__)

_MAX_HISTORY = 20

# Keywords que indican que el mensaje necesita datos de BD
_RUTINA_KW  = {"rutina", "entreno", "parque", "casa", "minutos", "min", "ejercicio", "workout", "sesión", "sesion", "entrena"}
_REPORTE_KW = {"hice", "hice todo", "realicé", "completé", "entrené", "series", "repeticiones", "reps", "terminé", "acabe", "acabé", "reporte"}

def _needs_db(text: str) -> bool:
    """Clasificación local sin LLM: ¿necesita datos de BD este mensaje?"""
    if not isinstance(text, str):
        return True  # multimodal → por si acaso
    t = text.lower()
    return any(w in t for w in _RUTINA_KW | _REPORTE_KW)


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
        """Pre-fetcha TODOS los datos relevantes para Valeria en paralelo."""
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=6) as ex:
            f_profile    = ex.submit(db.get_user_profile,              user_email=self.user_email)
            f_sessions   = ex.submit(db.get_recent_sessions, 12,       user_email=self.user_email)
            f_week_freq  = ex.submit(db.get_week_frequency,            user_email=self.user_email)
            f_days_since = ex.submit(db.get_days_since_last_session,   user_email=self.user_email)
            f_recs       = ex.submit(db.get_recent_recommendations, 5, user_email=self.user_email)
            f_planned    = ex.submit(db.get_planned_workout,           user_email=self.user_email)
            profile    = f_profile.result()
            sessions   = f_sessions.result()
            week_freq  = f_week_freq.result()
            days_since = f_days_since.result()
            recs       = f_recs.result()
            planned    = f_planned.result()
        t1 = time.time()
        logger.info(f"[DB] parallel fetch TOTAL={t1-t0:.2f}s")
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
        # Solo prefetch si el mensaje lo requiere — conversación libre no necesita BD
        if context or _needs_db(user_input):
            data_ctx = self._full_context()
            logger.info("[Orchestrator] Modo RUTINA/REPORTE — contexto BD cargado")
        else:
            data_ctx = ""
            logger.info("[Orchestrator] Modo CONVERSACIÓN — sin prefetch BD")
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
