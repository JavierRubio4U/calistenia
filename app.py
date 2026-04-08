"""
app.py - Interfaz Web Móvil (Streamlit) para Calistenia Coach

Diseñada para que Javi la use desde su Pixel 10a en el parque.
"""

import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import json

# Cargar entorno y lógica base
load_dotenv(Path(__file__).parent / ".env")
from database import init_db, get_user_profile
from agents import Orchestrator

# Configuración de página con estética premium
st.set_page_config(
    page_title="Calistenia Coach",
    page_icon="💪",
    layout="centered"
)

# Inicialización
if 'orchestrator' not in st.session_state:
    init_db()
    st.session_state.orchestrator = Orchestrator()

# Estilos personalizados (Aesthetics)
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; font-weight: bold; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 15px; border: 1px solid #3e4150; }
    h1, h2, h3 { color: #00ffcc; }
</style>
""", unsafe_allow_html=True)

# ─── HEADER / DASHBOARD ───
profile = get_user_profile()

if profile:
    st.title(f"💪 Hola, {profile['name']}!")
    
    # Métricas de Javi
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Peso", f"{profile['current_weight']} kg", delta=f"{profile['current_weight']-profile['initial_weight']:.1f} kg")
    with col2:
        st.metric("Objetivo", "10s Barra")
    
    st.info(f"📍 **Estado:** {profile['injuries']}")
else:
    st.warning("⚠️ Perfil no inicializado. Por favor, ejecuta la app CLI primero o reinicia el servidor.")

# ─── ACCIONES PRINCIPALES ───
tab1, tab2 = st.tabs(["🔥 Mi Entrenamiento", "📈 Mi Progreso"])

with tab1:
    st.subheader("Tu rutina de hoy")
    
    if st.button("🚀 Generar Rutina (Impacto 0)"):
        with st.spinner("Diseñando tu entrenamiento seguro..."):
            routine_md = st.session_state.orchestrator.get_workout_plan()
            st.session_state.current_routine = routine_md
            st.markdown(routine_md)
    
    st.divider()
    
    # --- FEEDBACK POR VOZ (Mobile Ready) ---
    st.subheader("¿Cómo te ha ido hoy?")
    audio_file = st.audio_input("Graba tu reporte final (Voz directa)")

    if audio_file is not None:
        if st.button("📤 Enviar Reporte a Gemini"):
            with st.spinner("Gemini está escuchando tu reporte..."):
                try:
                    # Preparar audio para el receptor
                    from google.genai import types
                    audio_bytes = audio_file.read()
                    
                    multimodal_input = [
                        types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
                        "Soy Javi. Aquí tienes mi reporte de hoy desde mi Pixel 10a."
                    ]
                    
                    receptor_resp, analyst_resp = st.session_state.orchestrator.report_session(multimodal_input)
                    
                    st.success("✅ Reporte procesado correctamente.")
                    st.markdown(f"**Chat:** {receptor_resp}")
                    if analyst_resp:
                        st.markdown(f"**Analista:** {analyst_resp}")
                        
                except Exception as e:
                    st.error(f"Error al procesar el audio: {e}")

with tab2:
    st.subheader("Historial y Logros")
    if st.button("🔍 Analizar mi progreso"):
        with st.spinner("Revisando tus datos..."):
            progress_md = st.session_state.orchestrator.analyze_progress()
            st.markdown(progress_md)
