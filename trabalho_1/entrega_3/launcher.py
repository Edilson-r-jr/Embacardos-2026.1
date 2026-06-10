import subprocess
import sys
import os
import json
import time
import threading
import select
import tty
import termios
from collections import deque
from datetime import datetime

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich import box

# ──────────────────────────────────────────────
# Configuração
# ──────────────────────────────────────────────

LOG_FILES = {
    "central": "logs/central.log",
    "dist1":   "logs/dist1.log",
    "dist2":   "logs/dist2.log",
}

MULTAS_FILE = "multas.json"

LOG_COLORS = {
    "[CENTRAL]":   "bold cyan",
    "[TCP]":       "cyan",
    "[DIST 1]":    "bold green",
    "[DIST 2]":    "bold blue",
    "[PUSH]":      "bold yellow",
    "[LPR]":       "yellow",
    "[EMERGENCY]": "bold red",
    "[NIGHT":      "magenta",
    "[MODBUS]":    "white",
    "[ERROR]":     "bold red",
}

# Tags consideradas "ruído" — filtradas quando filtro ativo
NOISE_TAGS = {"[MODBUS]", "[TCP]"}

MAX_LOG_LINES = 300
VISIBLE_LINES = 20
REFRESH_RATE  = 0.25

TABS = ["central", "dist1", "dist2", "multas"]

console = Console()


# ──────────────────────────────────────────────
# Estado global
# ──────────────────────────────────────────────

processes:    dict[str, subprocess.Popen] = {}
log_handles:  dict[str, object]           = {}
log_buffers:  dict[str, deque]            = {k: deque(maxlen=MAX_LOG_LINES) for k in LOG_FILES}
tail_threads: dict[str, threading.Thread] = {}
start_times:  dict[str, float]            = {}

active_tab    = "central"
status_msg    = ""
filter_noise  = False          # quando True, omite linhas com NOISE_TAGS
scroll_offsets: dict[str, int] = {k: 0 for k in TABS}  # 0 = fim do buffer
lock          = threading.Lock()


# ──────────────────────────────────────────────
# Helpers de processo
# ──────────────────────────────────────────────

def _ensure_log_dir():
    os.makedirs("logs", exist_ok=True)


def _tail_log(name: str, path: str):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
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
# Navegação: abas e scroll
# ──────────────────────────────────────────────

def _scroll(lines: int):
    """Ajusta offset de scroll da aba ativa. Positivo = sobe, negativo = desce."""
    with lock:
        if active_tab == "multas":
            return
        buf = log_buffers[active_tab]
        max_offset = max(0, len(buf) - VISIBLE_LINES)
        new_offset = scroll_offsets[active_tab] + lines
        scroll_offsets[active_tab] = max(0, min(new_offset, max_offset))
    off = scroll_offsets[active_tab]
    if off == 0:
        _set_status("fim do log")
    else:
        _set_status(f"scroll: {off} linhas acima do fim")


def _toggle_filter():
    global filter_noise
    filter_noise = not filter_noise
    state = "ativado" if filter_noise else "desativado"
    _set_status(f"filtro de ruído {state}")


# ──────────────────────────────────────────────
# Renderização Rich
# ──────────────────────────────────────────────

def _status_dot(name: str) -> Text:
    proc = processes.get(name)
    if proc is None:
        return Text("● offline",   style="dim red")
    if proc.poll() is not None:
        return Text("● encerrado", style="bold red")
    return Text("● online",       style="bold green")


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


def _build_tabs_header() -> Text:
    labels = {"central": "Central", "dist1": "Dist-1", "dist2": "Dist-2", "multas": "Multas"}
    t = Text()
    for key in TABS:
        if key == active_tab:
            t.append(f" {labels[key]} ", style="bold black on cyan")
        else:
            t.append(f" {labels[key]} ", style="dim")
        t.append("  ")
    return t


def _build_log_panel() -> Panel:
    if active_tab == "multas":
        return _build_multas_panel()

    with lock:
        all_lines = list(log_buffers[active_tab])
        offset = scroll_offsets[active_tab]

    # aplicar filtro de ruído
    if filter_noise:
        all_lines = [
            (ts, raw) for ts, raw in all_lines
            if not any(tag in raw for tag in NOISE_TAGS)
        ]

    n = len(all_lines)
    if offset == 0:
        lines = all_lines[-VISIBLE_LINES:]
    else:
        end = max(0, n - offset)
        start = max(0, end - VISIBLE_LINES)
        lines = all_lines[start:end]

    log_text = Text()
    for ts, raw in lines:
        log_text.append_text(_colorize_line(ts, raw))
        log_text.append("\n")
    log_text.append("\n" * max(0, VISIBLE_LINES - len(lines)))

    # subtítulo mostra posição no buffer
    if offset == 0:
        sub_info = f"  {n} linhas  fim  "
    else:
        sub_info = f"  {n} linhas  ↑ {offset} acima do fim  "
    if filter_noise:
        sub_info += "  [filtro ativo]  "

    subtitle = Text(sub_info, style="dim")

    return Panel(
        log_text,
        title=_build_tabs_header(),
        subtitle=subtitle,
        border_style="bright_black",
        box=box.ROUNDED,
    )


def _build_multas_panel() -> Panel:
    violations = []
    err_msg = ""
    try:
        if os.path.exists(MULTAS_FILE):
            with open(MULTAS_FILE, "r", encoding="utf-8") as f:
                violations = json.load(f)
        else:
            err_msg = f"Arquivo '{MULTAS_FILE}' não encontrado."
    except Exception as e:
        err_msg = f"Erro ao ler multas.json: {e}"

    if err_msg:
        body = Text(err_msg, style="dim red")
        return Panel(
            body,
            title=_build_tabs_header(),
            border_style="bright_black",
            box=box.ROUNDED,
        )

    # exibe as últimas N multas em tabela
    tbl = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold cyan",
        expand=True,
        padding=(0, 1),
    )
    tbl.add_column("Hora",         style="dim",          width=8)
    tbl.add_column("Cruzamento",   style="cyan",         width=12)
    tbl.add_column("Placa",        style="bold white",   width=10)
    tbl.add_column("Velocidade",   style="bold yellow",  width=12, justify="right")
    tbl.add_column("Confiança",    style="green",        width=10, justify="right")
    tbl.add_column("Multa (R$)",   style="bold red",     width=12, justify="right")
    tbl.add_column("Sensor",       style="dim",          width=8)

    shown = violations[-VISIBLE_LINES:]
    for v in reversed(shown):
        ts_raw = v.get("timestamp", "")
        # extrai só HH:MM:SS se vier no formato ISO
        try:
            ts = datetime.fromisoformat(str(ts_raw)).strftime("%H:%M:%S")
        except Exception:
            ts = str(ts_raw)[:8]

        tbl.add_row(
            ts,
            str(v.get("intersection_id", "—")),
            str(v.get("plate", "—")),
            f'{v.get("speed_kmh", 0):.1f} km/h',
            f'{v.get("confidence", 0)*100:.0f}%' if isinstance(v.get("confidence"), float) else str(v.get("confidence", "—")),
            f'R$ {v.get("fine_value", 0):.2f}',
            str(v.get("sensor_id", "—")),
        )

    total = len(violations)
    subtitle = Text(f"  {total} multa(s) registrada(s) — mostrando últimas {min(total, VISIBLE_LINES)}  ", style="dim")

    return Panel(
        tbl,
        title=_build_tabs_header(),
        subtitle=subtitle,
        border_style="bright_black",
        box=box.ROUNDED,
    )


def _build_controls_panel() -> Panel:
    t = Table.grid(padding=(0, 1))
    t.add_column(style="bold cyan", min_width=6)
    t.add_column()

    rows = [
        ("[bold]Processos[/]", ""),
        ("[1]", "[green]▶[/] iniciar Central"),
        ("[2]", "[green]▶[/] iniciar Dist-1"),
        ("[3]", "[green]▶[/] iniciar Dist-2"),
        ("[A]", "[green]▶[/] iniciar tudo"),
        ("[Q]", "[red]■[/] parar Central"),
        ("[W]", "[red]■[/] parar Dist-1"),
        ("[E]", "[red]■[/] parar Dist-2"),
        ("[S]", "[red]■[/] parar tudo"),
        ("", ""),
        ("[bold]Abas[/]", ""),
        ("[C]",  "aba Central"),
        ("[V]",  "aba Dist-1"),
        ("[B]",  "aba Dist-2"),
        ("[N]",  "aba Multas"),
        ("", ""),
        ("[bold]Scroll[/]", ""),
        ("[↑]",  "scroll ↑ (5 linhas)"),
        ("[↓]",  "scroll ↓ (5 linhas)"),
        ("[R]",  "voltar ao fim"),
        ("[F]",       "filtro ruído on/off"),
        ("", ""),
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
    if filter_noise:
        t.append("  [filtro ativo]", style="dim magenta")
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
# Loop principal
# ──────────────────────────────────────────────

TAB_KEYS = {"c": "central", "v": "dist1", "b": "dist2", "n": "multas"}


def _handle_key(key: str) -> bool:
    """Retorna False para sair."""
    if key in TAB_KEYS:
        global active_tab
        active_tab = TAB_KEYS[key]
        _set_status(f"aba: {active_tab}")
    elif key == "up":     _scroll(+5)
    elif key == "down":   _scroll(-5)
    elif key == "1":      start_central()
    elif key == "2":      start_dist1()
    elif key == "3":      start_dist2()
    elif key == "a":      start_all()
    elif key == "q":      _stop("central")
    elif key == "w":      _stop("dist1")
    elif key == "e":      _stop("dist2")
    elif key == "s":      stop_all()
    elif key == "r":
        with lock:
            scroll_offsets[active_tab] = 0
        _set_status("fim do log")
    elif key == "f":      _toggle_filter()
    elif key == "0":
        stop_all()
        return False
    return True


def _read_key() -> str:
    """Lê uma tecla em modo raw e retorna um identificador legível."""
    ch = sys.stdin.read(1)
    if ch == "\x1b":
        # tenta ler o restante da sequência de escape (ex.: setas)
        ready = select.select([sys.stdin], [], [], 0.05)[0]
        if ready:
            ch2 = sys.stdin.read(1)
            if ch2 == "[":
                ready2 = select.select([sys.stdin], [], [], 0.05)[0]
                if ready2:
                    ch3 = sys.stdin.read(1)
                    if ch3 == "A": return "up"
                    if ch3 == "B": return "down"
                    if ch3 == "C": return "right"
                    if ch3 == "D": return "left"
        return "esc"
    return ch.lower()


def _input_thread(running: threading.Event):
    if not sys.stdin.isatty():
        # fallback para ambientes sem TTY (pipe, testes)
        while running.is_set():
            try:
                key = input().strip().lower()
                if not _handle_key(key):
                    running.clear()
            except EOFError:
                running.clear()
        return

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while running.is_set():
            ready = select.select([sys.stdin], [], [], 0.1)[0]
            if ready:
                key = _read_key()
                if not _handle_key(key):
                    running.clear()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


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
