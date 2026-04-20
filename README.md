# 💪 Calistenia Coach — Sistema Multi-Agente con IA

> Entrenador personal adaptativo construido con **programación agéntica**.  
> Aprende de cada sesión y ajusta las rutinas automáticamente según historial real.

**🤖 Bot Telegram:** `@CalisteniaCoachBot` (interfaz principal)  
**🌐 Panel Admin:** https://calistenia-coach-8285977376.europe-west1.run.app

---

## 🧠 ¿Qué es la Programación Agéntica?

Un **agente** no es un chatbot. Es un LLM que puede **actuar** en el mundo real
a través de herramientas (tools), decidiendo autónomamente qué hacer y cuándo.

```
┌─────────────────────────────────────────────────────────────┐
│                   EL BUCLE AGÉNTICO                         │
│                                                             │
│   Tu mensaje                                                │
│       │                                                     │
│       ▼                                                     │
│   ┌───────┐    "Necesito ver el historial"    ┌──────────┐ │
│   │  LLM  │ ──────────────────────────────►  │ Tool:    │ │
│   │       │ ◄──────────────────────────────  │ get_     │ │
│   │       │    {sesiones: [...]}              │ sessions │ │
│   │       │                                  └──────────┘ │
│   │       │    "Necesito guardar el plan"     ┌──────────┐ │
│   │       │ ──────────────────────────────►  │ Tool:    │ │
│   │       │ ◄──────────────────────────────  │ save_    │ │
│   │       │    {status: "ok"}                │ workout  │ │
│   │       │                                  └──────────┘ │
│   │       │                                               │
│   │       │    "Ya tengo todo. Aquí tu rutina:"           │
│   └───────┘ ──────────────────────────────► Respuesta     │
│                                             final          │
└─────────────────────────────────────────────────────────────┘

 El LLM decide AUTÓNOMAMENTE:
   ✓ Qué tools usar        ✓ En qué orden
   ✓ Cuántas veces         ✓ Con qué parámetros
```

---

## 🏗️ Arquitectura del Sistema

```mermaid
graph TD
    U["👤 Usuario<br/>(voz o texto)"]

    subgraph TG["📱 Telegram Bot · Cloud Run"]
        B["telegram_bot.py<br/>Interfaz principal · min-instances=1"]
    end

    subgraph APP["🌐 Streamlit · Cloud Run"]
        A["app.py<br/>Panel de admin (OAuth Google)"]
    end

    subgraph ORQUESTADOR["🎯 Orchestrator"]
        O["orchestrator.py<br/>Coordinación determinista"]
    end

    subgraph AGENTES["🤖 Agentes Gemini"]
        R["📥 Receptor · Flash\nParsea reportes\n→ datos estructurados"]
        T["🏋️ Entrenador · Pro\nDiseña rutinas\nimpacto cero"]
        AN["📊 Analista · Pro\nDetecta progreso\ngenera recomendaciones"]
        C["💬 Coach · Pro\nResponde dudas\nde técnica y lesiones"]
    end

    subgraph DB["🗄️ Supabase · PostgreSQL"]
        S1["sessions"]
        S2["exercises"]
        S3["planned_workouts"]
        S4["analyst_recommendations"]
        S5["user_profile"]
    end

    U -->|"texto o audio .ogg"| B
    B --> O
    U -->|"admin"| A
    A --> O
    O -->|"reporte"| R
    O -->|"pedir rutina"| T
    O -->|"ver progreso"| AN
    O -->|"pregunta técnica"| C

    R -->|"save_session()"| S1
    R -->|"save_exercises()"| S2
    T -->|"lee historial"| S1
    T -->|"lee recomendaciones"| S4
    T -->|"save_planned_workout()"| S3
    AN -->|"lee todo"| S1
    AN -->|"save_recommendation()"| S4
    AN -->|"lee perfil"| S5
```

---

## 📱 Interfaz: Bot de Telegram

El bot es la interfaz principal. Funciona con comandos y botones de teclado:

```
/start · /menu   → Menú con 4 botones
/rutina          → Pregunta dónde entrenas (Parque / Casa) y genera rutina
/progreso        → Análisis de evolución con el Analista
/coach           → Modo consulta técnica (texto o audio)
/admin           → Resumen de usuarios registrados (solo admin)
Texto libre      → Receptor: registra la sesión de entrenamiento
Audio .ogg       → Receptor (multimodal): Gemini procesa el audio directamente
```

**Formato de rutina en Telegram:**
```
💪 ¡A por ello!

🏋️ *Colgado en barra* — 3×10s — 90s
🏋️ *Remo australiano* — 3×8 — 90s
🏋️ *Flexiones inclinadas* — 3×10 — 60s
🏋️ *Plancha frontal* — 3×30s — 60s

📖 *Remo australiano*
Qué es: Jalón horizontal con peso corporal desde barra baja.
Cómo: 1) Agarra barra a la altura de la cadera 2) Cuerpo recto 3) Tira del pecho a la barra
✅ Codos cerca del cuerpo · ❌ No dejes caer las caderas
```

---

## 🔄 Flujos Principales

### 1. Pedir rutina de hoy
```mermaid
sequenceDiagram
    actor Javi
    participant Bot
    participant Entrenador
    participant Supabase

    Javi->>Bot: /rutina → "Parque"
    Bot->>Entrenador: run("LUGAR HOY: Parque. Diseña rutina")
    Entrenador->>Supabase: get_recent_sessions(10)
    Supabase-->>Entrenador: [sesiones anteriores...]
    Entrenador->>Supabase: get_week_frequency()
    Supabase-->>Entrenador: {sessions_this_week: 2}
    Entrenador->>Supabase: get_days_since_last_session()
    Supabase-->>Entrenador: {days: 1}
    Entrenador->>Supabase: get_recent_recommendations()
    Supabase-->>Entrenador: [consejos del analista...]
    Note over Entrenador: Analiza frecuencia, grupos<br/>trabajados, fatiga → decide tipo sesión
    Entrenador->>Supabase: save_planned_workout(exercises)
    Entrenador-->>Bot: Lista de ejercicios
    Bot-->>Javi: 🏋️ Nombre — NxM — Xs
```

### 2. Reportar sesión (texto o audio)
```mermaid
sequenceDiagram
    actor Javi
    participant Bot
    participant Receptor
    participant Analista
    participant Supabase

    Javi->>Bot: Audio/Texto con reporte
    Bot->>Receptor: run([audio_bytes, "reporte"])
    Receptor->>Supabase: get_planned_workout()
    Supabase-->>Receptor: ejercicios planificados hoy
    Note over Receptor: Compara plan vs realidad<br/>Infiere fatiga del tono
    Receptor->>Supabase: save_session(date, exercises, fatigue...)
    Receptor-->>Bot: "¡Guardado! 3 series de colgado..."
    
    alt >= 3 sesiones en DB
        Bot->>Analista: run("Analiza progreso")
        Analista->>Supabase: get_all_sessions()
        Analista->>Supabase: save_recommendation("Subir a 4x15s...")
        Analista-->>Bot: Análisis de progreso
    end
    
    Bot-->>Javi: ✅ Confirmación + análisis
```

---

## 🤖 Los Agentes y su Lógica

### 📥 Receptor (`agents/receptor.py`)
- **Modelo:** Gemini Flash (más rápido, suficiente para parseo)
- **Input:** Texto libre o audio `.ogg`
- **Tools:** `get_user_profile`, `get_planned_workout`, `save_session`
- **Lógica especial:**
  - Carga el plan de hoy y pregunta si se completó
  - Infiere fatiga (1-10) del tono del reporte sin preguntar
  - Si el usuario dice "hice todo" → usa todos los ejercicios del plan

### 🏋️ Entrenador (`agents/trainer.py`)
- **Modelo:** Gemini Pro
- **Input:** `"LUGAR HOY: Parque"` o `"LUGAR HOY: Casa"`
- **Tools:** `get_user_profile`, `get_recent_sessions`, `get_week_frequency`, `get_days_since_last_session`, `get_recent_recommendations`, `save_planned_workout`, `set_next_milestone`
- **Lógica data-driven (3 pasos obligatorios):**
  1. Lee datos: frecuencia semanal, días consecutivos, ejercicios recientes, fatiga media
  2. Decide tipo de sesión: normal / equilibrada / suave / descanso activo
  3. Selecciona ejercicios con variedad real: nunca repite si apareció en las últimas 2 sesiones
- **Protocolos:** Parque (barras, colgado, equilibrio, inversión) / Casa (mancuernas, esterilla)

### 📊 Analista (`agents/analyst.py`)
- **Modelo:** Gemini Pro
- **Input:** Petición de análisis (se activa automáticamente tras ≥3 sesiones)
- **Tools:** `get_user_profile`, `get_all_sessions`, `get_exercise_history`, `save_recommendation`
- **Regla de fatiga:** Solo reporta fatiga si hay datos reales — nunca inventa valores

### 💬 Coach (`agents/coach.py`)
- **Modelo:** Gemini Pro
- **Input:** Pregunta técnica (texto o audio)
- **Tools:** `get_user_profile`, `get_recent_sessions`, `get_recent_recommendations`
- **Misión:** Responder dudas de técnica, adaptaciones por lesión, nutrición básica

### 🧪 Simulador (`agents/simulator.py`)
- **Modelo:** Gemini Flash
- **Misión:** Generar datos ficticios realistas para poblar la DB en desarrollo
- **Uso:** `python scripts/run_simulator.py --start 2026-03-01 --days 28`

### 🔄 ARP Evolver (`agents/arp_evolver.py`)
- **Modelo:** Gemini Pro
- **Misión:** Meta-agente que analiza patrones y propone mejoras a los system prompts
- **Uso:** `python scripts/run_arp.py`

---

## 🗄️ Schema de Base de Datos

```
user_profile          sessions              exercises
─────────────         ─────────────         ─────────────
id (PK)               id (PK)               id (PK)
user_email            user_email            session_id (FK)
name                  planned_workout_id    name
age                   date                  sets
initial_weight        weight                reps
current_weight        duration_minutes      seconds
injuries              fatigue_level         weight
goals                 general_notes         difficulty
home_equipment        created_at            notes
next_milestone
last_updated

planned_workouts      analyst_recommendations
─────────────         ───────────────────────
id (PK)               id (PK)
user_email            user_email
date                  date
focus                 recommendation
total_duration_min    created_at
exercises_json
status (PENDING/COMPLETED)
created_at
```

---

## 📁 Estructura del Proyecto

```
calistenia/
│
├── telegram_bot.py         # 📱 Bot de Telegram (interfaz principal)
├── app.py                  # 🌐 Panel admin Streamlit (Google OAuth)
├── main.py                 # 💻 CLI para uso local / Termux Android
├── database.py             # 🗄️ Capa de datos (Supabase SDK)
├── migration.py            # Auto-creación de tablas en Cloud Run
├── supabase_schema.sql     # SQL para crear tablas manualmente
│
├── agents/
│   ├── base.py             # ⭐ BUCLE AGÉNTICO EXPLÍCITO (leer primero)
│   ├── orchestrator.py     # Coordinación entre agentes
│   ├── receptor.py         # Agente: parseo de reportes + inferencia de fatiga
│   ├── trainer.py          # Agente: diseño de rutinas data-driven
│   ├── analyst.py          # Agente: análisis de progreso
│   ├── coach.py            # Agente: consultas técnicas y lesiones
│   ├── simulator.py        # Agente: generación de datos de prueba
│   └── arp_evolver.py      # Meta-agente: mejora autónoma de prompts
│
├── scripts/
│   ├── run_simulator.py    # Genera sesiones ficticias en Supabase
│   └── run_arp.py          # Ejecuta el ARP Evolver
│
├── Dockerfile              # Contenedor Streamlit (Cloud Run)
├── Dockerfile.telegram     # Contenedor Telegram bot (Cloud Run · min-instances=1)
├── deploy_cloud.ps1        # Deploy Streamlit a Cloud Run
├── deploy_telegram.ps1     # Deploy bot Telegram a Cloud Run
├── cloudbuild.telegram.yaml # Config Cloud Build para el bot
│
├── .streamlit/
│   ├── secrets.toml        # 🔒 Credenciales OAuth (no en git)
│   └── secrets.toml.example # Plantilla
│
├── .env                    # 🔒 Variables locales (no en git — ver .env.example)
└── requirements.txt        # Dependencias Python
```

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología | Por qué |
|---|---|---|
| **LLM** | Google Gemini (Flash + Pro) | Soporta audio nativo, function calling, multimodal |
| **Agent SDK** | `google-genai` | Automatic function calling, tool loop |
| **Base de datos** | Supabase (PostgreSQL) | Persiste entre reinicios, tier gratuito |
| **Interfaz principal** | python-telegram-bot 20.x | Funciona sin WebSocket persistente, perfecto para móvil |
| **Panel admin** | Streamlit + Google OAuth | Rapid prototyping, acceso protegido |
| **Despliegue** | Google Cloud Run | Escala a cero (coste ~0 en desuso), HTTPS gratis |
| **Contenedor** | Docker | Reproducible en cualquier entorno |

---

## 🚀 Instalación y Uso

### Requisitos
- Python 3.11+
- Cuenta en [Google AI Studio](https://aistudio.google.com/) (API key gratuita)
- Cuenta en [Supabase](https://supabase.com/) (tier gratuito)
- Bot de Telegram creado con [@BotFather](https://t.me/botfather)
- `gcloud` CLI (solo para despliegue en Cloud Run)

### Setup local
```bash
git clone https://github.com/JavierRubio4U/calistenia.git
cd calistenia

python -m venv venv
source venv/Scripts/activate   # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt

cp .env.example .env
# Editar .env con tus claves
```

### Crear tablas en Supabase (una sola vez)
1. Ve a https://supabase.com/dashboard → tu proyecto → **SQL Editor**
2. Pega el contenido de `supabase_schema.sql`
3. Ejecuta → "Success"

### Ejecutar localmente
```bash
# Bot Telegram
python telegram_bot.py

# Panel admin (Streamlit)
streamlit run app.py

# CLI
python main.py
```

### Desplegar en Cloud Run
```powershell
# Bot Telegram (min-instances=1 para mantener el polling activo)
.\deploy_telegram.ps1

# Panel admin Streamlit
.\deploy_cloud.ps1
```

---

## 🔑 Variables de Entorno

| Variable | Descripción | Dónde obtenerla |
|---|---|---|
| `GEMINI_API_KEY` | API key de Google Gemini | [aistudio.google.com](https://aistudio.google.com/apikey) |
| `SUPABASE_URL` | URL del proyecto Supabase | Dashboard → Settings → API |
| `SUPABASE_KEY` | Anon/public key de Supabase | Dashboard → Settings → API |
| `TELEGRAM_BOT_TOKEN` | Token del bot | [@BotFather](https://t.me/botfather) → /newbot |
| `TELEGRAM_ALLOWED_CHAT_ID` | Tu chat_id personal | [@RawDataBot](https://t.me/rawdatabot) → te lo envía |
| `CLI_USER_EMAIL` | Email del usuario por defecto (CLI/bot) | El tuyo |
| `ALLOWED_EMAIL` | Email con acceso al panel admin | El tuyo |

> **Nunca commitees `.env` ni `secrets.toml` — ya están en `.gitignore`**

---

## 💡 Conceptos Clave

### ¿Qué hace a esto "agéntico" y no solo un chatbot?

```
CHATBOT normal:           AGENTE:
─────────────────         ─────────────────────────────────────
Tú → pregunta             Tú → objetivo
LLM → respuesta           LLM → decide qué info necesita
                               → llama tools para obtenerla
                               → razona sobre los resultados
                               → vuelve a llamar tools si necesita más
                               → genera respuesta basada en datos reales
```

### Comunicación asíncrona entre agentes (Shared State)
El **Analista** no habla directamente con el **Entrenador**.
Escribe recomendaciones en Supabase → el Entrenador las lee en la siguiente petición.

```
Analista ──[save_recommendation()]──► Supabase
Entrenador ◄──[get_recent_recommendations()]── Supabase
```

### Orquestación determinista vs. con LLM
Este proyecto usa **orquestación determinista** (`orchestrator.py`, Python puro):
- `/rutina` → llama al Entrenador
- Texto libre → llama al Receptor, luego opcionalmente al Analista
- `/coach` → llama al Coach

Una alternativa sería usar otro LLM para decidir qué agente invocar (más flexible, más caro).

### Por qué Telegram en lugar de Streamlit para móvil
Streamlit usa WebSockets persistentes que se caen en conexiones móviles inestables.
Telegram usa HTTP polling — cada petición es independiente, nunca pierde el estado.
