"""
base.py - Clase base del Agente (Google Gemini Edition)

Implementa el bucle agéntico manualmente:
  1. LLM recibe el input y decide qué tool llamar
  2. Ejecutamos la tool localmente
  3. Devolvemos el resultado al LLM
  4. Repetimos hasta que el LLM da respuesta final (sin tool calls)
"""

import os
from typing import Any, Callable, List, Optional, Type, Union
from pydantic import BaseModel
from google import genai
from google.genai import types
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

MAX_TOOL_CALLS = 30  # límite de seguridad para evitar loops infinitos


class Agent:
    """
    Agente base usando Google Gemini con bucle agéntico explícito.
    """

    def __init__(
        self,
        name: str,
        system_prompt: str,
        tools: Optional[List[Callable]] = None,
        model_id: str = "gemini-2.5-flash",
        response_schema: Optional[Type[BaseModel]] = None
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.model_id = model_id
        self.tools = tools or []
        self.response_schema = response_schema

        # Mapa nombre_función → callable para ejecutar las tools
        self._tool_map = {fn.__name__: fn for fn in self.tools}

        api_key = os.getenv("GEMINI_API_KEY")
        try:
            import streamlit as st
            api_key = st.secrets.get("GEMINI_API_KEY", api_key)
        except Exception:
            pass
        self.client = genai.Client(api_key=api_key)

    def run(self, user_input: Union[str, List[Union[str, bytes]]], context: str = "") -> Any:
        """
        Ejecuta el agente con bucle agéntico explícito.
        """
        print(f"\n  [{self.name}] Procesando...")

        # Configuración base (sin AFC automático)
        config = types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            tools=self.tools if self.tools else None,
            response_mime_type="application/json" if self.response_schema else None,
            response_schema=self.response_schema if self.response_schema else None,
        )

        # Construir el contenido inicial
        if isinstance(user_input, str):
            initial_parts = [user_input]
        else:
            initial_parts = list(user_input)

        if context:
            initial_parts = [f"CONTEXTO PREVIO:\n{context}\n\n"] + initial_parts

        # Historial de la conversación (multi-turn para tool calls)
        contents: List[types.Content] = [
            types.Content(role="user", parts=[types.Part(text=p) if isinstance(p, str) else p for p in initial_parts])
        ]

        call_count = 0

        try:
            while call_count < MAX_TOOL_CALLS:
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=contents,
                    config=config,
                )

                # Obtener las partes de la respuesta del modelo
                candidate = response.candidates[0]
                content = candidate.content if candidate else None
                model_parts = (content.parts if content else None) or []

                # Separar tool calls de texto
                tool_calls = [p for p in model_parts if p.function_call is not None]
                text_parts = [p for p in model_parts if p.text is not None]

                if not tool_calls:
                    # Sin tool calls → respuesta final
                    if self.response_schema:
                        return response.parsed if hasattr(response, 'parsed') and response.parsed else response.text
                    text = response.text
                    if not text and text_parts:
                        text = "\n".join(p.text for p in text_parts)
                    if not text:
                        finish = candidate.finish_reason if candidate else "UNKNOWN"
                        raise ValueError(f"El modelo no generó respuesta (finish_reason={finish}). Puede que el modelo no esté disponible con esta API key.")
                    return text

                # Hay tool calls: ejecutarlos todos y continuar
                print(f"  [{self.name}] Tool calls: {[p.function_call.name for p in tool_calls]}")

                # Añadir la respuesta del modelo al historial
                contents.append(types.Content(role="model", parts=model_parts))

                # Ejecutar cada tool call y recopilar resultados
                tool_results = []
                for part in tool_calls:
                    fc = part.function_call
                    fn = self._tool_map.get(fc.name)
                    if fn is None:
                        result = {"error": f"Tool '{fc.name}' no encontrada"}
                    else:
                        try:
                            kwargs = dict(fc.args) if fc.args else {}
                            result = fn(**kwargs)
                        except Exception as e:
                            result = {"error": f"{type(e).__name__}: {e}"}

                    tool_results.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=fc.name,
                                response={"result": result},
                            )
                        )
                    )
                    call_count += 1

                # Añadir los resultados de las tools al historial
                contents.append(types.Content(role="user", parts=tool_results))

            return f"[Error] Se alcanzó el límite de {MAX_TOOL_CALLS} tool calls sin respuesta final."

        except Exception as e:
            print(f"  [Error en {self.name}] {str(e)}")
            raise e
