"""
streamlit_app.py - Interfaz web de Calistenia Coach

Diseñada para móvil (usarla en el parque desde Android).
Desplegada en Streamlit Community Cloud → URL pública gratuita.

La clave GEMINI_API_KEY se configura en:
  - Local: fichero .env
  - Streamlit Cloud: Settings → Secrets → GEMINI_API_KEY = "AIza..."
"""

import streamlit as st
from pathlib import Path

# ── Cargar .env si existe (local) ──────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

from database import init_db, get_user_profile, get_all_sessions
from agents import Orchestrator

# ── Config de página ───────────────────────────────────────────
st.set_page_config(
    page_title="Calistenia Coach 💪",
    page_icon="💪",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ── CSS mínimo para mejorar móvil ──────────────────────────────
st.markdown("""
<style>
    .stButton button { height: 3rem; font-size: 1.1rem; }
    .stTextArea textarea { font-size: 1rem; }
    div[data-testid="metric-container"] { background: #1e1e2e; border-radius: 8px; padding: 8px; }
</style>
""", unsafe_allow_html=True)


# ── Inicialización (se ejecuta una vez por sesión) ─────────────
@st.cache_resource
def setup():
    """Inicializa DB y crea el orquestador (una sola vez)."""
    init_db()
    return Orchestrator()


orchestrator = setup()


# ── Cabecera con perfil ────────────────────────────────────────
def show_header():
    profile = get_user_profile()
    if profile:
        st.title(f"💪 Hola {profile['name']}!")
        col1, col2, col3 = st.columns(3)
        col1.metric("Peso actual", f"{profile['current_weight']} kg")
        col2.metric("Sesiones", len(get_all_sessions()))
        col3.metric("Meta peso", "< 135 kg 🎯")
        st.caption(f"_{profile['injuries']}_")
    else:
        st.title("💪 Calistenia Coach")


show_header()
st.divider()


# ── Tabs principales ───────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🏋️ Rutina de hoy", "📝 Reportar sesión", "📊 Mi progreso"])


with tab1:
    st.subheader("Rutina personalizada")
    st.caption("El entrenador revisará tu historial y diseñará 40 min seguros para ti.")

    if st.button("🚀 Generar mi rutina", use_container_width=True, type="primary"):
        with st.spinner("Tu entrenador está pensando..."):
            try:
                plan = orchestrator.get_workout_plan()
                st.session_state["last_plan"] = plan
            except Exception as e:
                st.error(f"Error: {e}")

    if "last_plan" in st.session_state:
        st.markdown(st.session_state["last_plan"])


with tab2:
    st.subheader("Cuéntame cómo fue")
    st.caption(
        "Escribe con naturalidad. Ej: *'5 segundos colgado, 10 "
        "flexiones en banco, piernas algo cargadas, peso 134.5kg'*"
    )

    report = st.text_area(
        "Tu reporte:",
        height=160,
        placeholder="Cuéntame qué has hecho hoy...",
        label_visibility="collapsed"
    )

    if st.button("✅ Guardar reporte", use_container_width=True, type="primary", disabled=not report.strip()):
        with st.spinner("Procesando..."):
            try:
                receptor_resp, analyst_resp = orchestrator.report_session(report)
                st.success("¡Guardado!")
                st.markdown(receptor_resp)
                if analyst_resp:
                    st.info("**Análisis de progreso:**\n\n" + analyst_resp)
            except Exception as e:
                st.error(f"Error: {e}")


with tab3:
    st.subheader("Tu evolución")
    sessions = get_all_sessions()

    if not sessions:
        st.info("Aún no hay sesiones. ¡Empieza reportando tu primera sesión!")
    else:
        st.caption(f"{len(sessions)} sesión(es) registrada(s).")

        if st.button("🔍 Analizar mi progreso", use_container_width=True, type="primary"):
            with st.spinner("Analizando tu evolución..."):
                try:
                    progress = orchestrator.analyze_progress()
                    st.session_state["last_progress"] = progress
                except Exception as e:
                    st.error(f"Error: {e}")

        if "last_progress" in st.session_state:
            st.markdown(st.session_state["last_progress"])

        # Historial rápido
        with st.expander("Ver historial de sesiones"):
            for s in sessions[:10]:
                st.markdown(f"**{s['date']}** — {len(s.get('exercises', []))} ejercicios"
                            + (f" | {s['weight']}kg" if s.get('weight') else ""))
