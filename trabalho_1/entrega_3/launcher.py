import subprocess
import sys
import os
import time
import threading
from collections import deque
from datetime import datetime

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.columns import Columns
from rich import box
from rich.style import Style
import rich.spinner


# ──────────────────────────────────────────────
# Configuração
# ──────────────────────────────────────────────

LOG_FILES = {
    "central": "logs/central.log",
    "dist1":   "logs/dist1.log",
    "dist2":   "logs/dist2.log",
}

LOG_COLORS = {
    "[CENTRAL]": "bold cyan",
    "[TCP]":     "cyan",
    "[DIST 1]":  "bold green",
    "[DIST 2]":  "bold blue",
    "[PUSH]":    "bold yellow",
    "[LPR]":     "yellow",
    "[EMERGENCY]": "bold red",
    "[NIGHT":    "magenta",
    "[MODBUS]":  "white",
    "[ERROR]":   "bold red",
}

MAX_LOG_LINES   = 200   # buffer máximo por processo
VISIBLE_LINES   = 22    # linhas exibidas no painel de log
REFRESH_RATE    = 0.25  # segundos entre re-renders

console = Console()


# ──────────────────────────────────────────────
# Estado global
# ──────────────────────────────────────────────

processes:    dict[str, subprocess.Popen]  = {}
log_handles:  dict[str, object]            = {}
log_buffers:  dict[str, deque]             = {k: deque(maxlen=MAX_LOG_LINES) for k in LOG_FILES}
tail_threads: dict[str, threading.Thread]  = {}
start_times:  dict[str, float]             = {}

active_tab    = "central"   # aba de log visível
status_msg    = ""          # mensagem de status na barra inferior
lock          = threading.Lock()


# ──────────────────────────────────────────────
# Helpers de processo
# ──────────────────────────────────────────────

def _ensure_log_dir():
    os.makedirs("logs", exist_ok=True)


def _tail_log(name: str, path: str):
    """Lê linhas novas do arquivo de log e empurra para o buffer."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            # avança até o fim (evita re-ler log anterior)
            f.seek(0, 2)
            while name in processes:
                line = f.readline()
                if line:
                    ts = datetime.now().strftime("%H:%M:%S")
                    with lock:
                        log_buffers[name].append((ts, line.rstrip()))
                else:
                    time.sleep(0.05)
    except Exception:
        pass


def _start(name: str, cmd: list[str]):
    if name in processes:
        _set_status(f"{name} já está rodando")
        return
    _ensure_log_dir()
    path = LOG_FILES[name]
    log_handles[name] = open(path, "w", encoding="utf-8")
    processes[name]   = subprocess.Popen(
        cmd,
        stdout=log_handles[name],
        stderr=subprocess.STDOUT,
    )
    start_times[name] = time.time()
    t = threading.Thread(target=_tail_log, args=(name, path), daemon=True)
    t.start()
    tail_threads[name] = t
    _set_status(f"{name} iniciado (PID {processes[name].pid})")


def _stop(name: str):
    if name not in processes:
        _set_status(f"{name} não está rodando")
        return
    processes[name].terminate()
    try:
        processes[name].wait(timeout=3)
    except subprocess.TimeoutExpired:
        processes[name].kill()
    processes.pop(name)
    log_handles[name].close()
    log_handles.pop(name)
    start_times.pop(name, None)
    _set_status(f"{name} encerrado")


def _set_status(msg: str):
    global status_msg
    status_msg = msg


# ──────────────────────────────────────────────
# Ações de menu
# ──────────────────────────────────────────────

def start_central():
    _start("central", [sys.executable, "-u", "-m", "central.main"])

def start_dist1():
    _start("dist1", [sys.executable, "-u", "-m", "distributed.main", "config/intersection1.json"])

def start_dist2():
    _start("dist2", [sys.executable, "-u", "-m", "distributed.main", "config/intersection2.json"])

def start_all():
    start_central(); start_dist1(); start_dist2()
    _set_status("todos os processos iniciados")

def stop_all():
    for name in list(processes):
        _stop(name)
    _set_status("todos os processos encerrados")


# ──────────────────────────────────────────────
# Renderização Rich
# ──────────────────────────────────────────────

def _status_dot(name: str) -> Text:
    proc = processes.get(name)
    if proc is None:
        return Text("● offline", style="dim red")
    if proc.poll() is not None:
        return Text("● encerrado", style="bold red")
    return Text("● online", style="bold green")


def _uptime(name: str) -> str:
    t = start_times.get(name)
    if t is None:
        return "—"
    s = int(time.time() - t)
    return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"


def _colorize_line(ts: str, raw: str) -> Text:
    t = Text()
    t.append(ts + " ", style="dim")
    color = "white"
    for tag, c in LOG_COLORS.items():
        if tag in raw:
            color = c
            break
    t.append(raw, style=color)
    return t


def _build_status_panel() -> Panel:
    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)

    def proc_cell(name: str, label: str) -> Text:
        t = Text()
        t.append(f"{label}\n", style="bold")
        t.append(_status_dot(name))
        t.append(f"  uptime: {_uptime(name)}", style="dim")
        return t

    grid.add_row(
        proc_cell("central", "Central"),
        proc_cell("dist1",   "Distribuído 1"),
        proc_cell("dist2",   "Distribuído 2"),
    )
    return Panel(grid, title="[bold]Status dos processos[/]", border_style="bright_black", box=box.ROUNDED)


def _build_log_panel() -> Panel:
    # cabeçalho das abas
    tabs_text = Text()
    for key, label in [("central", "Central"), ("dist1", "Dist-1"), ("dist2", "Dist-2")]:
        if key == active_tab:
            tabs_text.append(f" {label} ", style="bold black on cyan")
        else:
            tabs_text.append(f" {label} ", style="dim")
        tabs_text.append("  ")

    with lock:
        lines = list(log_buffers[active_tab])[-VISIBLE_LINES:]

    log_text = Text()
    for ts, raw in lines:
        log_text.append_text(_colorize_line(ts, raw))
        log_text.append("\n")

    # preenche linhas vazias para manter altura fixa
    missing = VISIBLE_LINES - len(lines)
    log_text.append("\n" * missing)

    return Panel(
        log_text,
        title=tabs_text,
        subtitle=Text(f"  últimas {VISIBLE_LINES} linhas  ", style="dim"),
        border_style="bright_black",
        box=box.ROUNDED,
    )


def _build_controls_panel() -> Panel:
    t = Table.grid(padding=(0, 1))
    t.add_column(style="bold cyan", min_width=4)
    t.add_column()

    rows = [
        ("[1]", "[green]▶[/] iniciar Central"),
        ("[2]", "[green]▶[/] iniciar Dist-1"),
        ("[3]", "[green]▶[/] iniciar Dist-2"),
        ("[A]", "[green]▶[/] iniciar tudo"),
        ("",    ""),
        ("[Q]", "[red]■[/] parar Central"),
        ("[W]", "[red]■[/] parar Dist-1"),
        ("[E]", "[red]■[/] parar Dist-2"),
        ("[S]", "[red]■[/] parar tudo"),
        ("",    ""),
        ("[Tab]","trocar aba de log"),
        ("[0]", "[bold red]sair[/]"),
    ]
    for key, desc in rows:
        t.add_row(key, desc)

    return Panel(t, title="[bold]Controles[/]", border_style="bright_black", box=box.ROUNDED)


def _build_bottom_bar() -> Text:
    now = datetime.now().strftime("%H:%M:%S")
    t = Text()
    t.append(f" {now} ", style="bold")
    t.append("│ ", style="dim")
    if status_msg:
        t.append(status_msg, style="yellow")
    else:
        t.append("aguardando comando...", style="dim")
    return t


def _build_layout() -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="top",    size=7),
        Layout(name="middle", ratio=1),
        Layout(name="bottom", size=1),
    )
    layout["middle"].split_row(
        Layout(name="logs",     ratio=3),
        Layout(name="controls", ratio=1),
    )
    layout["top"].update(_build_status_panel())
    layout["logs"].update(_build_log_panel())
    layout["controls"].update(_build_controls_panel())
    layout["bottom"].update(_build_bottom_bar())
    return layout


# ──────────────────────────────────────────────
# Loop principal (input não-bloqueante)
# ──────────────────────────────────────────────

def _switch_tab():
    global active_tab
    tabs = ["central", "dist1", "dist2"]
    idx = tabs.index(active_tab)
    active_tab = tabs[(idx + 1) % len(tabs)]
    _set_status(f"aba: {active_tab}")


def _handle_key(key: str) -> bool:
    """Retorna False para sair."""
    key = key.strip().lower()
    if key == "1":   start_central()
    elif key == "2": start_dist1()
    elif key == "3": start_dist2()
    elif key == "a": start_all()
    elif key == "q": _stop("central")
    elif key == "w": _stop("dist1")
    elif key == "e": _stop("dist2")
    elif key == "s": stop_all()
    elif key == "\t": _switch_tab()   # Tab
    elif key == "0":
        stop_all()
        return False
    return True


def _input_thread(running: threading.Event):
    """Lê teclas em thread separada para não bloquear o Live render."""
    while running.is_set():
        try:
            key = input()
            if not _handle_key(key):
                running.clear()
                break
        except EOFError:
            running.clear()
            break


def main():
    running = threading.Event()
    running.set()

    t = threading.Thread(target=_input_thread, args=(running,), daemon=True)
    t.start()

    console.clear()
    with Live(
        _build_layout(),
        console=console,
        refresh_per_second=int(1 / REFRESH_RATE),
        screen=True,
    ) as live:
        while running.is_set():
            live.update(_build_layout())
            time.sleep(REFRESH_RATE)

    console.clear()
    console.print("[bold green]Launcher encerrado.[/]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        stop_all()
        console.print("\n[bold red]Interrompido.[/]")