"""
receptor.py - Agente Receptor Especializado (Javi)

Encargado de parsear voz/texto y transformarlo en datos de sesión.
"""

from datetime import datetime
from .base import Agent
from database import save_session, get_user_profile

SYSTEM_PROMPT = """Eres el Agente Receptor de Javi. Tu misión es ser sus ojos y oídos digitales.

═══ PERFIL DE JAVI ═══
- Peso inicial: 135 kg.
- Lesiones: Fascitis plantar.
- Objetivo: Perder peso y fortalecer agarre (colgarse en barra).

═══ REGLAS DE PARSEO ═══
1. Si Javi dice que le duele algo (ej. pie), anótalo siempre en 'general_notes'.
2. Identifica claramente el trío: SERIES, REPETICIONES y SEGUNDOS.
3. Si dice "3 de 10 segundos", asigna sets: 3, seconds: 10, reps: 0.
4. Si dice "2 de 15 flexiones", asigna sets: 2, seconds: 0, reps: 15.
5. Si menciona su peso hoy, pásalo en el argumento 'weight'.
6. Al finalizar, invoca 'save_session' con la lista estructurada de ejercicios.

Confirma a Javi qué has guardado (ej: "¡Guardado! 3 series de colgado...").
Fecha de hoy: {today}
"""

# Registro de herramientas: Pasamos las funciones directamente (Estándar de google-genai)
TOOLS = [get_user_profile, save_session]

def create_receptor_agent():
    today = datetime.now().strftime("%Y-%m-%d")
    return Agent(
        name="Receptor",
        system_prompt=SYSTEM_PROMPT.format(today=today),
        tools=TOOLS,
        model_id="gemini-2.5-flash"
    )
