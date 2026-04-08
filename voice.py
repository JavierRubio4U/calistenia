"""
voice.py - Módulo de grabación de audio (Desktop)

Este módulo graba el audio del micrófono directamente a un archivo .wav 
temporal para enviarlo al Agente Receptor (Gemini Multimodal).
"""

import os
import tempfile
import sounddevice as sd
from scipy.io import wavfile
import numpy as np

def get_voice_mode():
    """Para este proyecto didáctico, usamos 'native' si sounddevice está disponible."""
    try:
        sd.query_devices()
        return "native"
    except Exception:
        return None

def record_audio(duration_max=120, fs=16000):
    """
    Graba audio del micrófono y lo guarda en un archivo temporal .wav.
    
    Args:
        duration_max: Duración máxima en segundos.
        fs: Frecuencia de muestreo (16kHz es ideal para voz).
    
    Returns:
        Ruta al archivo temporal .wav.
    """
    print("\n🎤 [SISTEMA] Grabando... (Pulsa Ctrl+C para detener y procesar)")
    
    # Grabamos en un buffer circular o simplemente capturamos
    # Para simplicidad didáctica, capturamos hasta que el usuario corte o pase el tiempo
    try:
        # Grabación asíncrona
        recording = sd.rec(int(duration_max * fs), samplerate=fs, channels=1, dtype='int16')
        
        # Esperamos a que el usuario quiera parar (Enter)
        input("🎤 [SISTEMA] Grabando. Presiona ENTER para finalizar la grabación...")
        sd.stop()
        
        # Recortamos el silencio del final si paramos antes de duration_max
        # (Esto es una simplificación, en producción usaríamos VAD)
        # Por ahora, guardamos lo capturado.
        
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, "calistenia_report.wav")
        
        # Guardar con scipy
        wavfile.write(file_path, fs, recording)
        
        return file_path

    except KeyboardInterrupt:
        sd.stop()
        print("\n🎤 [SISTEMA] Grabación detenida.")
        return None
    except Exception as e:
        print(f"\n❌ [ERROR] Error al grabar: {e}")
        return None
