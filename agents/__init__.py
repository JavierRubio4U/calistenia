"""
agents/ - El sistema multi-agente

Aquí viven los 3 agentes especializados + el orquestador:

  Receptor   → Entiende tu reporte oral/escrito y lo guarda estructurado
  Entrenador → Diseña rutinas de 40min adaptadas a tu historial
  Analista   → Evalúa tu progreso y recomienda cambios
  Coach      → Responde dudas sobre técnica y ejercicios
  Orquestador → Coordina quién hace qué y cuándo
"""

from .orchestrator import Orchestrator

__all__ = ["Orchestrator"]
