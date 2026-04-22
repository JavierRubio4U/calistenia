"""
telegram_bot.py - Bot de Telegram para Calistenia Coach (Valeria)

Comandos:
  /start /menu  → menú principal
  /rutina       → rutina del día
  /progreso     → análisis de evolución
  /coach        → pregunta técnica
  /admin        → resumen de usuarios (solo admin)
  Texto/voz libre → Receptor (reporte de sesión)
"""

import os
import re
import random
import logging
import tempfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters,
)

from database import init_db, get_user_profile, get_all_users_admin
from agents import Orchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _start_healthcheck():
    import threading
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class _H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        def log_message(self, *a): pass

    port = int(os.getenv("PORT", "8080"))
    HTTPServer(("0.0.0.0", port), _H).serve_forever.__func__
    srv = HTTPServer(("0.0.0.0", port), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    logger.info(f"Healthcheck en :{port}")


TOKEN          = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_CHAT_ID = int(os.getenv("TELEGRAM_ALLOWED_CHAT_ID", "0"))
ADMIN_EMAIL    = os.getenv("ALLOWED_EMAIL", "carthagonova@gmail.com")
USER_EMAIL     = os.getenv("CLI_USER_EMAIL", "carthagonova@gmail.com")

init_db()
_profile = get_user_profile(user_email=USER_EMAIL)
_orch    = Orchestrator(user_email=USER_EMAIL, profile=_profile)
_state: dict = {}  # chat_id → None | "coach" | "esperando_lugar_tiempo" | {"step":"esperando_estado","lugar":str,"minutos":int}


def _allowed(update: Update) -> bool:
    return update.effective_chat.id == ALLOWED_CHAT_ID


def _keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🏋️ Rutina"),        KeyboardButton("📊 Progreso")],
         [KeyboardButton("💬 Coach"),          KeyboardButton("📝 Reportar sesión")]],
        resize_keyboard=True,
    )


_MSGS_RUTINA = [
    "⚡ Dame un momento, voy a ver qué toca hoy...",
    "🏋️ Mirando tu historial y preparando algo...",
    "📋 Un segundo, revisando lo que has hecho últimamente...",
    "💪 Voy a ello, dame un momento...",
    "🧠 Analizando y armando tu sesión de hoy...",
    "⏳ Un momento, te lo preparo...",
]

_MSGS_PROGRESO = [
    "🔍 Revisando tus datos... dame un momento 📈",
    "📊 Analizando tu evolución...",
    "⏳ Un segundo, voy a ver cómo llevas todo...",
    "💡 Mirando tus sesiones y sacando conclusiones...",
]

_MSGS_COACH = [
    "🤔 Un momento...",
    "💭 Déjame pensar...",
    "⏳ Dame un segundo...",
    "🧐 En ello...",
]

_MSGS_SESION = [
    "📥 Anotando...",
    "✍️ Registrando tu sesión...",
    "📋 Un momento...",
    "💾 Guardando lo que me cuentas...",
    "📝 Procesando...",
]


def _fix_bold(text: str) -> str:
    """Convierte **texto** → *texto* para Telegram."""
    return re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)


async def _send(update: Update, text: str):
    text = _fix_bold(text)
    for i, chunk in enumerate([text[i:i+4000] for i in range(0, len(text), 4000)]):
        kb = _keyboard() if i == (len(text) - 1) // 4000 else None
        await update.message.reply_text(chunk, parse_mode="Markdown", reply_markup=kb)


# ─── /start /menu ────────────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _allowed(update): return
    name = _profile.get("name", "!")
    await _send(update,
        f"💪 *¡Hola {name}! Soy Valeria* 😊\n\n"
        "🏋️ *Rutina* — te preparo el entreno de hoy\n"
        "📊 *Progreso* — vemos cómo vas\n"
        "💬 *Coach* — pregúntame lo que quieras\n"
        "📝 *Reportar sesión* — cuéntame cómo fue")


# ─── /rutina ─────────────────────────────────────────────────────────────────
async def cmd_rutina(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _allowed(update): return
    _state[update.effective_chat.id] = "esperando_lugar_tiempo"
    await update.message.reply_text(
        "⚡ ¿Dónde entrenas y cuánto tiempo tienes?",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("🌳 Parque 30min"), KeyboardButton("🌳 Parque 40min"), KeyboardButton("🌳 Parque 60min")],
             [KeyboardButton("🏠 Casa 30min"),   KeyboardButton("🏠 Casa 40min"),   KeyboardButton("🏠 Casa 60min")]],
            resize_keyboard=True, one_time_keyboard=True))


# ─── /progreso ───────────────────────────────────────────────────────────────
async def cmd_progreso(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _allowed(update): return
    _state[update.effective_chat.id] = None
    await update.message.reply_text(random.choice(_MSGS_PROGRESO))
    try:
        await _send(update, _orch.analyze_progress())
    except Exception as e:
        await _send(update, f"❌ Error: {e}")


# ─── /coach ──────────────────────────────────────────────────────────────────
async def cmd_coach(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _allowed(update): return
    pregunta = " ".join(ctx.args) if ctx.args else ""
    if pregunta:
        await update.message.reply_text(random.choice(_MSGS_COACH))
        try:
            await _send(update, _orch.ask_coach(pregunta))
        except Exception as e:
            await _send(update, f"❌ Error: {e}")
    else:
        _state[update.effective_chat.id] = "coach"
        await update.message.reply_text("💬 ¡Dime! Escribe o manda un audio 🎙️",
                                        reply_markup=_keyboard())


# ─── /admin ──────────────────────────────────────────────────────────────────
async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _allowed(update): return
    try:
        users = get_all_users_admin()
        if not users:
            await _send(update, "No hay usuarios registrados.")
            return
        lines = [f"👥 *{len(users)} usuarios registrados*\n"]
        for u in users:
            last = u.get("last_session") or "Nunca"
            lines.append(
                f"• *{u.get('name','?')}* — {u.get('session_count',0)} sesiones — última: {last}"
            )
        await _send(update, "\n".join(lines))
    except Exception as e:
        await _send(update, f"❌ Error: {e}")


# ─── Texto libre ─────────────────────────────────────────────────────────────
async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _allowed(update): return
    chat_id = update.effective_chat.id
    text    = update.message.text.strip()
    state   = _state.get(chat_id)

    # Botones menú
    if text == "🏋️ Rutina":        await cmd_rutina(update, ctx);   return
    if text == "📊 Progreso":       await cmd_progreso(update, ctx); return
    if text == "💬 Coach":          await cmd_coach(update, ctx);    return
    if text == "📝 Reportar sesión":
        _state[chat_id] = None
        await update.message.reply_text(
            "📝 Cuéntame cómo fue — texto o audio 🎙️", reply_markup=_keyboard())
        return

    # Saludos → menú
    if text.lower() in {"hola","hello","hi","buenas","ey","hey","menú","menu","ayuda","help"}:
        await cmd_start(update, ctx)
        return

    # Paso 1: Selección de lugar + tiempo
    if state == "esperando_lugar_tiempo":
        tl = text.lower()
        lugar   = "Parque / Calistenia" if "parque" in tl else "Casa"
        minutos = 30 if "30" in tl else (60 if "60" in tl else 40)
        _state[chat_id] = {"step": "esperando_estado", "lugar": lugar, "minutos": minutos}
        await update.message.reply_text(
            "¿Cómo estás hoy?",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("😓 Mal"), KeyboardButton("😐 Normal"), KeyboardButton("💪 Bien")]],
                resize_keyboard=True, one_time_keyboard=True))
        return

    # Paso 2: Estado de forma → generar rutina
    if isinstance(state, dict) and state.get("step") == "esperando_estado":
        tl     = text.lower()
        estado = "Mal" if "mal" in tl else ("Bien" if "bien" in tl else "Normal")
        lugar  = state["lugar"]
        minutos = state["minutos"]
        _state[chat_id] = None
        await update.message.reply_text(random.choice(_MSGS_RUTINA))
        ctx_str = f"LUGAR HOY: {lugar}. TIEMPO DISPONIBLE: {minutos} min. ESTADO HOY: {estado}."
        try:
            await _send(update, _orch.get_workout_plan(context=ctx_str))
        except Exception as e:
            await _send(update, f"❌ Error: {e}")
        return

    # Modo coach
    if state == "coach":
        _state[chat_id] = None
        await update.message.reply_text(random.choice(_MSGS_COACH))
        try:
            await _send(update, _orch.ask_coach(text))
        except Exception as e:
            await _send(update, f"❌ Error: {e}")
        return

    # Reporte de sesión (por defecto)
    _state[chat_id] = None
    await update.message.reply_text(random.choice(_MSGS_SESION))
    try:
        receptor_resp, _ = _orch.report_session(text)
        await _send(update, receptor_resp)
    except Exception as e:
        await _send(update, f"❌ Error: {e}")


# ─── Voz ─────────────────────────────────────────────────────────────────────
async def handle_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _allowed(update): return
    chat_id = update.effective_chat.id
    state   = _state.get(chat_id)
    await update.message.reply_text(random.choice(_MSGS_SESION))
    try:
        vf = await update.message.voice.get_file()
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name
        await vf.download_to_drive(tmp_path)
        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()
        os.unlink(tmp_path)

        from google.genai import types as gtypes
        multimodal = [
            gtypes.Part.from_bytes(data=audio_bytes, mime_type="audio/ogg"),
            "Este es mi mensaje de voz."
        ]
        if state == "coach":
            _state[chat_id] = None
            await _send(update, _orch.ask_coach(multimodal))
        else:
            receptor_resp, _ = _orch.report_session(multimodal)
            await _send(update, receptor_resp)
    except Exception as e:
        await _send(update, f"❌ Error procesando audio: {e}")


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    _start_healthcheck()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("menu",     cmd_start))
    app.add_handler(CommandHandler("rutina",   cmd_rutina))
    app.add_handler(CommandHandler("progreso", cmd_progreso))
    app.add_handler(CommandHandler("coach",    cmd_coach))
    app.add_handler(CommandHandler("admin",    cmd_admin))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    logger.info("Valeria arrancada en modo polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
