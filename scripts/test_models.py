"""
test_models.py - Lista los modelos disponibles con la API key y prueba los más relevantes.

Uso:
    python scripts/test_models.py
    python scripts/test_models.py --api-key TU_KEY
"""

import argparse
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path
from dotenv import load_dotenv
import os

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from google import genai
from google.genai import types


def test_model(client, model_id: str, with_tools: bool = False) -> str:
    """Prueba un modelo y devuelve el resultado."""
    try:
        if with_tools:
            def dummy_tool() -> dict:
                """Devuelve datos de prueba."""
                return {"status": "ok", "value": 42}

            r = client.models.generate_content(
                model=model_id,
                contents=["Llama a dummy_tool y dime el valor que devuelve."],
                config=types.GenerateContentConfig(
                    system_instruction="Usa la herramienta disponible para responder.",
                    tools=[dummy_tool],
                )
            )
        else:
            r = client.models.generate_content(
                model=model_id,
                contents=["Di 'OK' en una sola palabra."],
            )

        c = r.candidates[0] if r.candidates else None
        if not c or not c.content or not c.content.parts:
            return f"⚠️  Sin contenido (finish_reason={c.finish_reason if c else 'N/A'})"
        return f"✅  '{r.text.strip()}'"
    except Exception as e:
        return f"❌  {e}"


def list_models(client):
    """Lista todos los modelos disponibles."""
    try:
        models = list(client.models.list())
        return [m.name for m in models if "generateContent" in (m.supported_actions or [])]
    except Exception as e:
        print(f"⚠️  No se pudo listar modelos: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description="Test de modelos Gemini")
    parser.add_argument("--api-key", default=None, help="API key (por defecto usa .env)")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ No se encontró GEMINI_API_KEY")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  TEST DE MODELOS GEMINI")
    print(f"  API Key: ...{api_key[-8:]}")
    print(f"{'='*60}\n")

    client = genai.Client(api_key=api_key)

    # Modelos a probar (texto + tools)
    PRIORITY_MODELS = [
        # Gemini 3.x
        "models/gemini-3.1-pro-preview",
        "models/gemini-3.1-pro-preview-customtools",
        "models/gemini-3-pro-preview",
        "models/gemini-3.1-flash-lite-preview",
        "models/gemini-flash-latest",
        "models/gemini-pro-latest",
        # Gemini 2.5
        "gemini-2.5-pro",
        "gemini-2.5-flash",
    ]

    print("── Modelos disponibles (texto + tools) ──────────────────")
    for model_id in PRIORITY_MODELS:
        result_text = test_model(client, model_id, with_tools=False)
        result_tools = test_model(client, model_id, with_tools=True)
        print(f"  {model_id:<45} texto:{result_text}  tools:{result_tools}")

    print("\n── Todos los modelos disponibles con esta key ───────────")
    available = list_models(client)
    if available:
        for m in sorted(available):
            if not any(p in m for p in PRIORITY_MODELS):
                print(f"  {m}")
    else:
        print("  (no se pudo obtener la lista)")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
