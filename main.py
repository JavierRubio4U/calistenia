"""
main.py - Punto de entrada de Calistenia Coach (Edición Javi)

Interfaz CLI personalizada con el perfil de Javi y soporte multimodal.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

# Cargar entorno
load_dotenv(Path(__file__).parent / ".env")

from database import init_db, get_user_profile
from agents import Orchestrator
from voice import get_voice_mode, record_audio

console = Console()

def show_header(profile):
    """Muestra la cabecera personalizada para Javi."""
    console.print()
    
    # Crear panel de perfil
    if profile:
        profile_info = (
            f"[bold cyan]Hola {profile['name']}![/bold cyan] | "
            f"[yellow]{profile['age']} años[/yellow] | "
            f"[green]{profile['current_weight']} kg[/green]\n"
            f"[dim]Lesiones: {profile['injuries']}[/dim]\n"
            f"[dim]Objetivos: {profile['goals']}[/dim]"
        )
    else:
        profile_info = "[bold red]Perfil no encontrado. Inicializando...[/bold red]"

    console.print(Panel(
        profile_info,
        title="[bold green]CALISTENIA COACH [Agentes Gemini][/bold green]",
        border_style="green",
        expand=False
    ))

def show_menu(voice_available):
    table = Table(show_header=False, box=None)
    table.add_column("Op", style="bold cyan")
    table.add_column("Des", style="white")
    
    table.add_row("[1]", "Pedir rutina segura de hoy (Impacto 0)")
    table.add_row("[2]", "Reportar sesión (Texto)")
    if voice_available:
        table.add_row("[3]", "Reportar sesión (VOZ DIRECTA - Javi dice cómo le fue)")
    table.add_row("[4]", "Ver progreso y objetivos alcanzados")
    table.add_row("[0]", "Salir")
    
    console.print(table)

def handle_workout_plan(orchestrator):
    console.print("\n[bold blue]🤖 Entrenador diseñando tu rutina segura...[/bold blue]\n")
    try:
        plan = orchestrator.get_workout_plan()
        console.print(Markdown(plan))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

def handle_text_report(orchestrator):
    console.print("\n[dim]Cuéntame qué has hecho Javi. Ej: '5s colgado, 10 flexiones pared, peso 134.5kg'[/dim]")
    report = console.input("[bold]Tu reporte: [/bold]")
    if not report.strip(): return
    process_report(orchestrator, report)

def handle_voice_report(orchestrator):
    audio_path = record_audio()
    if not audio_path:
        console.print("[yellow]Grabación cancelada.[/yellow]")
        return

    console.print("\n[bold cyan]🎙️ Javi, estoy escuchando tu reporte...[/bold cyan]")
    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
            
        from google.genai import types
        multimodal_input = [
            types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
            "Este es mi reporte de entrenamiento. Soy Javi. Por favor, analízalo y actualiza mi progreso."
        ]
        
        process_report(orchestrator, multimodal_input)
        if os.path.exists(audio_path):
            os.remove(audio_path)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

def process_report(orchestrator, report_input):
    try:
        receptor_resp, analyst_resp = orchestrator.report_session(report_input)
        console.print("\n[bold green]✅ Reporte Guardado:[/bold green]")
        console.print(Markdown(receptor_resp))

        if analyst_resp:
            console.print("\n[bold magenta]📈 Análisis de Progreso:[/bold magenta]")
            console.print(Markdown(analyst_resp))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

def handle_progress(orchestrator):
    console.print("\n[bold yellow]🔍 Analizando tus hitos, Javi...[/bold yellow]\n")
    try:
        progress = orchestrator.analyze_progress()
        console.print(Markdown(progress))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

def main():
    init_db()
    profile = get_user_profile()
    voice_mode = get_voice_mode()
    orchestrator = Orchestrator()

    show_header(profile)
    
    while True:
        show_menu(voice_available=voice_mode is not None)
        try:
            choice = console.input("[bold]Selección > [/bold]").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if choice == "1": handle_workout_plan(orchestrator)
        elif choice == "2": handle_text_report(orchestrator)
        elif choice == "3" and voice_mode: handle_voice_report(orchestrator)
        elif choice == "4": handle_progress(orchestrator)
        elif choice == "0": break
        else: console.print("[red]Opción no válida[/red]")

if __name__ == "__main__":
    main()
