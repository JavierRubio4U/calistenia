"""
app.py - Interfaz Web Móvil (Streamlit) para Calistenia Coach

Diseñada para que Javi la use desde su Pixel 10a en el parque.
Protegida con Google OAuth — solo el email autorizado puede acceder.
"""

import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv

# ─── CRÍTICO: cargar .env ANTES de importar nada que use credenciales ───
load_dotenv(Path(__file__).parent / ".env")

from database import init_db, get_user_profile
from agents import Orchestrator

# Configuración de página
st.set_page_config(
    page_title="Calistenia Coach",
    page_icon="💪",
    layout="centered"
)

# ─── AUTENTICACIÓN ────────────────────────────────────────────
ALLOWED_EMAIL = os.getenv("ALLOWED_EMAIL", "")

if not st.user.is_logged_in:
    st.title("💪 Calistenia Coach")
    st.markdown("Tu entrenador personal con IA. Acceso privado.")
    if st.button("Entrar con Google", type="primary", use_container_width=True):
        st.login("google")
    st.stop()

if ALLOWED_EMAIL and st.user.email != ALLOWED_EMAIL:
    st.error(f"Acceso no autorizado: {st.user.email}")
    if st.button("Cerrar sesión"):
        st.logout()
    st.stop()

# ─── INICIALIZACIÓN ───────────────────────────────────────────
@st.cache_resource
def init_app():
    init_db()
    return Orchestrator()

try:
    orchestrator = init_app()
    profile = get_user_profile()
except Exception as e:
    st.error(f"⚠️ Error al conectar con la base de datos: {e}")
    st.info("Comprueba que SUPABASE_URL y SUPABASE_KEY están configuradas y que las tablas existen.")
    st.stop()

# ─── HEADER / DASHBOARD ──────────────────────────────────────
if profile:
    col_title, col_logout = st.columns([4, 1])
    with col_title:
        st.title(f"💪 Hola, {profile['name']}!")
    with col_logout:
        st.write("")
        if st.button("Salir", use_container_width=True):
            st.logout()

    col1, col2 = st.columns(2)
    with col1:
        current = profile.get('current_weight') or 0
        initial = profile.get('initial_weight') or current
        delta = round(current - initial, 1)
        st.metric("Peso", f"{current} kg", delta=f"{delta} kg")
    with col2:
        st.metric("Objetivo", "10s Barra 🎯")

    st.info(f"📍 {profile.get('injuries', '')}")
else:
    st.warning("⚠️ Perfil no encontrado. Ejecuta el SQL en Supabase dashboard primero.")
    st.stop()

# ─── ACCIONES PRINCIPALES ─────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🔥 Mi Entrenamiento", "📈 Mi Progreso", "💬 Preguntar al Coach"])

with tab1:
    st.subheader("Tu rutina de hoy")

    # ─── FORMULARIO PRE-ENTRENO ───────────────────────────────
    with st.form("form_rutina"):
        col_e, col_p = st.columns(2)
        with col_e:
            energia = st.slider("Nivel de energía", 1, 10, 7,
                                help="1 = agotado, 10 = con mucha energía")
        with col_p:
            dolor_pie = st.checkbox("Me duele el pie hoy", value=False)

        col_t, col_n = st.columns(2)
        with col_t:
            tiempo = st.radio("Tiempo disponible", ["30 min", "40 min", "60 min"],
                              index=1, horizontal=True)
        with col_n:
            nota_previa = st.text_input("Algo más que deba saber",
                                        placeholder="Ej: dormí mal, me duele el hombro...")

        generar = st.form_submit_button("🚀 Generar Rutina", use_container_width=True, type="primary")

    if generar:
        # Construir contexto del estado de hoy
        contexto_hoy = f"Nivel de energía de Javi hoy: {energia}/10."
        if dolor_pie:
            contexto_hoy += " AVISO: hoy tiene dolor en el pie — reducir volumen de piernas y extremar precauciones."
        else:
            contexto_hoy += " El pie está bien hoy."
        contexto_hoy += f" Tiempo disponible: {tiempo}."
        if nota_previa.strip():
            contexto_hoy += f" Nota adicional: {nota_previa.strip()}."

        with st.spinner("Diseñando tu entrenamiento seguro..."):
            try:
                routine_md = orchestrator.get_workout_plan(context=contexto_hoy)
                st.session_state["routine"] = routine_md
            except Exception as e:
                st.error(f"Error: {e}")

    if "routine" in st.session_state:
        st.markdown(st.session_state["routine"])

    st.divider()

    # ─── REPORTE (Voz o Texto) ────────────────────────────────
    st.subheader("¿Cómo te ha ido hoy?")

    modo = st.radio("Modo de reporte:", ["🎤 Voz", "⌨️ Texto"], horizontal=True)

    if modo == "🎤 Voz":
        audio_file = st.audio_input("Graba tu reporte")
        if audio_file is not None:
            if st.button("📤 Enviar reporte", use_container_width=True, type="primary"):
                with st.spinner("Gemini está escuchando tu reporte..."):
                    try:
                        from google.genai import types
                        audio_bytes = audio_file.read()
                        mime_type = getattr(audio_file, "type", None) or "audio/wav"
                        st.caption(f"Formato detectado: `{mime_type}`")

                        multimodal_input = [
                            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                            "Soy Javi. Aquí tienes mi reporte de entrenamiento de hoy."
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
            placeholder="Ej: 3 series de 10s colgado, 10 flexiones en banco, peso 134.5kg, me ha ido bien",
            height=120
        )
        if st.button("📤 Enviar reporte", use_container_width=True, type="primary", disabled=not texto.strip()):
            with st.spinner("Procesando tu reporte..."):
                try:
                    receptor_resp, analyst_resp = orchestrator.report_session(texto)
                    st.success("✅ Reporte guardado.")
                    st.markdown(receptor_resp)
                    if analyst_resp:
                        st.info(analyst_resp)
                except Exception as e:
                    st.error(f"Error: {e}")

with tab3:
    st.subheader("Pregunta al Coach")
    st.caption("Técnica, dudas sobre ejercicios, adaptaciones para tu lesión...")

    modo_coach = st.radio("Modo:", ["⌨️ Texto", "🎤 Voz"], horizontal=True, key="modo_coach")

    if modo_coach == "⌨️ Texto":
        pregunta = st.text_area(
            "Tu pregunta:",
            placeholder="Ej: ¿Cómo hago correctamente el remo australiano? ¿Qué hago si me duele el pie?",
            height=100,
            key="pregunta_coach"
        )
        if st.button("🤔 Preguntar", use_container_width=True, type="primary", disabled=not (pregunta or "").strip()):
            with st.spinner("El Coach está pensando..."):
                try:
                    respuesta = orchestrator.ask_coach(pregunta)
                    st.session_state["coach_resp"] = respuesta
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        audio_coach = st.audio_input("Graba tu pregunta", key="audio_coach")
        if audio_coach is not None:
            if st.button("🤔 Preguntar", use_container_width=True, type="primary", key="btn_coach_audio"):
                with st.spinner("El Coach está escuchando..."):
                    try:
                        from google.genai import types as gtypes
                        audio_bytes = audio_coach.read()
                        mime_type = getattr(audio_coach, "type", None) or "audio/wav"
                        multimodal = [
                            gtypes.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                            "Soy Javi. Tengo esta duda sobre mis ejercicios:"
                        ]
                        respuesta = orchestrator.ask_coach(multimodal)
                        st.session_state["coach_resp"] = respuesta
                    except Exception as e:
                        st.error(f"Error: {e}")

    if "coach_resp" in st.session_state:
        st.markdown(st.session_state["coach_resp"])

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
