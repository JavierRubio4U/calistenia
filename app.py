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
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ─── CRÍTICO: cargar .env ANTES de importar nada que use credenciales ───
load_dotenv(Path(__file__).parent / ".env")

from database import init_db, get_user_profile, save_user_profile, get_all_users_admin, get_recent_recommendations
from agents import Orchestrator

ADMIN_EMAIL = "carthagonova@gmail.com"

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
user_display = st.user.name or user_email

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
col_title, col_logout = st.columns([4, 1])
with col_title:
    st.title(f"💪 Hola, {profile['name']}!")
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
    goals_text = profile.get("goals") or ""
    # Mostrar solo la primera frase/cláusula del objetivo
    first_clause = goals_text.split(",")[0].split(".")[0].strip()
    goals_display = first_clause[:30] + ("..." if len(first_clause) > 30 else "")
    st.metric("Objetivo", goals_display + " 🎯")

if profile.get("injuries") and profile["injuries"] not in ("Sin lesiones conocidas", "ninguna"):
    st.info(f"📍 {profile['injuries']}")

# ─── TABS ────────────────────────────────────────────────────
is_admin = (user_email.lower() == ADMIN_EMAIL.lower())
tab_names = ["🔥 Mi Entrenamiento", "📈 Mi Progreso", "📋 Recomendaciones", "💬 Preguntar al Coach"]
if is_admin:
    tab_names.append("🛡️ Admin")

tabs = st.tabs(tab_names)
tab1, tab2, tab_rec, tab3 = tabs[0], tabs[1], tabs[2], tabs[3]
tab_admin = tabs[4] if is_admin else None

# ─── TAB 1: ENTRENAMIENTO ─────────────────────────────────────
with tab1:
    st.subheader("Tu rutina de hoy")

    with st.form("form_rutina"):
        col_e, col_p = st.columns(2)
        with col_e:
            energia = st.slider("Nivel de energía", 1, 10, 7,
                                help="1 = agotado, 10 = con mucha energía")
        with col_p:
            dolor = st.checkbox("Me duele algo hoy", value=False)

        col_t, col_n = st.columns(2)
        with col_t:
            tiempo = st.radio("Tiempo disponible", ["30 min", "40 min", "60 min"],
                              index=1, horizontal=True)
        with col_n:
            nota_previa = st.text_input("Algo más que deba saber",
                                        placeholder="Ej: dormí mal, hombro molesto...")

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
        contexto = f"Nivel de energía hoy: {energia}/10."
        if dolor:
            contexto += " AVISO: el usuario reporta dolor hoy — adaptar ejercicios con precaución."
        else:
            contexto += " Sin dolor reportado hoy."
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

    # ─── REPORTE ─────────────────────────────────────────────
    st.subheader("¿Cómo te ha ido hoy?")
    modo = st.radio("Modo de reporte:", ["🎤 Voz", "⌨️ Texto"], horizontal=True)

    if modo == "🎤 Voz":
        audio_file = st.audio_input("Graba tu reporte")
        if audio_file is not None:
            if st.button("📤 Enviar reporte", use_container_width=True, type="primary"):
                with st.spinner("Procesando tu reporte..."):
                    try:
                        from google.genai import types
                        audio_bytes = audio_file.read()
                        mime_type = getattr(audio_file, "type", None) or "audio/wav"
                        st.caption(f"Formato detectado: `{mime_type}`")
                        multimodal_input = [
                            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                            "Aquí tienes mi reporte de entrenamiento de hoy."
                        ]
                        receptor_resp, analyst_resp = orchestrator.report_session(multimodal_input)
                        st.success("✅ Reporte guardado.")
                        st.markdown(receptor_resp)
                        if analyst_resp:
                            st.info(analyst_resp)
                    except Exception as e:
                        st.error(f"Error al procesar el audio: {e}")
    else:
        texto = st.text_area(
            "Escribe tu reporte:",
            placeholder="Ej: 3 series de 10s colgado, 10 flexiones en banco, peso 74.5kg, me ha ido bien",
            height=120,
        )
        if st.button("📤 Enviar reporte", use_container_width=True, type="primary",
                     disabled=not texto.strip()):
            with st.spinner("Procesando tu reporte..."):
                try:
                    receptor_resp, analyst_resp = orchestrator.report_session(texto)
                    st.success("✅ Reporte guardado.")
                    st.markdown(receptor_resp)
                    if analyst_resp:
                        st.info(analyst_resp)
                except Exception as e:
                    st.error(f"Error: {e}")

# ─── TAB 3: COACH ────────────────────────────────────────────
with tab3:
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
