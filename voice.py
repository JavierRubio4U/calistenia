"""
voice.py - Módulo de entrada por voz (OPCIONAL)

Este módulo detecta automáticamente tu entorno y usa el método
de grabación + transcripción adecuado:

  Android (Termux):
    - Graba con termux-microphone-record (necesitas: pkg install termux-api)
    - Transcribe con OpenAI Whisper API (necesitas: pip install openai)

  Desktop (Windows/Mac/Linux):
    - Graba con SpeechRecognition + PyAudio
    - Transcribe con Google Speech API (gratis, sin API key)

  Si nada está disponible:
    - Usa el teclado de Android con dictado por voz (el icono del micro)
    - O simplemente escribe el texto a mano

NOTA PARA ANDROID: La forma MÁS FÁCIL de usar voz es el teclado de
Google (Gboard). Pulsa el icono del micrófono y dicta. El texto aparece
en la terminal directamente. No necesitas instalar nada extra.
"""

import os
import shutil
import subprocess
import tempfile


def is_termux():
    """Detecta si estamos en Termux (Android)."""
    return shutil.which("termux-microphone-record") is not None


def is_desktop_voice_available():
    """Detecta si SpeechRecognition está disponible (Desktop)."""
    try:
        import speech_recognition  # noqa: F401
        return True
    except ImportError:
        return False


def get_voice_mode():
    """Determina qué modo de voz está disponible.

    Returns:
        "termux" | "desktop" | None
    """
    if is_termux():
        return "termux"
    if is_desktop_voice_available():
        return "desktop"
    return None


def record_termux(max_seconds=120):
    """Graba audio usando Termux API.

    Requiere: pkg install termux-api
    """
    with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as f:
        filepath = f.name

    print("🎤 Grabando... (pulsa Enter cuando termines)")
    try:
        # Inicia grabación en background
        subprocess.Popen([
            "termux-microphone-record",
            "-f", filepath,
            "-l", str(max_seconds),
        ])
        input()  # Espera a que el usuario pulse Enter
        subprocess.run(["termux-microphone-record", "-q"], check=True)
    except KeyboardInterrupt:
        subprocess.run(["termux-microphone-record", "-q"], check=True)

    return filepath


def transcribe_with_whisper_api(filepath):
    """Transcribe audio usando OpenAI Whisper API.

    Requiere: pip install openai + OPENAI_API_KEY en .env
    """
    try:
        from openai import OpenAI
    except ImportError:
        print("Para transcripción con Whisper: pip install openai")
        return None

    try:
        client = OpenAI()
        with open(filepath, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="es"
            )
        return transcript.text
    except Exception as e:
        print(f"Error transcribiendo: {e}")
        return None


def record_desktop():
    """Graba y transcribe usando SpeechRecognition (Desktop).

    Requiere: pip install SpeechRecognition pyaudio
    """
    import speech_recognition as sr
    r = sr.Recognizer()

    try:
        with sr.Microphone() as source:
            print("🎤 Ajustando ruido de fondo...")
            r.adjust_for_ambient_noise(source, duration=1)
            print("🎤 Habla ahora... (máx 2 minutos)")
            audio = r.listen(source, timeout=30, phrase_time_limit=120)
            print("🎤 Procesando audio...")
    except Exception as e:
        print(f"Error con el micrófono: {e}")
        return None

    try:
        return r.recognize_google(audio, language="es-ES")
    except sr.UnknownValueError:
        print("No se pudo entender el audio. Intenta de nuevo.")
        return None
    except sr.RequestError as e:
        print(f"Error con el servicio de reconocimiento: {e}")
        return None


def record_and_transcribe():
    """Función principal: graba y transcribe según el entorno.

    Returns:
        str con el texto transcrito, o None si falla
    """
    mode = get_voice_mode()

    if mode == "termux":
        filepath = record_termux()
        if filepath:
            text = transcribe_with_whisper_api(filepath)
            try:
                os.unlink(filepath)
            except OSError:
                pass
            return text

    elif mode == "desktop":
        return record_desktop()

    print("Voz no disponible. Usa el teclado con dictado o escribe el texto.")
    return None
