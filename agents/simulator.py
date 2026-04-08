"""
simulator.py - ARP Simulator

Simula un mes realista de entrenamiento para Javi (56 años, 135kg, fascitis plantar).
Genera sesiones ficticias con progresión semanal creíble y las guarda en la base de datos.
"""

from .base import Agent
from database import save_session, get_all_sessions


def create_simulator_agent(start_date: str, num_days: int = 28) -> Agent:
    """
    Crea un agente simulador que genera datos de entrenamiento realistas.

    Args:
        start_date: Fecha de inicio en formato YYYY-MM-DD.
        num_days: Número de días a simular (default 28).
    """

    system_prompt = f"""Eres un simulador de entrenamiento de calistenia para Javi.

PERFIL DE JAVI:
- 56 años, 135 kg, fascitis plantar
- Objetivo: colgar en barra 10 segundos, perder peso progresivamente
- Nivel actual: principiante-intermedio
- No puede correr ni saltar por la fascitis

EJERCICIOS DISPONIBLES:
- Colgado en barra (seconds por serie)
- Flexiones inclinadas en banco (reps por serie)
- Remo australiano (reps por serie)
- Sentadilla al banco (reps por serie)
- Plancha (seconds por serie)
- Sentadilla isométrica pared (seconds por serie)

INSTRUCCIONES DE SIMULACIÓN:
Simula {num_days} días de entrenamiento empezando el {start_date}.
Genera exactamente 12 sesiones totales (3 sesiones por semana × 4 semanas).
NO entrenes más de 2 días seguidos. Deja siempre al menos 1 día de descanso entre sesiones.

FECHAS OBLIGATORIAS (usa exactamente estas, calculadas desde {start_date}):
- Semana 1: días +1, +3, +5 del inicio
- Semana 2: días +8, +10, +12 del inicio
- Semana 3: días +15, +17, +19 del inicio
- Semana 4: días +22, +24, +26 del inicio

PROGRESIÓN REALISTA SEMANA A SEMANA:
- Semana 1: Inicio conservador. Peso: 135 kg. Colgado 3×5s, Flexiones 3×8, Remo 3×8.
- Semana 2: Pequeñas mejoras. Peso: 134.5 kg. Colgado 3×7s, Flexiones 3×10, Remo 3×10.
- Semana 3: Consolidación. Peso: 134 kg. Colgado 3×8s, Flexiones 3×12, Remo 3×12.
- Semana 4: Progresión notable. Peso: 133.5 kg. Colgado 3×10s, Flexiones 3×14, Remo 3×14.

VARIACIONES REALISTAS (añade estas para que parezca real):
- Algunos días Javi tiene DOLOR DE PIE → nota "dolor leve en pie derecho", reduce volumen 20%
- Algunos días tiene más energía → añade una serie extra
- La fatiga varía entre 3 y 8 según el esfuerzo
- Las notas son en español y naturales ("buena sesión", "me ha costado hoy", "el pie bien", etc.)

PARA CADA SESIÓN DE ENTRENAMIENTO debes:
1. Elegir una fecha válida dentro del rango (distribución 3-4 días/semana, sin 2 días seguidos)
2. Seleccionar 3-5 ejercicios del listado
3. Calcular valores realistas según la semana correspondiente
4. Llamar a save_session con:
   - date: fecha en YYYY-MM-DD
   - exercises: lista de dicts con keys: name, sets, reps, seconds, difficulty, notes
   - weight: peso corporal de esa semana
   - fatigue_level: 1-10
   - notes: nota natural de la sesión
   - duration_minutes: 35-45 minutos

IMPORTANTE:
- Llama a save_session UNA VEZ por cada una de las 12 fechas. No repitas fechas.
- Si save_session devuelve "already_exists", esa fecha ya está guardada — pasa a la siguiente.
- Si save_session devuelve "status: ok", la sesión se guardó correctamente — continúa.
- Usa reps=0 para ejercicios de tiempo (seconds>0) y seconds=0 para ejercicios de reps.
- No pares hasta haber guardado las 12 sesiones.

Al finalizar, lista las 12 fechas guardadas y resume el progreso observado.
"""

    return Agent(
        name="Simulador ARP",
        system_prompt=system_prompt,
        tools=[save_session, get_all_sessions],
        model_id="gemini-2.5-flash"
    )
