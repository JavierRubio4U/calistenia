"""
run_arp.py - Ejecuta el ARP Evolver

Analiza todos los datos de entrenamiento en Supabase y propone mejoras
concretas a los system prompts de los agentes del sistema.

Requiere que haya sesiones en la DB (corre run_simulator.py primero si no las hay).

Uso:
    python scripts/run_arp.py
"""

import sys
import io
from pathlib import Path
from dotenv import load_dotenv

# Forzar UTF-8 en la salida estándar (Windows cp1252 no soporta todos los caracteres)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from database import get_all_sessions
from agents.arp_evolver import create_arp_evolver_agent


def main():
    print(f"\n{'='*60}")
    print(f"  ARP EVOLVER")
    print(f"{'='*60}\n")

    # Verificar que hay datos antes de lanzar el agente
    sessions = get_all_sessions()
    if not sessions:
        print("⚠️  No hay sesiones en la base de datos.")
        print("   Ejecuta primero: python scripts/run_simulator.py\n")
        return

    print(f"  Sesiones encontradas: {len(sessions)}")
    print(f"  Lanzando análisis...\n")

    agent = create_arp_evolver_agent()

    result = agent.run(
        "Analiza todos los datos de entrenamiento disponibles. "
        "Detecta patrones, identifica problemas y propón mejoras concretas "
        "a los system prompts de los agentes. Genera el informe completo."
    )

    print("\n" + "="*60)
    print("  INFORME ARP EVOLVER")
    print("="*60)
    print(result)
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
