"""
base.py - Clase base del Agente (EL CORAZÓN DEL SISTEMA)

╔══════════════════════════════════════════════════════════════════╗
║  CONCEPTO CLAVE: EL BUCLE AGÉNTICO (Agentic Loop)              ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Un agente NO es solo una llamada a un LLM.                     ║
║  Un agente es un LLM + herramientas + un bucle de ejecución.   ║
║                                                                  ║
║  Flujo del bucle agéntico:                                      ║
║                                                                  ║
║  ┌──────────────────────────────────────────────┐               ║
║  │  1. Envías mensaje al LLM (con tools)        │               ║
║  │  2. El LLM responde:                         │               ║
║  │     ├─ "Quiero usar esta tool" → EJECUTAS    │               ║
║  │     │   la tool y le devuelves el resultado   │               ║
║  │     │   → vuelve al paso 2                    │               ║
║  │     └─ "Ya terminé, aquí está mi respuesta"   │               ║
║  │         → FIN del bucle                       │               ║
║  └──────────────────────────────────────────────┘               ║
║                                                                  ║
║  La MAGIA está en que el LLM DECIDE:                            ║
║  - Qué herramientas usar (o ninguna)                            ║
║  - En qué orden                                                 ║
║  - Cuántas veces                                                ║
║  - Con qué parámetros                                           ║
║                                                                  ║
║  Eso lo hace "agéntico": tiene AUTONOMÍA para actuar.           ║
╚══════════════════════════════════════════════════════════════════╝

¿POR QUÉ UNA CLASE BASE?
Porque los 3 agentes (Receptor, Entrenador, Analista) comparten
el mismo patrón: system prompt + tools + bucle. Solo cambian:
  - El system prompt (su "personalidad" y conocimiento)
  - Las tools disponibles (qué puede hacer)
  - El modelo (haiku para tareas simples, sonnet para las complejas)
"""

import json
import anthropic


class Agent:
    """
    Clase base para todos los agentes del sistema.

    Cada agente necesita:
      - name: nombre para logs/debug
      - system_prompt: instrucciones especializadas (quién es, qué hace)
      - tools: lista de herramientas que puede usar (formato Anthropic)
      - tool_handlers: diccionario {nombre_tool: función_python}
      - model: qué modelo de Claude usar
    """

    def __init__(self, name, system_prompt, tools, tool_handlers, model="claude-sonnet-4-6"):
        self.name = name
        self.client = anthropic.Anthropic()  # Lee ANTHROPIC_API_KEY del entorno
        self.system_prompt = system_prompt
        self.tools = tools
        self.tool_handlers = tool_handlers
        self.model = model

    def run(self, user_message, context=""):
        """
        Ejecuta el bucle agéntico.

        Args:
            user_message: lo que el usuario dice o la tarea a realizar
            context: contexto adicional (ej: recomendaciones del Analista)

        Returns:
            str: la respuesta final del agente (texto)

        ESTE ES EL BUCLE AGÉNTICO EN ACCIÓN:
        ────────────────────────────────────
        Observa cómo el while True implementa el bucle.
        El agente sigue ejecutando tools hasta que decide
        que ya tiene suficiente información para responder.
        """
        # Preparar el mensaje inicial
        full_message = f"{context}\n\n{user_message}" if context else user_message
        messages = [{"role": "user", "content": full_message}]

        print(f"\n  [{self.name}] Pensando...")

        # ═══ INICIO DEL BUCLE AGÉNTICO ═══
        while True:
            # Paso 1: Llamar al LLM
            # Le pasamos el system prompt (quién es), los tools (qué puede hacer)
            # y los mensajes (la conversación hasta ahora)
            kwargs = {
                "model": self.model,
                "max_tokens": 4096,
                "system": self.system_prompt,
                "messages": messages,
            }
            if self.tools:
                kwargs["tools"] = self.tools

            response = self.client.messages.create(**kwargs)

            # Guardar la respuesta del asistente en el historial
            messages.append({"role": "assistant", "content": response.content})

            # Paso 2: ¿El LLM quiere usar tools?
            if response.stop_reason == "tool_use":
                # SÍ → ejecutar cada tool que pidió
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        print(f"  [{self.name}] Herramienta: {block.name}")

                        # Buscar el handler Python para esta tool
                        handler = self.tool_handlers.get(block.name)
                        if handler:
                            try:
                                # Ejecutar la función con los args que eligió el LLM
                                result = handler(**block.input)
                            except Exception as e:
                                result = {"error": str(e)}
                        else:
                            result = {"error": f"Tool '{block.name}' no registrada"}

                        # Devolver el resultado al LLM
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(
                                result, ensure_ascii=False, default=str
                            )
                        })

                # Añadir resultados de tools como mensaje del "usuario"
                # (así es como funciona la API: los resultados van en role=user)
                messages.append({"role": "user", "content": tool_results})

                # → Volver al paso 1 (el LLM procesa los resultados)
            else:
                # NO → el agente ha terminado, extraer texto
                text_parts = [
                    block.text
                    for block in response.content
                    if hasattr(block, "text")
                ]
                return "\n".join(text_parts)
        # ═══ FIN DEL BUCLE AGÉNTICO ═══
