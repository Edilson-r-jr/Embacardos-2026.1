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

MULTAS_FILE         = "logs/multas.json"
SYSTEM_STATE_FILE   = "logs/system_state.json"
CENTRAL_EVENTS_FILE = "logs/central_events.json"
DIST_EVENTS_FILES   = {"dist1": "logs/dist1_events.json", "dist2": "logs/dist2_events.json"}
CMD_FILE            = "central_cmd.json"

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
lock = threading.Lock()
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


def _read_json(path: str) -> dict | list | None:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def _fmt_ts(ts_raw) -> str:
    try:
        return datetime.fromisoformat(str(ts_raw)).strftime("%H:%M:%S")
    except Exception:
        return str(ts_raw)[:8]


def _build_intersection_table() -> Table:
    tbl = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold cyan",
                expand=True, padding=(0, 1))
    tbl.add_column("CRZ",          style="bold cyan",   no_wrap=True, width=5)
    tbl.add_column("Fluxo (v/min)", style="white",       )
    tbl.add_column("Vel. Média",    style="bold yellow", )
    tbl.add_column("Infrações",     style="bold red",    no_wrap=True, justify="right", width=10)
    tbl.add_column("Multas",        style="green",       no_wrap=True, justify="right", width=14)

    state   = _read_json(SYSTEM_STATE_FILE) or {}
    multas  = _read_json(MULTAS_FILE) or []
    inters  = state.get("intersections", {})

    for iid_str in sorted(inters.keys(), key=int):
        iid  = int(iid_str)
        data = inters[iid_str]

        rates  = data.get("vehicle_rate", {})
        avg_sp = data.get("avg_speed",    {})

        flux_parts = [f"S{sid}: {v:.1f}" for sid, v in sorted((int(k), v) for k, v in rates.items())]
        avg_parts  = [f"S{sid}: {v:.1f}" for sid, v in sorted((int(k), v) for k, v in avg_sp.items())]

        flux_str = "  ".join(flux_parts) if flux_parts else "—"
        avg_str  = "  ".join(avg_parts)  if avg_parts  else "—"

        viol = data.get("speed_violations", 0)
        muls = [m for m in multas if m.get("intersection_id") == iid]
        total_val = sum(m.get("fine_value", 0) for m in muls)
        multas_str = f"{len(muls)}x  R$ {total_val:.2f}"

        tbl.add_row(str(iid), flux_str, avg_str, str(viol), multas_str)

    if not inters:
        tbl.add_row("—", "aguardando dados...", "—", "—", "—")

    return tbl


def _build_lpr_push_table(visible: int) -> Table:
    tbl = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold cyan",
                expand=True, padding=(0, 1))
    tbl.add_column("Hora",   style="dim",         no_wrap=True, width=9)
    tbl.add_column("Tipo",   style="bold",         no_wrap=True, width=6)
    tbl.add_column("CRZ",    style="cyan",         no_wrap=True, width=4)
    tbl.add_column("Sensor", style="dim",          no_wrap=True, width=7)
    tbl.add_column("Info",   style="white",        )

    events_data = _read_json(CENTRAL_EVENTS_FILE) or {}
    lpr   = events_data.get("lpr_events",  [])
    push  = events_data.get("push_events", [])

    combined = []
    for e in lpr:
        combined.append(("LPR",  e.get("timestamp",""), e))
    for e in push:
        combined.append(("PUSH", e.get("timestamp",""), e))
    combined.sort(key=lambda x: x[1])

    shown = combined[-visible:]
    for tipo, _, e in reversed(shown):
        ts  = _fmt_ts(e.get("timestamp", ""))
        iid = str(e.get("intersection_id", "—"))
        sid = str(e.get("sensor_id", "—"))
        if tipo == "LPR":
            conf = e.get("confidence", 0)
            conf_s = f"{conf*100:.0f}%" if isinstance(conf, float) else str(conf)
            info = f"{e.get('plate','—')}  conf: {conf_s}"
            color = "yellow"
        else:
            info  = f"{e.get('speed_kmh', 0):.1f} km/h"
            color = "bold magenta"
        tbl.add_row(ts, Text(tipo, style=color), iid, sid, info)

    if not combined:
        tbl.add_row("—", "—", "—", "—", "aguardando eventos...")

    return tbl


def _build_mode_section(visible: int) -> Table:
    events_data = _read_json(CENTRAL_EVENTS_FILE) or {}
    mode_events = events_data.get("mode_events", [])

    tbl = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold cyan",
                expand=True, padding=(0, 1))
    tbl.add_column("Hora",     style="dim",   no_wrap=True, width=9)
    tbl.add_column("Tipo",     no_wrap=True,  width=12)
    tbl.add_column("Estado",   style="white", no_wrap=True, width=10)
    tbl.add_column("Fonte",    style="dim",   no_wrap=True, width=8)
    tbl.add_column("Detalhes", style="dim")

    shown = mode_events[-(visible - 2):]
    for e in reversed(shown):
        ts     = _fmt_ts(e.get("timestamp", ""))
        etype  = e.get("type", "—")
        source = e.get("source", "—")

        if etype == "night_mode":
            estado = "ON" if e.get("enabled") else "OFF"
            color  = "bold magenta" if e.get("enabled") else "dim"
            det    = ""
        else:
            estado = "ATIVA" if e.get("active") else "INATIVA"
            color  = "bold red" if e.get("active") else "dim"
            det_parts = []
            if e.get("road") is not None:
                det_parts.append(f"via:{e['road']}")
            if e.get("signal_group") is not None:
                det_parts.append(f"grp:{e['signal_group']}")
            if e.get("intersection_id") is not None:
                det_parts.append(f"crz:{e['intersection_id']}")
            det = "  ".join(det_parts)

        tbl.add_row(ts, Text(etype, style="bold"), Text(estado, style=color), source, det)

    if not mode_events:
        tbl.add_row("—", "—", "—", "—", "aguardando eventos...")

    return tbl


def _build_mode_title() -> str:
    state    = _read_json(SYSTEM_STATE_FILE) or {}
    night_on = state.get("night_mode",       False)
    emerg_on = state.get("emergency_active", False)
    night_s  = "[bold magenta]SIM[/]" if night_on else "NÃO"
    emerg_s  = "[bold red]ATIVA[/]"   if emerg_on else "NÃO"
    return f"[bold]Noturno & Emergência[/]  Noturno: {night_s}  Emergência: {emerg_s}"


def _build_central_panel():
    inner = Layout()
    inner.split_column(
        Layout(name="tabs",    size=1),
        Layout(name="sections", ratio=1),
    )
    inner["tabs"].update(_build_tabs_header())

    inner["sections"].split_column(
        Layout(name="crz",  ratio=3),
        Layout(name="lpr",  ratio=3),
        Layout(name="modes", ratio=2),
    )

    visible = max(3, console.size.height - 20)
    inner["sections"]["crz"].update(
        Panel(_build_intersection_table(),
              title="[bold]Cruzamentos[/]",
              border_style="cyan", box=box.ROUNDED)
    )
    inner["sections"]["lpr"].update(
        Panel(_build_lpr_push_table(visible),
              title="[bold]LPR & Push[/]",
              border_style="yellow", box=box.ROUNDED)
    )
    inner["sections"]["modes"].update(
        Panel(_build_mode_section(visible),
              title=_build_mode_title(),
              border_style="magenta", box=box.ROUNDED)
    )
    return inner


def _build_dist_messages_table(name: str, visible: int) -> Table:
    tbl = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold cyan",
                expand=True, padding=(0, 1))
    tbl.add_column("Hora",   style="dim",   no_wrap=True, width=9)
    tbl.add_column("Tipo",   no_wrap=True,  width=16)
    tbl.add_column("Sensor", style="dim",   no_wrap=True, width=7)
    tbl.add_column("Valor",  style="white", no_wrap=True)

    data  = _read_json(DIST_EVENTS_FILES[name]) or {}
    msgs  = data.get("messages", [])
    shown = msgs[-visible:]

    TYPE_COLOR = {
        "heartbeat":       "dim",
        "vehicle_count":   "bold green",
        "speed_violation": "bold red",
    }
    for e in reversed(shown):
        ts    = _fmt_ts(e.get("timestamp", ""))
        etype = e.get("type", "—")
        sid   = str(e.get("sensor_id") or "—")
        val   = e.get("value")
        if etype == "speed_violation":
            val_str = f"{val:.1f} km/h" if isinstance(val, (int, float)) else str(val or "—")
        elif etype == "vehicle_count":
            val_str = f"{val} veíc." if val is not None else "—"
        else:
            val_str = "—"
        tbl.add_row(ts, Text(etype, style=TYPE_COLOR.get(etype, "dim")), sid, val_str)

    if not msgs:
        tbl.add_row("—", "aguardando mensagens...", "—", "—")
    return tbl


def _build_dist_commands_table(name: str, visible: int) -> Table:
    tbl = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold cyan",
                expand=True, padding=(0, 1))
    tbl.add_column("Hora",  style="dim",   no_wrap=True, width=9)
    tbl.add_column("Tipo",  no_wrap=True,  width=16)
    tbl.add_column("Dados", style="white", )

    data  = _read_json(DIST_EVENTS_FILES[name]) or {}
    cmds  = data.get("commands", [])
    shown = cmds[-visible:]

    CMD_COLOR = {
        "night_mode":      "magenta",
        "emergency":       "bold red",
        "manual_override": "yellow",
    }
    for e in reversed(shown):
        ts    = _fmt_ts(e.get("timestamp", ""))
        etype = e.get("type", "—")
        d     = e.get("data", {})
        parts = [f"{k}:{v}" for k, v in d.items() if v is not None]
        tbl.add_row(ts, Text(etype, style=CMD_COLOR.get(etype, "dim")), "  ".join(parts) or "—")

    if not cmds:
        tbl.add_row("—", "aguardando comandos...", "—")
    return tbl


def _build_dist_panel(name: str):
    label = "Distribuído 1" if name == "dist1" else "Distribuído 2"
    border = "green" if name == "dist1" else "blue"
    visible = max(3, (console.size.height - 18) // 2)

    inner = Layout()
    inner.split_column(
        Layout(name="tabs",    size=1),
        Layout(name="sections", ratio=1),
    )
    inner["tabs"].update(_build_tabs_header())
    inner["sections"].split_column(
        Layout(name="msgs", ratio=1),
        Layout(name="cmds", ratio=1),
    )
    inner["sections"]["msgs"].update(
        Panel(_build_dist_messages_table(name, visible),
              title=f"[bold]{label} — Mensagens Enviadas[/]",
              border_style=border, box=box.ROUNDED)
    )
    inner["sections"]["cmds"].update(
        Panel(_build_dist_commands_table(name, visible),
              title=f"[bold]{label} — Comandos Recebidos[/]",
              border_style="yellow", box=box.ROUNDED)
    )
    return inner


def _build_log_panel():
    if active_tab == "multas":
        return _build_multas_panel()
    if active_tab == "central":
        return _build_central_panel()
    if active_tab in ("dist1", "dist2"):
        return _build_dist_panel(active_tab)

    # fallback (nunca deve chegar aqui com os tabs atuais)
    visible = _get_visible_lines()
    with lock:
        all_lines = list(log_buffers[active_tab])
    lines = all_lines[-visible:]
    return Panel(
        _build_log_table(lines),
        title=_build_tabs_header(),
        subtitle=Text(f"  {len(all_lines)} linhas  ", style="dim"),
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
        t.append("pronto", style="dim")
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


def _read_key() -> str:
    ch = sys.stdin.read(1)
    if not ch:
        return ""
    if ch == "\x1b":
        if not select.select([sys.stdin], [], [], 0.1)[0]:
            return "esc"
        ch2 = sys.stdin.read(1)
        if ch2 != "[":
            return "esc"
        # drena todos os bytes restantes da sequência antes de retornar
        while select.select([sys.stdin], [], [], 0.05)[0]:
            sys.stdin.read(1)
        return ""
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
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def main():
    running = threading.Event()
    running.set()

    fd = sys.stdin.fileno() if sys.stdin.isatty() else None
    old_term = termios.tcgetattr(fd) if fd is not None else None

    t = threading.Thread(target=_input_thread, args=(running,), daemon=True)
    t.start()

    console.clear()
    try:
        with Live(
            _build_layout(),
            console=console,
            refresh_per_second=int(1 / REFRESH_RATE),
            screen=True,
        ) as live:
            while running.is_set():
                live.update(_build_layout())
                time.sleep(REFRESH_RATE)
    finally:
        running.clear()
        if fd is not None and old_term is not None:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_term)
            except Exception:
                pass

    console.clear()
    console.print("[bold green]Launcher encerrado.[/]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        stop_all()
        console.print("\n[bold red]Interrompido.[/]")
