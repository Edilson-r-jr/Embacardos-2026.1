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
CMD_FILE    = "central_cmd.json"

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

MAX_LOG_LINES = 300
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

active_tab     = "central"
status_msg     = ""
scroll_offsets: dict[str, int] = {k: 0 for k in TABS}
lock           = threading.Lock()
force_mode     = False
night_mode_on  = False


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


def _write_central_cmd(cmd: dict):
    try:
        with open(CMD_FILE, "w", encoding="utf-8") as f:
            json.dump(cmd, f)
    except Exception:
        pass


def _enable_mouse():
    sys.stdout.write("\x1b[?1000h")
    sys.stdout.flush()

def _disable_mouse():
    sys.stdout.write("\x1b[?1000l")
    sys.stdout.flush()


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
# Helpers de layout
# ──────────────────────────────────────────────

def _get_visible_lines() -> int:
    # overhead: top(5) + actions(3 normal / 4 force) + bottom(1) + bordas(2)
    return max(5, console.size.height - (13 if force_mode else 11))


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
        return ""
    s = int(time.time() - t)
    return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"


def _parse_log_tag(raw: str) -> tuple[str, str, str]:
    """Returns (tag_key, display_label, message) from a raw log line."""
    for tag in LOG_COLORS:
        if tag in raw:
            idx = raw.index(tag)
            after = raw[idx + len(tag):]
            if tag.endswith("]"):
                label = tag[1:-1]
            else:
                end = raw.find("]", idx + len(tag))
                if end != -1:
                    label = raw[idx + 1:end]
                    after = raw[end + 1:]
                else:
                    label = tag[1:]
            return tag, label, after.strip()
    return "", "—", raw


def _build_log_table(lines: list) -> Table:
    tbl = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold cyan",
        expand=True,
        padding=(0, 1),
    )
    tbl.add_column("Hora",    style="dim", no_wrap=True, width=8)
    tbl.add_column("Módulo",  no_wrap=True, width=12)
    tbl.add_column("Mensagem")

    for ts, raw in lines:
        tag_key, label, msg = _parse_log_tag(raw)
        color = LOG_COLORS.get(tag_key, "dim")
        tbl.add_row(
            ts,
            Text(label, style=color),
            Text(msg if msg else raw, style="white"),
        )
    return tbl


def _build_status_panel() -> Panel:
    proc_grid = Table.grid(expand=True, padding=(0, 2))
    proc_grid.add_column(ratio=1)
    proc_grid.add_column(ratio=1)
    proc_grid.add_column(ratio=1)

    def proc_cell(name: str, label: str, k_start: str, k_stop: str, k_tab: str) -> Text:
        t = Text()
        t.append(f"{label}\n", style="bold")
        t.append(_status_dot(name))
        up = _uptime(name)
        if up:
            t.append(f"  {up}", style="dim")
        t.append("\n")
        t.append(f"[{k_start}]", style="bold cyan"); t.append(" ▶  ", style="green")
        t.append(f"[{k_stop}]",  style="bold cyan"); t.append(" ■  ", style="red")
        t.append(f"[{k_tab}]",   style="bold cyan"); t.append(" log", style="dim")
        return t

    proc_grid.add_row(
        proc_cell("central", "Central",       "1", "Q", "C"),
        proc_cell("dist1",   "Distribuído 1", "2", "W", "V"),
        proc_cell("dist2",   "Distribuído 2", "3", "E", "B"),
    )

    return Panel(proc_grid, title="[bold]Status dos processos[/]", border_style="bright_black", box=box.ROUNDED)


def _build_actions_panel() -> Panel:
    if force_mode:
        grid = Table.grid(expand=True, padding=(0, 1))
        grid.add_column()

        row1 = Text()
        row1.append("CRZ-1: ", style="bold")
        for k, lbl in [("1", "principal"), ("2", "cruzamento"), ("3", "vermelho"), ("4", "normal")]:
            row1.append(f"[{k}]", style="bold cyan"); row1.append(f" {lbl}   ", style="dim")
        row1.append("│  ", style="dim")
        row1.append("[Y]", style="bold cyan"); row1.append(" amarelo intermitente", style="dim")

        row2 = Text()
        row2.append("CRZ-2: ", style="bold")
        for k, lbl in [("5", "principal"), ("6", "cruzamento"), ("7", "vermelho"), ("8", "normal")]:
            row2.append(f"[{k}]", style="bold cyan"); row2.append(f" {lbl}   ", style="dim")
        row2.append("│  ", style="dim")
        row2.append("[Esc]", style="bold cyan"); row2.append(" cancelar", style="dim")

        grid.add_row(row1)
        grid.add_row(row2)
        return Panel(grid, title="[bold yellow]Controle Manual[/]", border_style="yellow", box=box.ROUNDED)

    t = Text(justify="center")
    t.append("[A]", style="bold cyan"); t.append(" ▶ iniciar todos    ", style="dim")
    t.append("[S]", style="bold cyan"); t.append(" ■ parar todos    ",   style="dim")
    t.append("[F]", style="bold cyan"); t.append(" controle    ",        style="dim")
    t.append("[N]", style="bold cyan"); t.append(" multas    ",          style="dim")
    t.append("[0]", style="bold cyan"); t.append(" sair",                style="dim")
    return Panel(t, border_style="bright_black", box=box.ROUNDED)


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

    visible = _get_visible_lines()
    with lock:
        all_lines = list(log_buffers[active_tab])
        offset = scroll_offsets[active_tab]

    n = len(all_lines)

    # corrige offset caso o terminal tenha sido redimensionado
    max_offset = max(0, n - visible)
    if offset > max_offset:
        offset = max_offset
        with lock:
            scroll_offsets[active_tab] = offset

    if offset == 0:
        lines = all_lines[-visible:]
    else:
        end   = max(0, n - offset)
        start = max(0, end - visible)
        lines = all_lines[start:end]

    sub_info = f"  {n} linhas"
    if offset > 0:
        sub_info += f"  ↑ {offset} acima do fim"
    sub_info += "  "

    return Panel(
        _build_log_table(lines),
        title=_build_tabs_header(),
        subtitle=Text(sub_info, style="dim"),
        border_style="bright_black",
        box=box.ROUNDED,
    )


def _build_multas_panel() -> Panel:
    visible = _get_visible_lines()
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
        return Panel(
            Text(err_msg, style="dim red"),
            title=_build_tabs_header(),
            border_style="bright_black",
            box=box.ROUNDED,
        )

    tbl = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold cyan",
        expand=True,
        padding=(0, 1),
    )
    tbl.add_column("Hora",        style="dim",         no_wrap=True)
    tbl.add_column("Cruzamento",  style="cyan",        no_wrap=True)
    tbl.add_column("Placa",       style="bold white",  no_wrap=True)
    tbl.add_column("Velocidade",  style="bold yellow", no_wrap=True, justify="right")
    tbl.add_column("Confiança",   style="green",       no_wrap=True, justify="right")
    tbl.add_column("Multa (R$)",  style="bold red",    no_wrap=True, justify="right")
    tbl.add_column("Sensor",      style="dim",         no_wrap=True)

    shown = violations[-visible:]
    for v in reversed(shown):
        ts_raw = v.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(str(ts_raw)).strftime("%H:%M:%S")
        except Exception:
            ts = str(ts_raw)[:8]

        conf = v.get("confidence", "—")
        conf_str = f'{conf*100:.0f}%' if isinstance(conf, float) else str(conf)

        tbl.add_row(
            ts,
            str(v.get("intersection_id", "—")),
            str(v.get("plate", "—")),
            f'{v.get("speed_kmh", 0):.1f} km/h',
            conf_str,
            f'R$ {v.get("fine_value", 0):.2f}',
            str(v.get("sensor_id", "—")),
        )

    total = len(violations)
    return Panel(
        tbl,
        title=_build_tabs_header(),
        subtitle=Text(f"  {total} multa(s) — mostrando últimas {min(total, visible)}  ", style="dim"),
        border_style="bright_black",
        box=box.ROUNDED,
    )


def _build_bottom_bar() -> Text:
    now = datetime.now().strftime("%H:%M:%S")
    t = Text()
    t.append(f" {now} ", style="bold")
    t.append("│ ", style="dim")
    if status_msg:
        t.append(status_msg, style="yellow")
    else:
        t.append("scroll: roda do mouse", style="dim")
    return t


def _build_layout() -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="top",     size=5),
        Layout(name="actions", size=4 if force_mode else 3),
        Layout(name="middle",  ratio=1),
        Layout(name="bottom",  size=1),
    )
    layout["top"].update(_build_status_panel())
    layout["actions"].update(_build_actions_panel())
    layout["middle"].update(_build_log_panel())
    layout["bottom"].update(_build_bottom_bar())
    return layout


# ──────────────────────────────────────────────
# Loop principal
# ──────────────────────────────────────────────

TAB_KEYS = {"c": "central", "v": "dist1", "b": "dist2", "n": "multas"}

_FORCE_MAP = {
    "1": (1, 1),    "2": (1, 5),    "3": (1, 4),    "4": (1, None),
    "5": (2, 1),    "6": (2, 5),    "7": (2, 4),    "8": (2, None),
}
_STATE_LABELS = {1: "principal verde", 5: "cruzamento verde", 4: "vermelho total", None: "normal"}


def _handle_force_key(key: str):
    global force_mode, night_mode_on
    if key in _FORCE_MAP:
        iid, code = _FORCE_MAP[key]
        _write_central_cmd({"type": "manual_override", "intersection_id": iid, "state_code": code})
        _set_status(f"CRZ-{iid}: {_STATE_LABELS[code]}")
        force_mode = False
    elif key == "y":
        night_mode_on = not night_mode_on
        _write_central_cmd({"type": "night_mode", "enabled": night_mode_on})
        _set_status(f"amarelo intermitente: {'ON' if night_mode_on else 'OFF'}")
        force_mode = False


def _handle_key(key: str) -> bool:
    global active_tab, force_mode

    if key == "esc":
        if force_mode:
            force_mode = False
            _set_status("controle cancelado")
        return True

    if force_mode:
        _handle_force_key(key)
        return True

    if key in TAB_KEYS:
        active_tab = TAB_KEYS[key]
        _set_status(f"aba: {active_tab}")
    elif key == "scroll_up":
        if active_tab != "multas":
            with lock:
                buf     = log_buffers[active_tab]
                visible = _get_visible_lines()
                max_off = max(0, len(buf) - visible)
                scroll_offsets[active_tab] = min(scroll_offsets[active_tab] + 3, max_off)
    elif key == "scroll_down":
        if active_tab != "multas":
            with lock:
                scroll_offsets[active_tab] = max(0, scroll_offsets[active_tab] - 3)
    elif key == "1":  start_central()
    elif key == "2":  start_dist1()
    elif key == "3":  start_dist2()
    elif key == "a":  start_all()
    elif key == "q":  _stop("central")
    elif key == "w":  _stop("dist1")
    elif key == "e":  _stop("dist2")
    elif key == "s":  stop_all()
    elif key == "f":
        force_mode = True
        _set_status("controle manual: escolha ação (Esc cancela)")
    elif key == "0":
        stop_all()
        return False
    return True


def _drain(n: int, timeout: float = 0.15):
    """Descarta n bytes do stdin com timeout por byte."""
    for _ in range(n):
        if not select.select([sys.stdin], [], [], timeout)[0]:
            break
        sys.stdin.read(1)


def _read_key() -> str:
    """Lê uma tecla ou evento de mouse em modo raw."""
    ch = sys.stdin.read(1)
    if not ch:
        return ""
    if ch == "\x1b":
        if not select.select([sys.stdin], [], [], 0.1)[0]:
            return "esc"
        ch2 = sys.stdin.read(1)
        if ch2 != "[":
            return "esc"
        if not select.select([sys.stdin], [], [], 0.1)[0]:
            return "esc"
        ch3 = sys.stdin.read(1)
        if ch3 == "M":
            try:
                if not select.select([sys.stdin], [], [], 0.15)[0]:
                    return "mouse"
                b = ord(sys.stdin.read(1)) - 32
                _drain(2)  # descarta x e y
                if b == 64: return "scroll_up"
                if b == 65: return "scroll_down"
            except Exception:
                pass
            return "mouse"
        # sequência desconhecida — bytes já consumidos, ignora
        return "esc"
    return ch.lower()


def _input_thread(running: threading.Event):
    if not sys.stdin.isatty():
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
        _enable_mouse()
        while running.is_set():
            ready = select.select([sys.stdin], [], [], 0.1)[0]
            if ready:
                try:
                    key = _read_key()
                except Exception:
                    continue
                if key and not _handle_key(key):
                    running.clear()
    finally:
        _disable_mouse()
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
