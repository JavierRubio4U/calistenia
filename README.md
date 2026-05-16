# 💪 Calistenia Coach — Sistema Multi-Agente con IA

> Entrenador personal adaptativo construido con **programación agéntica**.  
> Aprende de cada sesión y ajusta las rutinas automáticamente según historial real.

**🤖 Interfaz:** Bot de Telegram (única interfaz — `@calistenia_javi_bot`)

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
│   ┌───────┐    "Necesito guardar el plan"     ┌──────────┐  │
│   │  LLM  │ ──────────────────────────────►  │ Tool:    │  │
│   │       │ ◄──────────────────────────────  │ save_    │  │
│   │       │    {status: "ok"}                │ workout  │  │
│   │       │                                  └──────────┘  │
│   │       │    "Necesito guardar la sesión"   ┌──────────┐  │
│   │       │ ──────────────────────────────►  │ Tool:    │  │
│   │       │ ◄──────────────────────────────  │ save_    │  │
│   │       │    {status: "ok"}                │ session  │  │
│   │       │                                  └──────────┘  │
│   │       │                                                 │
│   │       │    "Listo. Aquí tu rutina:"                     │
│   └───────┘ ──────────────────────────────► Respuesta final │
└─────────────────────────────────────────────────────────────┘

 El LLM decide AUTÓNOMAMENTE:
   ✓ Qué tools usar        ✓ En qué orden
   ✓ Cuántas veces         ✓ Con qué parámetros
```

---

## 🏗️ Arquitectura del Sistema

```
                         ┌─────────────────────────────────────────┐
                         │  Cloud Run · min-instances=1 · max=1    │
  👤 Usuario             │                                         │
  (texto/audio)    ──►   │  telegram_bot.py                        │
                         │    ├─ asyncio.Lock por chat_id          │
                         │    └─ asyncio.to_thread (no bloquea)    │
                         └───────────────┬─────────────────────────┘
                                         │
                         ┌───────────────▼─────────────────────────┐
                         │  orchestrator.py                        │
                         │    Pre-fetcha TODOS los datos de DB     │
                         │    antes de llamar al LLM               │
                         └─────┬────────────────────────┬──────────┘
                               │ chat()                 │ analyze_progress()
                ┌──────────────▼──────────┐   ┌────────▼──────────┐
                │  Valeria (valeria.py)   │   │ Analista          │
                │  gemini-2.5-flash       │   │ (analyst.py)      │
                │  Agente Unificado:      │   │ gemini-2.5-flash  │
                │  · Diseña rutinas       │   │ Solo con /progreso│
                │  · Registra sesiones    │   └────────┬──────────┘
                │  · Responde preguntas   │            │
                │  · Detecta hitos        │            │
                └──────────┬─────────────┘            │
                           │                          │
                ┌──────────▼──────────────────────────▼──────────┐
                │              Supabase (PostgreSQL)              │
                │  sessions · exercises · planned_workouts        │
                │  analyst_recommendations · user_profile         │
                └─────────────────────────────────────────────────┘
```

---

## 📱 Interfaz: Bot de Telegram

El bot es la **única interfaz**. Menú con 3 botones principales:

```
🏋️ Rutina    📊 Progreso    📝 Reporte
```

### Comandos disponibles
```
/start · /menu   → Menú de bienvenida
/rutina          → Selecciona lugar+tiempo → genera rutina
/progreso        → Análisis de evolución (Analista)
/coach           → Chat directo con Valeria
/admin           → Resumen de usuarios (solo admin)
Texto libre      → Valeria: rutina, reporte o conversación
Audio .ogg       → Valeria multimodal: procesa el audio directamente
```

### Flujo de rutina
```
Usuario: 🏋️ Rutina
Bot: ⚡ ¿Dónde entrenas y cuánto tiempo tienes?
     [🌳 Parque 30min] [🌳 Parque 40min] [🌳 Parque 60min]
     [🏠 Casa 30min]   [🏠 Casa 40min]   [🏠 Casa 60min]

Usuario: 🌳 Parque 40min
Bot: [Un momento...]
     🎯 *Objetivo:* 10 Flexiones con rodillas (Pausa 1s)
     ⚠️ *Teniendo en cuenta:* Fascitis plantar
     ¡Venga!
     🏋️ *Colgado en barra* — 3×20s — 90s
     🏋️ *Remo australiano* — 3×8 — 90s
     ...
```

### Flujo de reporte
```
Usuario: hice todo el plan
  — o —
Usuario: hice 3x10 dominadas, 4x8 fondos, me dolió un poco el hombro

Bot: ✅ *Dominadas* — 3×10
     ✅ *Fondos* — 4×8
     [Aviso si hay lesión nueva]
     ¡Bien!
```

---

## ⚡ Optimización: Pre-fetch en el Orquestador

El mayor cuello de botella en sistemas multi-agente es el número de **round-trips al LLM** (cada tool call = 1 llamada + respuesta = ~2-5s extra).

**Solución aplicada:**

```
ANTES (agéntico puro):          AHORA (pre-fetch + agéntico):
─────────────────────────       ──────────────────────────────
LLM → get_user_profile()        Python pre-fetcha en secuencia:
LLM → get_recent_sessions()       profile, sessions, week_freq,
LLM → get_week_frequency()        days_since, recs, planned
LLM → get_days_since_last()     → pasa TODO como contexto al LLM
LLM → get_recommendations()
LLM → get_planned_workout()     LLM solo llama:
LLM → save_planned_workout()      → save_planned_workout ✓
= 7 round-trips (~30s extra)    = 1-2 round-trips
```

Valeria solo tiene **tools de escritura** — los datos llegan pre-cargados.

---

## 🤖 Los Agentes

### 💪 Valeria (`agents/valeria.py`) — Agente Principal
- **Modelo:** `gemini-2.5-flash`
- **Rol:** Agente unificado. Detecta intención del usuario y actúa:
  - **RUTINA** → diseña sesión con historial real, guarda en `planned_workouts`
  - **REPORTE** → parsea lo realizado, guarda en `sessions` + `exercises`
  - **CONVERSACIÓN** → responde preguntas técnicas o motivacionales
- **Tools de escritura:**
  - `save_session(date, exercises, weight, notes, duration)` — registra sesión completada
  - `save_planned_workout(exercises, duration, focus)` — guarda rutina planificada
  - `set_next_milestone(milestone)` — actualiza objetivo cuando se logra
  - `update_conditions(conditions)` — actualiza lesiones/condiciones del perfil
- **Tools de lectura** (solo para preguntas técnicas puntuales):
  - `get_recent_sessions(limit)` · `get_user_profile()`
- **Historial de conversación:** mantiene los últimos 20 mensajes por usuario

### 📊 Analista (`agents/analyst.py`) — Solo con /progreso
- **Modelo:** `gemini-2.5-flash`
- **Activación:** únicamente al pulsar 📊 Progreso
- **Tools:** `get_all_sessions`, `get_exercise_history`, `get_user_profile`, `save_recommendation`
- **Rol:** Analiza toda la evolución histórica y detecta mejoras de marcas personales

### 🧪 Simulador (`agents/simulator.py`)
- Genera sesiones ficticias para poblar la DB en desarrollo
- Uso: `python scripts/run_simulator.py --start 2026-03-01 --days 28`

### 🔄 ARP Evolver (`agents/arp_evolver.py`)
- Meta-agente que propone mejoras a los system prompts analizando patrones
- Uso: `python scripts/run_arp.py`

---

## 🎯 Sistema de Objetivos (Milestones)

El perfil tiene un campo `next_milestone` — el reto actual, concreto y alcanzable en 2-4 semanas.

```
Valeria detecta que el usuario logró el hito actual
    → Felicita en el chat
    → Llama set_next_milestone(siguiente_escalón)
    → El siguiente hito se diseña variado, medible, un escalón (no un salto)

Valeria diseña cada rutina orientada a conseguir el next_milestone actual.
```

Las condiciones físicas (lesiones, limitaciones) también son dinámicas:
el usuario dice "me duele el hombro" → Valeria llama `update_conditions()` → el perfil se actualiza → la siguiente rutina ya lo tiene en cuenta.

---

## 🗄️ Schema de Base de Datos

```
user_profile                sessions              exercises
────────────────            ──────────────        ──────────────
user_email (PK)             id (PK)               id (PK)
name                        user_email            session_id (FK)
age                         planned_workout_id    name
initial_weight              date                  sets
current_weight              weight                reps
injuries                    duration_minutes      seconds
goals                       fatigue_level         weight
home_equipment              general_notes         difficulty
next_milestone              created_at            notes
last_updated

planned_workouts            analyst_recommendations
────────────────            ───────────────────────
id (PK)                     id (PK)
user_email                  user_email
date                        date
focus                       recommendation
total_duration_minutes      created_at
exercises_json
status (PENDING/COMPLETED)
```

---

## 📁 Estructura del Proyecto

```
calistenia/
│
├── telegram_bot.py          # 📱 Bot de Telegram (única interfaz de usuario)
├── main.py                  # 💻 CLI local / Termux Android
├── database.py              # 🗄️ Capa de datos (Supabase SDK)
├── supabase_schema.sql      # SQL para crear las tablas (ejecutar una sola vez)
│
├── agents/
│   ├── __init__.py          # Exporta Orchestrator
│   ├── base.py              # ⭐ Bucle agéntico explícito (leer primero)
│   ├── orchestrator.py      # Pre-fetch de datos + coordinación general
│   ├── valeria.py           # ⭐ Agente Unificado: rutinas + reportes + conversación
│   ├── analyst.py           # Agente Analista: análisis de progreso (/progreso)
│   ├── simulator.py         # Agente: generación de datos de prueba
│   └── arp_evolver.py       # Meta-agente: mejora autónoma de prompts
│
├── scripts/
│   ├── run_simulator.py     # Genera sesiones ficticias para desarrollo
│   └── run_arp.py           # Ejecuta el ARP Evolver
│
├── Dockerfile.telegram      # Contenedor del bot (desplegado en Cloud Run)
├── deploy_telegram.ps1      # ⭐ Deploy a Cloud Run + limpieza auto de revisiones viejas
├── cloudbuild.telegram.yaml # Configuración de Google Cloud Build
│
├── .env                     # 🔒 Variables locales (NO en git — ver abajo)
├── .env.example             # Plantilla de variables de entorno
└── requirements.txt         # Dependencias Python
```

---

## 🚀 Setup y Despliegue

### Requisitos previos
- Python 3.11+
- Cuenta en [Google AI Studio](https://aistudio.google.com/) (API key de Gemini)
- Proyecto en [Supabase](https://supabase.com/) (tier gratuito suficiente)
- Bot de Telegram creado con [@BotFather](https://t.me/botfather)
- `gcloud` CLI configurado (solo para Cloud Run)

### Setup local
```bash
git clone <repo>
cd calistenia

python -m venv venv
source venv/Scripts/activate   # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt

cp .env.example .env
# Editar .env con tus claves (ver tabla abajo)
```

### Crear tablas en Supabase (una sola vez)
1. Ve a tu proyecto en Supabase → **SQL Editor**
2. Pega el contenido de `supabase_schema.sql`
3. Ejecuta → "Success"

### Ejecutar localmente
```bash
python telegram_bot.py   # Bot de Telegram (requiere TELEGRAM_BOT_TOKEN)
python main.py           # CLI sin Telegram
```

### Desplegar en Cloud Run
```powershell
.\deploy_telegram.ps1
```

El script hace automáticamente:
1. `gcloud builds submit` — construye la imagen Docker
2. `gcloud run deploy` — despliega en Cloud Run (`min-instances=1`, `max-instances=1`)
3. Elimina todas las revisiones antiguas para evitar que múltiples instancias hagan polling simultáneo

> ⚠️ **IMPORTANTE:** Cloud Run con `min-instances=1` en modo polling Telegram puede tener conflictos de 30-60 segundos entre la revisión antigua y la nueva durante cada deploy. Esto es normal y se resuelve solo.

---

## 🔑 Variables de Entorno

| Variable | Descripción | Dónde obtenerla |
|---|---|---|
| `GEMINI_API_KEY` | API key de Google Gemini | [aistudio.google.com](https://aistudio.google.com/apikey) |
| `SUPABASE_URL` | URL del proyecto Supabase | Dashboard → Settings → API |
| `SUPABASE_KEY` | Anon/public key de Supabase | Dashboard → Settings → API |
| `TELEGRAM_BOT_TOKEN` | Token del bot | [@BotFather](https://t.me/botfather) → /newbot |
| `TELEGRAM_ALLOWED_CHAT_ID` | Tu chat_id personal (seguridad) | [@RawDataBot](https://t.me/rawdatabot) |
| `CLI_USER_EMAIL` | Email del usuario por defecto | El tuyo |

> **Nunca commitees `.env` — ya está en `.gitignore`**

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología | Por qué |
|---|---|---|
| **LLM** | Google Gemini 2.5 Flash | Soporta audio nativo, function calling, multimodal, rápido |
| **Agent SDK** | `google-genai` | Bucle agéntico manual para control total |
| **Base de datos** | Supabase (PostgreSQL) | Persiste entre reinicios, tier gratuito |
| **Interfaz** | python-telegram-bot 20.x | HTTP polling — funciona en móvil sin WebSocket |
| **Despliegue** | Google Cloud Run | `min-instances=1` mantiene el bot vivo, HTTPS gratis |
| **Contenedor** | Docker | Reproducible en cualquier entorno |

---

## 💡 Decisiones de Diseño

### ¿Por qué un solo agente (Valeria) en vez de varios especializados?

El sistema anterior tenía Receptor + Entrenador + Coach separados. El problema: cada agente necesitaba sus propias tool calls de lectura (round-trips lentos). Con un agente unificado + pre-fetch en el orquestador, el tiempo de respuesta baja drásticamente.

### ¿Por qué orquestación determinista y no un "meta-agente" que decide?

```
ENFOQUE A (meta-agente):          ENFOQUE B (determinista) — el que usamos
─────────────────────────         ──────────────────────────────────────────
Usuario → LLM decide              Usuario → Python decide
  ¿quién responde?                  "Casa 40min" → es rutina → Valeria
Más flexible                      Más rápido, más predecible, más barato
Más caro y lento                  Valeria detecta la intención internamente
```

### ¿Por qué Telegram en lugar de una web app?

Telegram usa HTTP polling — cada petición es independiente. Funciona perfectamente en conexiones móviles inestables. Una web (Streamlit/React) necesita WebSockets persistentes que se caen.

### ¿Por qué `asyncio.to_thread` + Lock?

`_orch.chat()` es síncrono (bloquea). Sin `asyncio.to_thread`, bloquearía el event loop de Telegram y encolaría mensajes. El `asyncio.Lock` por `chat_id` evita que dos mensajes del mismo usuario se procesen en paralelo.

### Comunicación asíncrona entre agentes

El **Analista** no habla directamente con **Valeria**. Escribe recomendaciones en Supabase → el Orquestador las pre-fetcha → Valeria las lee en su contexto la siguiente vez.

```
Analista ──[save_recommendation()]──► Supabase
Valeria  ◄──[pre-fetched en contexto]── Orchestrator
```
