"""
base.py - Clase base del Agente (Google Gemini Edition)

Implementa el bucle agéntico manualmente:
  1. LLM recibe el input y decide qué tool llamar
  2. Ejecutamos la tool localmente
  3. Devolvemos el resultado al LLM
  4. Repetimos hasta que el LLM da respuesta final (sin tool calls)
"""

import os
import time
import logging
import traceback
import httpx
from typing import Any, Callable, List, Optional, Type, Union
from pydantic import BaseModel
from google import genai
from google.genai import types
from pathlib import Path
from dotenv import load_dotenv
import httpx

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger(__name__)

MAX_TOOL_CALLS = 10  # límite de seguridad para evitar loops infinitos
MAX_RETRIES    = 4   # reintentos ante errores de red transitorios

# Tools cuyo único efecto es escribir en BD (no devuelven datos útiles para razonar).
# Si el modelo emite texto + una de estas, esa primera respuesta YA es la final:
# no llamamos al modelo otra vez (evita el "ya te envié la rutina" confuso).
WRITE_ONLY_TOOLS = {
    "save_session",
    "save_planned_workout",
    "set_next_milestone",
    "update_conditions",
    "save_recommendation",
}


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
        response_schema: Optional[Type[BaseModel]] = None,
        thinking_budget: int = 0,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.model_id = model_id
        self.tools = tools or []
        self.response_schema = response_schema
        self.thinking_budget = thinking_budget

        # Mapa nombre_función → callable para ejecutar las tools
        self._tool_map = {fn.__name__: fn for fn in self.tools}

        api_key = os.getenv("GEMINI_API_KEY")
        try:
            import streamlit as st
            api_key = st.secrets.get("GEMINI_API_KEY", api_key)
        except Exception:
            pass
        self.client = genai.Client(api_key=api_key)

    def run(
        self,
        user_input: Union[str, List[Union[str, bytes]]],
        context: str = "",
        history: Optional[List] = None,
        return_history: bool = False,
    ) -> Any:
        """
        Ejecuta el agente con bucle agéntico explícito.

        Args:
            user_input: Texto o lista de partes multimodal del usuario.
            context: Contexto adicional prepend al mensaje.
            history: Lista de types.Content previos (conversación anterior).
            return_history: Si True, devuelve tupla (text, contents) con el historial completo.
        """
        logger.info(f"[{self.name}] === RUN START === model={self.model_id} thinking_budget={self.thinking_budget} tools={len(self.tools)}")
        print(f"\n  [{self.name}] Procesando...")

        # Configuración base — AFC desactivado para bucle manual, thinking mínimo para velocidad
        config = types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            tools=self.tools if self.tools else None,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            thinking_config=None,
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
        # Si viene historial previo, usarlo como base antes del mensaje actual
        contents: List[types.Content] = list(history) if history else []
        contents.append(
            types.Content(role="user", parts=[types.Part(text=p) if isinstance(p, str) else p for p in initial_parts])
        )

        call_count = 0
        last_emitted_text = ""  # último texto emitido junto a un tool call — fallback si tras la tool el modelo cierra con STOP vacío

        try:
            while call_count < MAX_TOOL_CALLS:
                # Reintentos ante errores de red transitorios (red inestable desde Cloud Run)
                response = None
                last_exc = None
                for attempt in range(MAX_RETRIES):
                    t_call = time.time()
                    try:
                        logger.info(f"[{self.name}] generate_content attempt={attempt+1}/{MAX_RETRIES} contents_len={len(contents)}")
                        response = self.client.models.generate_content(
                            model=self.model_id,
                            contents=contents,
                            config=config,
                        )
                        logger.info(f"[{self.name}] generate_content OK in {time.time()-t_call:.2f}s on attempt {attempt+1}")
                        break  # éxito
                    except Exception as e:
                        last_exc = e
                        err_str = type(e).__name__.lower() + str(e).lower()
                        is_retryable = any(w in err_str for w in [
                            'timeout', 'remote', 'protocol', 'connection',
                            'write', 'network', 'unavailable', 'reset', '503', '502',
                        ])
                        logger.error(
                            f"[{self.name}] generate_content FAIL attempt={attempt+1}/{MAX_RETRIES} "
                            f"after {time.time()-t_call:.2f}s retryable={is_retryable} "
                            f"type={type(e).__name__} msg={str(e)[:300]}\n{traceback.format_exc()}"
                        )
                        if is_retryable and attempt < MAX_RETRIES - 1:
                            # Recrear el cliente para soltar cualquier conexión HTTP/2 rota
                            try:
                                self._recreate_client()
                                logger.info(f"[{self.name}] cliente recreado tras error retryable")
                            except Exception as rec_e:
                                logger.error(f"[{self.name}] fallo al recrear cliente: {rec_e}")
                            backoff = 2 ** attempt  # 1, 2, 4
                            time.sleep(backoff)
                        else:
                            raise
                if response is None:
                    # Defensivo: nunca debería pasar
                    raise last_exc if last_exc else RuntimeError("generate_content devolvió None sin excepción")

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
                        result = response.parsed if hasattr(response, 'parsed') and response.parsed else response.text
                        if return_history:
                            return result, contents
                        return result
                    text = response.text
                    if not text and text_parts:
                        text = "\n".join(p.text for p in text_parts)
                    if not text:
                        # El modelo cerró sin texto. Si ya emitió texto en un turno previo (junto al tool call), úsalo.
                        finish = candidate.finish_reason if candidate else "UNKNOWN"
                        if last_emitted_text:
                            logger.warning(
                                f"[{self.name}] respuesta final vacía (finish={finish}) — usando texto emitido previamente junto al tool call ({len(last_emitted_text)} chars)"
                            )
                            text = last_emitted_text
                        else:
                            raise ValueError(f"El modelo no generó respuesta (finish_reason={finish}). Puede que el modelo no esté disponible con esta API key.")
                    if return_history:
                        # Añadir respuesta final del modelo al historial antes de devolver
                        if content:
                            contents.append(types.Content(role="model", parts=model_parts))
                        return text, contents
                    return text

                # Hay tool calls: ejecutarlos todos y continuar.
                # Si el modelo ya emitió texto junto al tool call, guárdalo como fallback final.
                if text_parts:
                    emitted = "\n".join(p.text for p in text_parts if p.text)
                    if emitted.strip():
                        last_emitted_text = emitted
                        logger.info(f"[{self.name}] texto emitido junto al tool call: {len(emitted)} chars")

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

                # Shortcut: si TODOS los tool calls eran write-only Y el modelo ya emitió texto
                # substantivo en este turno, esa respuesta YA es la final — no llamamos al modelo otra vez.
                all_write_only = all(p.function_call.name in WRITE_ONLY_TOOLS for p in tool_calls)
                if all_write_only and last_emitted_text and len(last_emitted_text.strip()) > 100:
                    logger.info(
                        f"[{self.name}] shortcut write-only: devolviendo texto previo ({len(last_emitted_text)} chars) sin segunda llamada al modelo"
                    )
                    if return_history:
                        return last_emitted_text, contents
                    return last_emitted_text

            error_msg = f"[Error] Se alcanzó el límite de {MAX_TOOL_CALLS} tool calls sin respuesta final."
            if return_history:
                return error_msg, contents
            return error_msg

        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"[{self.name}] === RUN FAIL === type={type(e).__name__} msg={str(e)[:500]}\n{tb}")
            print(f"  [Error en {self.name}] {type(e).__name__}: {str(e)}\n{tb}")
            raise e

    def _recreate_client(self):
        """Recrea el cliente Gemini para soltar conexiones HTTP/2 rotas tras un error de red."""
        api_key = os.getenv("GEMINI_API_KEY")
        try:
            import streamlit as st
            api_key = st.secrets.get("GEMINI_API_KEY", api_key)
        except Exception:
            pass
        self.client = genai.Client(api_key=api_key)
