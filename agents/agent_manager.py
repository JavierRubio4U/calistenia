"""
agent_manager.py - Tools para que el ARP Evolver lea y reescriba prompts de agentes

El ARP Evolver usa estas tools para modificar directamente los system prompts
de los agentes basándose en el análisis de datos reales.
"""

import re
from pathlib import Path

AGENTS_DIR = Path(__file__).parent

AGENT_FILES = {
    "receptor": AGENTS_DIR / "receptor.py",
    "entrenador": AGENTS_DIR / "trainer.py",
    "analista": AGENTS_DIR / "analyst.py",
    "coach": AGENTS_DIR / "coach.py",
}


def read_agent_prompt(agent_name: str) -> dict:
    """Lee el system prompt actual de un agente.

    Args:
        agent_name: Nombre del agente. Valores válidos: receptor, entrenador, analista, coach.
    """
    path = AGENT_FILES.get(agent_name.lower())
    if not path or not path.exists():
        return {"error": f"Agente '{agent_name}' no encontrado. Válidos: {list(AGENT_FILES.keys())}"}

    content = path.read_text(encoding="utf-8")

    # Extraer el SYSTEM_PROMPT o system_prompt de la variable
    match = re.search(r'SYSTEM_PROMPT\s*=\s*"""(.*?)"""', content, re.DOTALL)
    if not match:
        match = re.search(r'system_prompt\s*=\s*f?"""(.*?)"""', content, re.DOTALL)
    if not match:
        return {"error": f"No se encontró SYSTEM_PROMPT en {path.name}"}

    return {
        "agent": agent_name,
        "file": path.name,
        "current_prompt": match.group(1).strip()
    }


def update_agent_prompt(agent_name: str, new_prompt: str, reason: str) -> dict:
    """Reescribe el system prompt de un agente con una versión mejorada.

    Args:
        agent_name: Nombre del agente a actualizar: receptor, entrenador, analista, coach.
        new_prompt: El nuevo system prompt completo que reemplazará al actual.
        reason: Justificación del cambio basada en los datos analizados.
    """
    path = AGENT_FILES.get(agent_name.lower())
    if not path or not path.exists():
        return {"error": f"Agente '{agent_name}' no encontrado."}

    content = path.read_text(encoding="utf-8")

    # Reemplazar SYSTEM_PROMPT = """..."""
    pattern = r'(SYSTEM_PROMPT\s*=\s*""").*?(""")'
    new_content = re.sub(pattern, rf'\g<1>{new_prompt}\g<2>', content, flags=re.DOTALL)

    if new_content == content:
        # Intentar con system_prompt minúscula
        pattern = r'(system_prompt\s*=\s*f?""").*?(""")'
        new_content = re.sub(pattern, rf'\g<1>{new_prompt}\g<2>', content, flags=re.DOTALL)

    if new_content == content:
        return {"error": f"No se pudo reemplazar el prompt en {path.name}"}

    path.write_text(new_content, encoding="utf-8")

    print(f"[ARP] Prompt de '{agent_name}' actualizado. Motivo: {reason}", flush=True)
    return {
        "status": "ok",
        "agent": agent_name,
        "file": path.name,
        "reason": reason,
        "chars_new_prompt": len(new_prompt)
    }
