"""
app.py - Interfaz Web Móvil (Streamlit) para Calistenia Coach

Diseñada para que Javi la use desde su Pixel 10a en el parque.
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
    st.code("Ver supabase_schema.sql para crear las tablas.", language="text")
    st.stop()

# ─── HEADER / DASHBOARD ──────────────────────────────────────
if profile:
    st.title(f"💪 Hola, {profile['name']}!")

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

    if st.button("🚀 Generar Rutina (Impacto 0)", use_container_width=True, type="primary"):
        with st.spinner("Diseñando tu entrenamiento seguro..."):
            try:
                routine_md = orchestrator.get_workout_plan()
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
                        # Usar el MIME type real del archivo (webm en móvil, wav en desktop)
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
