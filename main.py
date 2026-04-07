"""
main.py - Punto de entrada de Calistenia Coach

╔══════════════════════════════════════════════════════════════════╗
║  ARQUITECTURA DEL PROYECTO                                      ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  main.py (este archivo)                                         ║
║    └── Interfaz CLI → el usuario elige qué hacer                ║
║                                                                  ║
║  agents/orchestrator.py                                         ║
║    └── Coordina los agentes → decide quién actúa               ║
║                                                                  ║
║  agents/receptor.py     (Agente 1 - Haiku)                     ║
║    └── Parsea reportes → guarda datos en DB                     ║
║                                                                  ║
║  agents/trainer.py      (Agente 2 - Sonnet)                    ║
║    └── Diseña rutinas → consulta historial + recomendaciones    ║
║                                                                  ║
║  agents/analyst.py      (Agente 3 - Sonnet)                    ║
║    └── Analiza progreso → genera recomendaciones                ║
║                                                                  ║
║  database.py                                                     ║
║    └── SQLite: sesiones, ejercicios, planes, recomendaciones    ║
║                                                                  ║
║  voice.py                                                        ║
║    └── Grabación + transcripción (opcional)                     ║
║                                                                  ║
║  FLUJO DE DATOS:                                                ║
║  Usuario → Receptor → DB ← Entrenador ← Analista               ║
║                                                                  ║
║  Los agentes se comunican a través de la DB, no directamente.   ║
╚══════════════════════════════════════════════════════════════════╝

USO:
    python main.py
"""

import sys

# Cargar variables de entorno (.env)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Sin dotenv, usa variables del sistema

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from database import init_db
from agents import Orchestrator
from voice import get_voice_mode, record_and_transcribe

console = Console()


def show_header():
    """Muestra la cabecera de la app."""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]CALISTENIA COACH[/bold cyan]\n"
        "[dim]Entrenamiento adaptativo con agentes de IA[/dim]",
        border_style="cyan"
    ))


def show_menu(voice_available):
    """Muestra el menú de opciones."""
    console.print()
    console.print("  [bold][1][/bold] Pedir rutina de hoy")
    console.print("  [bold][2][/bold] Reportar sesion (texto)")
    if voice_available:
        console.print("  [bold][3][/bold] Reportar sesion (voz)")
    console.print("  [bold][4][/bold] Ver mi progreso")
    console.print("  [bold][0][/bold] Salir")
    console.print()


def handle_workout_plan(orchestrator):
    """Opción 1: Pedir rutina de hoy."""
    console.print("\n[bold green]Generando tu rutina...[/bold green]\n")
    try:
        plan = orchestrator.get_workout_plan()
        console.print(Markdown(plan))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def handle_text_report(orchestrator):
    """Opción 2: Reportar sesión por texto."""
    console.print(
        "\n[dim]Escribe cómo fue tu sesión. Ejemplo:[/dim]\n"
        '[dim]"Hoy 40min, australianas 3x10 bien, flexiones 3x8 las '
        'últimas al fallo, sentadillas búlgaras 3x12. Peso 76kg, algo '
        'cansado de ayer"[/dim]\n'
    )
    report = console.input("[bold]Tu reporte: [/bold]")
    if not report.strip():
        console.print("[yellow]Reporte vacío, cancelado.[/yellow]")
        return

    try:
        receptor_resp, analyst_resp = orchestrator.report_session(report)
        console.print(Markdown(receptor_resp))

        if analyst_resp:
            console.print("\n[bold cyan]--- Analisis de Progreso ---[/bold cyan]\n")
            console.print(Markdown(analyst_resp))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def handle_voice_report(orchestrator):
    """Opción 3: Reportar sesión por voz."""
    text = record_and_transcribe()
    if not text:
        console.print("[yellow]No se pudo obtener texto. Usa la opción de texto.[/yellow]")
        return

    console.print(f'\n[bold]Transcripcion:[/bold] "{text}"')
    confirm = console.input("Correcto? [S/n]: ").strip().lower()

    if confirm not in ("", "s", "si", "sí", "y", "yes"):
        console.print("Cancelado. Intenta de nuevo.")
        return

    try:
        receptor_resp, analyst_resp = orchestrator.report_session(text)
        console.print(Markdown(receptor_resp))

        if analyst_resp:
            console.print("\n[bold cyan]--- Analisis de Progreso ---[/bold cyan]\n")
            console.print(Markdown(analyst_resp))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def handle_progress(orchestrator):
    """Opción 4: Ver progreso."""
    console.print("\n[bold green]Analizando tu progreso...[/bold green]\n")
    try:
        progress = orchestrator.analyze_progress()
        console.print(Markdown(progress))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def main():
    """Bucle principal de la aplicación."""
    # 1. Inicializar base de datos
    init_db()

    # 2. Detectar si hay soporte de voz
    voice_mode = get_voice_mode()
    if voice_mode:
        console.print(f"[green]Voz disponible ({voice_mode})[/green]")
    else:
        console.print(
            "[dim]Voz no disponible. En Android puedes usar el teclado "
            "de dictado como alternativa.[/dim]"
        )

    # 3. Crear el orquestador (que crea los 3 agentes)
    orchestrator = Orchestrator()

    # 4. Bucle del menú
    show_header()
    while True:
        show_menu(voice_available=voice_mode is not None)

        try:
            choice = console.input("[bold]Opcion: [/bold]").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if choice == "1":
            handle_workout_plan(orchestrator)
        elif choice == "2":
            handle_text_report(orchestrator)
        elif choice == "3" and voice_mode:
            handle_voice_report(orchestrator)
        elif choice == "4":
            handle_progress(orchestrator)
        elif choice == "0":
            console.print("\n[bold]Hasta luego![/bold]\n")
            break
        else:
            console.print("[red]Opcion no valida[/red]")


if __name__ == "__main__":
    main()
