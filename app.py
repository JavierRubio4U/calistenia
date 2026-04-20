"""
app.py - Interfaz Web Móvil (Streamlit) para Calistenia Coach

Multi-usuario con Google OAuth.
- Cualquier cuenta Google puede registrarse.
- Onboarding en primer acceso: nombre, edad, peso, lesiones, objetivo.
- Cada usuario solo ve sus propios datos.
- Panel Admin (solo carthagonova@gmail.com) para ver usuarios activos.
"""

import streamlit as st
import os
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# ─── CRÍTICO: cargar .env ANTES de importar nada que use credenciales ───
load_dotenv(Path(__file__).parent / ".env")

from streamlit_autorefresh import st_autorefresh
from database import init_db, get_user_profile, save_user_profile, get_all_users_admin, get_recent_recommendations
from agents import Orchestrator

ADMIN_EMAIL = "carthagonova@gmail.com"

MILESTONE_DEFAULT = "Colgarme 5s en barra"

st.set_page_config(
    page_title="Calistenia Coach",
    page_icon="💪",
    layout="centered"
)

# ─── AUTENTICACIÓN ────────────────────────────────────────────
if not st.user.is_logged_in:
    st.title("💪 Calistenia Coach")
    st.markdown("Tu entrenador personal con IA. Acceso con Google.")
    if st.button("Entrar con Google", type="primary", use_container_width=True):
        st.login("google")
    st.stop()

user_email = st.user.email
st.session_state["_user_email"] = user_email
user_display = st.user.name or user_email

# ─── KEEPALIVE (ping cada 3 min, solo si la sesión del día está abierta) ─────
_hoy = datetime.now().strftime("%Y-%m-%d")
_dia_cerrado = st.session_state.get("session_closed_date") == _hoy
if not _dia_cerrado:
    st_autorefresh(interval=180_000, limit=None, key="keepalive_ping")

# ─── TIMEOUT DE SESIÓN (máx 4 horas) ────────────────────────────────────────
SESSION_TIMEOUT_HOURS = 4
if "session_start" not in st.session_state:
    st.session_state["session_start"] = datetime.now()
elif datetime.now() - st.session_state["session_start"] > timedelta(hours=SESSION_TIMEOUT_HOURS):
    st.warning("⏰ Tu sesión ha expirado tras 4 horas de actividad. Vuelve a entrar para continuar.")
    if st.button("🔒 Cerrar sesión", type="primary"):
        st.logout()
    st.stop()

# ─── INICIALIZACIÓN DB ───────────────────────────────────────
@st.cache_resource
def init_app():
    init_db()

try:
    init_app()
except Exception as e:
    st.error(f"⚠️ Error al conectar con la base de datos: {e}")
    st.stop()

# ─── ONBOARDING (primer acceso) ──────────────────────────────
profile = get_user_profile(user_email=user_email)

if not profile:
    st.title("👋 Bienvenido a Calistenia Coach")
    st.markdown(f"Hola **{user_display}**, antes de empezar cuéntanos un poco sobre ti.")

    with st.form("form_onboarding"):
        name = st.text_input("¿Cómo quieres que te llamemos?",
                             value=user_display.split()[0] if user_display else "")
        col_a, col_b = st.columns(2)
        with col_a:
            birth_year = st.number_input("Año de nacimiento",
                                         min_value=1940, max_value=2015, value=1975, step=1)
        with col_b:
            weight = st.number_input("Peso actual (kg)",
                                     min_value=30.0, max_value=300.0, value=75.0, step=0.5)
        injuries = st.text_area(
            "¿Tienes alguna lesión o condición física?",
            placeholder="Ej: fascitis plantar, dolor de rodilla... (escribe 'ninguna' si estás bien)",
            height=80,
        )
        goals = st.text_area(
            "¿Cuál es tu objetivo principal?",
            placeholder="Ej: perder peso, mejorar fuerza, hacer mi primera dominada...",
            height=80,
        )
        home_equipment = st.text_input(
            "¿Qué material tienes en casa para entrenar? (opcional)",
            placeholder="Ej: mancuernas hasta 12 kg y esterilla, bandas elásticas, barra dominadas...",
        )
        submit = st.form_submit_button("🚀 Comenzar mi entrenamiento",
                                       type="primary", use_container_width=True)

    if submit:
        if not name.strip():
            st.error("Por favor escribe tu nombre.")
        elif not goals.strip():
            st.error("Por favor indica tu objetivo.")
        else:
            age = datetime.now().year - int(birth_year)
            result = save_user_profile(
                user_email=user_email,
                name=name.strip(),
                weight=float(weight),
                age=age,
                injuries=injuries.strip() or "Sin lesiones conocidas",
                goals=goals.strip(),
                home_equipment=home_equipment.strip(),
            )
            if result.get("status") == "ok":
                st.success("¡Perfil creado! Cargando tu entrenador...")
                st.rerun()
            else:
                st.error(f"Error al guardar: {result.get('error')}")
    st.stop()

# ─── CARGAR ORQUESTADOR POR USUARIO ──────────────────────────
@st.cache_resource
def get_orchestrator(email: str, profile_id: int):
    p = get_user_profile(user_email=email)
    return Orchestrator(user_email=email, profile=p)

try:
    orchestrator = get_orchestrator(user_email, profile.get("id", 0))
except Exception as e:
    st.error(f"⚠️ Error al inicializar agentes: {e}")
    st.stop()

# ─── HEADER ──────────────────────────────────────────────────
col_title, col_profile, col_logout = st.columns([4, 1, 1])
with col_title:
    st.title(f"💪 Hola, {profile['name']}!")
with col_profile:
    st.write("")
    with st.popover("👤", use_container_width=True):
        st.markdown(f"**{profile['name']}** · {user_email}")
        st.divider()
        with st.form("form_perfil"):
            p_name = st.text_input("Nombre", value=profile.get("name", ""))
            p_birth = st.number_input("Año de nacimiento",
                                      min_value=1940, max_value=2015,
                                      value=datetime.now().year - int(profile.get("age") or 40),
                                      step=1)
            p_weight = st.number_input("Peso actual (kg)",
                                       min_value=30.0, max_value=300.0,
                                       value=float(profile.get("current_weight") or 75.0),
                                       step=0.5)
            p_injuries = st.text_area("Lesiones / condiciones",
                                      value=profile.get("injuries", ""),
                                      height=70)
            p_goals = st.text_area("Objetivo principal",
                                   value=profile.get("goals", ""),
                                   height=70)
            p_equipment = st.text_input("Material en casa",
                                        value=profile.get("home_equipment", ""),
                                        placeholder="Ej: mancuernas hasta 12kg, esterilla, bandas")
            if st.form_submit_button("💾 Guardar cambios", use_container_width=True, type="primary"):
                p_age = datetime.now().year - int(p_birth)
                res = save_user_profile(
                    user_email=user_email,
                    name=p_name.strip(),
                    weight=float(p_weight),
                    age=p_age,
                    injuries=p_injuries.strip() or "Sin lesiones conocidas",
                    goals=p_goals.strip(),
                    home_equipment=p_equipment.strip(),
                )
                if res.get("status") == "ok":
                    st.success("✅ Perfil actualizado")
                    st.cache_resource.clear()
                    st.rerun()
                else:
                    st.error(f"Error: {res.get('error')}")
with col_logout:
    st.write("")
    if st.button("Salir", use_container_width=True):
        st.logout()

col1, col2 = st.columns(2)
with col1:
    current = profile.get("current_weight") or 0
    initial = profile.get("initial_weight") or current
    delta = round(current - initial, 1)
    st.metric("Peso", f"{current} kg", delta=f"{delta:+.1f} kg")
with col2:
    milestone = profile.get("next_milestone") or MILESTONE_DEFAULT
    st.markdown("**Objetivo**")
    st.markdown(f"### {milestone} 🎯")

if profile.get("injuries") and profile["injuries"] not in ("Sin lesiones conocidas", "ninguna"):
    st.info(f"📍 {profile['injuries']}")

# ─── TABS ────────────────────────────────────────────────────
is_admin = (user_email.lower() == ADMIN_EMAIL.lower())
# ─── HELPERS RECEPTOR CHAT ───────────────────────────────────
def _build_receptor_context(exclude_last: bool = False) -> str:
    """Construye el contexto de la conversación anterior del receptor."""
    msgs = st.session_state.get("receptor_msgs", [])
    if exclude_last and msgs:
        msgs = msgs[:-1]
    if not msgs:
        return ""
    lines = []
    for m in msgs:
        role = "Usuario" if m["role"] == "user" else "Receptor"
        lines.append(f"{role}: {m['content']}")
    return "\n".join(lines)


def _check_receptor_done(response: str, orch) -> None:
    """Detecta si el receptor ha guardado la sesión y lanza el analista."""
    keywords = ["guardado", "guardada", "registrado", "registrada", "anotado", "anotada"]
    if any(kw in response.lower() for kw in keywords):
        st.session_state["receptor_done"] = True
        # Lanzar analista si hay suficientes sesiones
        import database as _db
        sessions = _db.get_all_sessions(user_email=st.session_state.get("_user_email", ""))
        if len(sessions) >= 3:
            try:
                analyst_resp = orch.analyst.run(
                    "Analiza las últimas sesiones guardadas y genera recomendaciones "
                    "técnicas nuevas para mis próximos entrenamientos."
                )
                if analyst_resp:
                    st.session_state["receptor_msgs"].append(
                        {"role": "assistant",
                         "content": f"📊 **Análisis del Analista:**\n\n{analyst_resp}"})
            except Exception:
                pass


tab_names = ["🔥 Mi Entrenamiento", "💬 Hablar con el Coach", "📈 Mi Progreso", "📋 Recomendaciones"]
if is_admin:
    tab_names.append("🛡️ Admin")

tabs = st.tabs(tab_names)
tab1, tab_coach, tab2, tab_rec = tabs[0], tabs[1], tabs[2], tabs[3]
tab_admin = tabs[4] if is_admin else None

# ─── TAB 1: ENTRENAMIENTO ─────────────────────────────────────
with tab1:
    st.subheader("Tu rutina de hoy")

    with st.form("form_rutina"):
        lugar = st.radio(
            "¿Dónde entrenas hoy?",
            ["🌳 Parque / Calistenia", "🏠 Casa"],
            horizontal=True,
        )

        col_e, col_t = st.columns(2)
        with col_e:
            energia = st.slider("Nivel de energía", 1, 10, 7,
                                help="1 = agotado, 10 = con mucha energía")
        with col_t:
            tiempo = st.radio("Tiempo disponible", ["30 min", "40 min", "60 min"],
                              index=1, horizontal=True)

        nota_previa = st.text_input(
            "¿Algo que deba saber hoy?",
            placeholder="Ej: dormí mal, me duele el hombro, tengo prisa..."
        )

        peso_hoy = st.number_input(
            "Peso hoy (kg)",
            min_value=30.0, max_value=300.0,
            value=float(profile.get("current_weight") or 75.0),
            step=0.5,
            help="Actualiza tu peso para un seguimiento preciso",
        )

        generar = st.form_submit_button("🚀 Generar Rutina",
                                        use_container_width=True, type="primary")

    if generar:
        lugar_limpio = "Casa" if lugar == "🏠 Casa" else "Parque / Calistenia"
        contexto = f"LUGAR HOY: {lugar_limpio}."
        contexto += f" Nivel de energía hoy: {energia}/10."
        contexto += f" Tiempo disponible: {tiempo}."
        if nota_previa.strip():
            contexto += f" Nota adicional: {nota_previa.strip()}."
        contexto += f" Peso corporal hoy: {peso_hoy} kg."

        with st.spinner("Diseñando tu entrenamiento personalizado..."):
            try:
                routine_md = orchestrator.get_workout_plan(context=contexto)
                st.session_state["routine"] = routine_md
            except Exception as e:
                st.error(f"Error: {e}")

    if "routine" in st.session_state:
        st.markdown(st.session_state["routine"])

    st.divider()

    # ─── REPORTE (chat multi-turno) ───────────────────────────
    st.divider()

    # Estado del reporte
    if "receptor_msgs" not in st.session_state:
        st.session_state["receptor_msgs"] = []
    if "receptor_done" not in st.session_state:
        st.session_state["receptor_done"] = False
    if "session_closed_date" not in st.session_state:
        st.session_state["session_closed_date"] = None
    if "mic_active" not in st.session_state:
        st.session_state["mic_active"] = False
    if "mic_used" not in st.session_state:
        st.session_state["mic_used"] = False

    today_str = datetime.now().strftime("%Y-%m-%d")
    session_closed = (st.session_state["session_closed_date"] == today_str)

    if session_closed:
        st.success("✅ Sesión del día cerrada. ¡Hasta mañana!")
        if st.button("🔓 Reabrir sesión"):
            st.session_state["session_closed_date"] = None
            st.rerun()
    else:
        col_titulo, col_cerrar = st.columns([4, 1])
        with col_titulo:
            st.subheader("¿Cómo te ha ido hoy?")
        with col_cerrar:
            st.write("")
            if st.button("🏁 Cerrar día", help="Oculta el micrófono y el reporte hasta mañana"):
                st.session_state["session_closed_date"] = today_str
                st.session_state["mic_active"] = False
                st.rerun()

        # Mostrar historial del chat
        for msg in st.session_state["receptor_msgs"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if not st.session_state["receptor_done"]:
            # ─── FATIGA (opcional) ────────────────────────────────────────
            with st.expander("⚡ Indicar fatiga manualmente (opcional)"):
                fatiga = st.slider(
                    "Fatiga al terminar",
                    min_value=1, max_value=10,
                    value=st.session_state.get("fatiga_hoy", 5),
                    help="1 = fresco · 10 = agotado. Si no lo tocas, el Receptor lo infiere de tu reporte.",
                    key="fatiga_slider",
                )
                st.session_state["fatiga_hoy"] = fatiga

            # Selector de modo — Voz por defecto
            modo_rep = st.radio("Modo:", ["🎤 Voz", "⌨️ Texto"], horizontal=True,
                                key="modo_rep", label_visibility="collapsed")

            if modo_rep == "🎤 Voz":
                # El micro SOLO aparece al pulsar el botón — evita activación automática en el coche
                if not st.session_state["mic_active"] and not st.session_state["mic_used"]:
                    if st.button("🎤 Activar grabación", use_container_width=True, type="primary"):
                        st.session_state["mic_active"] = True
                        st.rerun()
                else:
                    audio_file = st.audio_input("Graba tu reporte de hoy", key="audio_rep")
                    col_env, col_cancel = st.columns([3, 1])
                    with col_env:
                        enviar_audio = st.button("📤 Enviar", type="primary",
                                                 use_container_width=True,
                                                 disabled=audio_file is None)
                    with col_cancel:
                        if st.button("✕ Cancelar", use_container_width=True):
                            st.session_state["mic_active"] = False
                            st.rerun()

                    if audio_file and enviar_audio:
                        with st.spinner("Procesando audio..."):
                            try:
                                from google.genai import types as gtypes
                                audio_bytes = audio_file.read()
                                mime_type = getattr(audio_file, "type", None) or "audio/wav"
                                st.session_state["receptor_msgs"].append(
                                    {"role": "user", "content": "🎤 *Reporte de voz enviado*"})
                                st.session_state["mic_active"] = False
                                st.session_state["mic_used"] = True
                                fatiga_ctx = f"FATIGA REPORTADA POR EL USUARIO: {st.session_state.get('fatiga_hoy', 5)}/10.\n"
                                history_ctx = fatiga_ctx + _build_receptor_context()
                                multimodal = [
                                    gtypes.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                                    "Aquí tienes mi reporte de entrenamiento de hoy."
                                ]
                                resp = orchestrator.receptor.run(multimodal, context=history_ctx)
                                st.session_state["receptor_msgs"].append(
                                    {"role": "assistant", "content": resp})
                                _check_receptor_done(resp, orchestrator)
                            except Exception as e:
                                st.error(f"Error: {e}")
                        st.rerun()

            # Input de texto siempre disponible
            user_input = st.chat_input("Cuéntame cómo fue o responde al receptor...")
            if user_input:
                st.session_state["receptor_msgs"].append({"role": "user", "content": user_input})
                st.session_state["mic_active"] = False
                with st.spinner("Procesando..."):
                    try:
                        fatiga_ctx = f"FATIGA REPORTADA POR EL USUARIO: {st.session_state.get('fatiga_hoy', 5)}/10.\n"
                        history_ctx = fatiga_ctx + _build_receptor_context(exclude_last=True)
                        resp = orchestrator.receptor.run(user_input, context=history_ctx)
                        st.session_state["receptor_msgs"].append(
                            {"role": "assistant", "content": resp})
                        _check_receptor_done(resp, orchestrator)
                    except Exception as e:
                        resp = f"Error: {e}"
                        st.session_state["receptor_msgs"].append(
                            {"role": "assistant", "content": resp})
                st.rerun()

        else:
            st.success("✅ Sesión guardada correctamente.")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🔄 Reportar otra sesión", use_container_width=True):
                    st.session_state["receptor_msgs"] = []
                    st.session_state["receptor_done"] = False
                    st.session_state["mic_used"] = False
                    st.session_state["mic_active"] = False
                    st.rerun()
            with col_b:
                if st.button("🏁 Cerrar día", use_container_width=True, type="primary"):
                    st.session_state["session_closed_date"] = today_str
                    st.rerun()

# ─── TAB COACH ───────────────────────────────────────────────
with tab_coach:
    st.subheader("Pregunta al Coach")
    st.caption("Técnica, dudas sobre ejercicios, adaptaciones para tu lesión...")

    modo_coach = st.radio("Modo:", ["⌨️ Texto", "🎤 Voz"], horizontal=True, key="modo_coach")

    if modo_coach == "⌨️ Texto":
        pregunta = st.text_area(
            "Tu pregunta:",
            placeholder="Ej: ¿Cómo hago correctamente el remo australiano?",
            height=100,
            key="pregunta_coach",
        )
        if st.button("🤔 Preguntar", use_container_width=True, type="primary",
                     disabled=not (pregunta or "").strip()):
            with st.spinner("El Coach está pensando..."):
                try:
                    respuesta = orchestrator.ask_coach(pregunta)
                    st.session_state["coach_resp"] = respuesta
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        audio_coach = st.audio_input("Graba tu pregunta", key="audio_coach")
        if audio_coach is not None:
            if st.button("🤔 Preguntar", use_container_width=True, type="primary",
                         key="btn_coach_audio"):
                with st.spinner("El Coach está escuchando..."):
                    try:
                        from google.genai import types as gtypes
                        audio_bytes = audio_coach.read()
                        mime_type = getattr(audio_coach, "type", None) or "audio/wav"
                        multimodal = [
                            gtypes.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                            "Tengo esta duda sobre mis ejercicios:"
                        ]
                        respuesta = orchestrator.ask_coach(multimodal)
                        st.session_state["coach_resp"] = respuesta
                    except Exception as e:
                        st.error(f"Error: {e}")

    if "coach_resp" in st.session_state:
        st.markdown(st.session_state["coach_resp"])

# ─── TAB REC: RECOMENDACIONES DEL ANALISTA ───────────────────
with tab_rec:
    st.subheader("Recomendaciones del Analista")
    st.caption("Lo que el Analista ha ido anotando para mejorar tu entrenamiento.")
    with st.expander("ℹ️ ¿Qué es esto?", expanded=False):
        st.markdown(
            "Esta pestaña muestra la **comunicación interna entre agentes** del sistema. "
            "Cada vez que reportas una sesión, el **Agente Analista** revisa tu historial completo "
            "y deja notas técnicas en una base de datos compartida. "
            "El **Agente Entrenador** lee esas notas automáticamente antes de diseñar tu próxima rutina, "
            "sin que tú tengas que hacer nada. "
            "Es un ejemplo de *shared state* en programación agéntica: dos IAs coordinándose "
            "de forma asíncrona a través de una memoria persistente."
        )

    col_r, col_refresh = st.columns([5, 1])
    with col_refresh:
        if st.button("🔄", help="Actualizar"):
            st.session_state.pop("recomendaciones", None)

    if "recomendaciones" not in st.session_state:
        all_recs = get_recent_recommendations(limit=30, user_email=user_email)
        # Filtrar informes internos del ARP (son para el sistema, no para el usuario)
        analyst_recs = [r for r in all_recs if not r.get("recommendation", "").startswith("## Ciclo ARP")]
        st.session_state["recomendaciones"] = analyst_recs[:20]

    recs = st.session_state.get("recomendaciones", [])

    if not recs:
        st.info("El Analista aún no ha generado recomendaciones. Envía al menos 3 reportes de sesión para activarlo.")
    else:
        for rec in recs:
            date = rec.get("date", "")
            text = rec.get("recommendation", "")
            with st.container(border=True):
                st.caption(f"📅 {date}")
                st.markdown(text)

# ─── TAB 2: PROGRESO ─────────────────────────────────────────
with tab2:
    st.subheader("Historial y Logros")

    if st.button("🔍 Analizar mi progreso", use_container_width=True, type="primary"):
        with st.spinner("Revisando tus datos..."):
            try:
                progress_md = orchestrator.analyze_progress()
                st.session_state["progress"] = progress_md
            except Exception as e:
                st.error(f"Error: {e}")

    if "progress" in st.session_state:
        st.markdown(st.session_state["progress"])

# ─── TAB ADMIN (solo carthagonova@gmail.com) ─────────────────
if is_admin and tab_admin is not None:
    with tab_admin:
        st.subheader("Panel de Administración")
        st.caption(f"Acceso admin: {user_email}")

        if st.button("🔄 Actualizar", use_container_width=True):
            st.session_state.pop("admin_users", None)

        if "admin_users" not in st.session_state:
            with st.spinner("Cargando usuarios..."):
                try:
                    st.session_state["admin_users"] = get_all_users_admin()
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.session_state["admin_users"] = []

        users = st.session_state.get("admin_users", [])

        if not users:
            st.info("No hay usuarios registrados aún.")
        else:
            st.metric("Usuarios registrados", len(users))
            st.divider()
            for u in users:
                col_n, col_e, col_s, col_l = st.columns([2, 3, 1, 2])
                with col_n:
                    st.write(f"**{u.get('name', '?')}**")
                with col_e:
                    st.write(u.get("user_email", "?"))
                with col_s:
                    st.write(f"{u.get('session_count', 0)} sesiones")
                with col_l:
                    last = u.get("last_session")
                    st.write(f"Última: {last or 'Nunca'}")
