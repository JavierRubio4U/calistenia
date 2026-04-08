"""
base.py - Clase base del Agente (Google Gemini Edition)

Este archivo define la estructura de "Agente crudo":
LLM + Tools + Estructura de Salida (Pydantic).
"""

import os
from typing import Any, Callable, Dict, List, Optional, Type, Union
from pydantic import BaseModel
from google import genai
from google.genai import types
from pathlib import Path
from dotenv import load_dotenv

# Ruta absoluta al .env del proyecto (2 niveles arriba: agents/ → proyecto/)
load_dotenv(Path(__file__).parent.parent / ".env")

class Agent:
    """
    Agente base usando Google Gemini.
    
    Características:
    - Bucle agéntico automático para uso de herramientas.
    - Soporte nativo para esquemas de respuesta Pydantic.
    - Configuración simplificada.
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
        
        # Cliente oficial de Google
        # Prioridad: Streamlit Secrets (cloud) → .env (local)
        api_key = os.getenv("GEMINI_API_KEY")
        try:
            import streamlit as st
            api_key = st.secrets.get("GEMINI_API_KEY", api_key)
        except Exception:
            pass
        self.client = genai.Client(api_key=api_key)

    def run(self, user_input: Union[str, List[Union[str, bytes]]], context: str = "") -> Any:
        """
        Ejecuta el agente. user_input puede ser texto o una lista con audio (bytes).
        """
        print(f"\n  [{self.name}] Procesando...")

        # 1. Configuración de la petición
        config = types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            tools=self.tools if self.tools else None,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False) if self.tools else None,
            response_mime_type="application/json" if self.response_schema else "text/plain",
            response_schema=self.response_schema if self.response_schema else None,
        )

        # 2. Preparar el contenido (incluyendo contexto si existe)
        full_input = []
        if context:
            full_input.append(f"CONTEXTO PREVIO:\n{context}\n\n")
        
        if isinstance(user_input, str):
            full_input.append(user_input)
        else:
            full_input.extend(user_input)

        # 3. Llamada al modelo (Gemini maneja el bucle de tools automáticamente si se configura)
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=full_input,
                config=config
            )

            # 4. Retornar resultado
            if self.response_schema:
                # Si pedimos JSON/Pydantic, Gemini devuelve el objeto parseado o el string JSON
                return response.parsed if hasattr(response, 'parsed') and response.parsed else response.text
            
            return response.text

        except Exception as e:
            print(f"  [Error en {self.name}] {str(e)}")
            raise e
