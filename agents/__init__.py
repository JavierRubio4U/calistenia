"""
agents/ - El sistema multi-agente

  Valeria    → Agente unificado: rutinas, reportes y preguntas (Flash)
  Analista   → Evalúa el progreso bajo demanda (Pro, solo /progreso)
  Orquestador → Coordina quién hace qué y cuándo

  (receptor.py, trainer.py, coach.py mantenidos como referencia)
"""

from .orchestrator import Orchestrator
from .valeria import create_valeria_agent
from .simulator import create_simulator_agent
from .arp_evolver import create_arp_evolver_agent

__all__ = ["Orchestrator", "create_valeria_agent", "create_simulator_agent", "create_arp_evolver_agent"]
