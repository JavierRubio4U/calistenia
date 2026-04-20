"""
main.py - Interfaz CLI para Calistenia Coach (Termux / desktop)

Usa texto + Gboard micrófono para voz en Android.
El email se configura en .env como CLI_USER_EMAIL.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

load_dotenv(Path(__file__).parent / ".env")

from database import init_db, get_user_profile
from agents import Orchestrator

console = Console()

CLI_USER_EMAIL = os.getenv("CLI_USER_EMAIL", "carthagonova@gmail.com")


def show_header(profile):
    if profile:
        info = (
            f"[bold cyan]Hola {profile['name']}![/bold cyan] | "
            f"[yellow]{profile['age']} años[/yellow] | "
            f"[green]{profile['current_weight']} kg[/green]\n"
            f"[dim]Lesiones: {profile['injuries']}[/dim]\n"
            f"[dim]Objetivo: {profile['goals']}[/dim]"
        )
    else:
        info = "[bold red]Perfil no encontrado en la base de datos.[/bold red]"
    console.print(Panel(info, title="[bold green]CALISTENIA COACH[/bold green]",
                        border_style="green", expand=False))


def show_menu():
    t = Table(show_header=False, box=None)
    t.add_column("Op", style="bold cyan")
    t.add_column("Des", style="white")
    t.add_row("[1]", "Pedir rutina de hoy")
    t.add_row("[2]", "Reportar sesión  (texto / voz con Gboard)")
    t.add_row("[3]", "Ver mi progreso")
    t.add_row("[0]", "Salir")
    console.print(t)


def ask_fatigue() -> int:
    console.print("[dim]Fatiga al terminar (1=fresco · 10=agotado)[/dim]")
    while True:
        try:
            v = int(console.input("[bold]Fatiga > [/bold]").strip())
            if 1 <= v <= 10:
                return v
        except ValueError:
            pass
        console.print("[red]Introduce un número del 1 al 10[/red]")


def handle_workout(orch):
    console.print("\n[dim]¿Dónde entrenas? (p=parque / c=casa)[/dim]")
    lugar = "Parque / Calistenia" if console.input("> ").strip().lower() != "c" else "Casa"
    energia = int(console.input("[bold]Energía hoy (1-10) > [/bold]").strip() or "7")
    nota = console.input("[dim]Nota adicional (Enter para saltar): [/dim]").strip()
    contexto = f"LUGAR HOY: {lugar}. Nivel de energía: {energia}/10."
    if nota:
        contexto += f" Nota: {nota}."
    console.print("\n[bold blue]Diseñando tu rutina...[/bold blue]\n")
    try:
        console.print(Markdown(orch.get_workout_plan(context=contexto)))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def handle_report(orch):
    console.print("\n[dim]Cuéntame cómo fue (usa el micrófono de Gboard si quieres dictar):[/dim]")
    report = console.input("[bold]Reporte > [/bold]").strip()
    if not report:
        return
    fatiga = ask_fatigue()
    contexto = f"FATIGA REPORTADA POR EL USUARIO: {fatiga}/10.\n"
    console.print("\n[bold blue]Procesando...[/bold blue]")
    try:
        receptor_resp, analyst_resp = orch.report_session(
            f"{contexto}{report}"
        )
        console.print("\n[bold green]✅ Sesión guardada:[/bold green]")
        console.print(Markdown(receptor_resp))
        if analyst_resp:
            console.print("\n[bold magenta]📈 Análisis:[/bold magenta]")
            console.print(Markdown(analyst_resp))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def handle_progress(orch):
    console.print("\n[bold yellow]Analizando tu progreso...[/bold yellow]\n")
    try:
        console.print(Markdown(orch.analyze_progress()))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def main():
    init_db()
    profile = get_user_profile(user_email=CLI_USER_EMAIL)
    if not profile:
        console.print(f"[red]No se encontró perfil para {CLI_USER_EMAIL}[/red]")
        return
    orch = Orchestrator(user_email=CLI_USER_EMAIL, profile=profile)
    show_header(profile)

    while True:
        console.print()
        show_menu()
        try:
            choice = console.input("[bold]> [/bold]").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if choice == "1":
            handle_workout(orch)
        elif choice == "2":
            handle_report(orch)
        elif choice == "3":
            handle_progress(orch)
        elif choice == "0":
            break
        else:
            console.print("[red]Opción no válida[/red]")


if __name__ == "__main__":
    main()
