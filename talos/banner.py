"""Startup banner with Crush-style split layout."""

import asyncio
import subprocess
from pathlib import Path

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from talos.agent import Agent
from talos.config import Config
from talos.theme import THEME, COLORS


console = Console(theme=THEME)

LOGO = r"""
 ╔╦╗╔═╗╦  ╔═╗╔═╗
  ║ ╠═╣║  ║ ║╚═╗
  ╩ ╩ ╩╩═╝╚═╝╚═╝"""


def _bar(pct: float, width: int = 16) -> str:
    """Render a compact progress bar."""
    filled = int(pct / 100 * width)
    empty = width - filled
    return f"[accent]{'━' * filled}[/][dim]{'╌' * empty}[/] {pct:.0f}%"


def _gpu_stats() -> dict:
    """Read GPU stats from rocm-smi."""
    try:
        r = subprocess.run(
            ["rocm-smi", "--showuse", "--showmemuse", "--showtemp", "--json"],
            capture_output=True, text=True, timeout=5,
        )
        import json
        data = json.loads(r.stdout)
        card = data.get("card0", {})
        return {
            "temp": card.get("Temperature (Sensor junction) (C)", "?"),
            "vram_pct": card.get("GPU Memory Allocated (VRAM%)", "?"),
            "gpu_pct": card.get("GPU use (%)", "?"),
        }
    except Exception:
        return {}


async def _fetch_stats(agent: Agent):
    """Fetch all stats concurrently. Returns (health, stats, bench, gpu)."""
    health_coro = agent.health()
    stats_coro = agent.stats()
    bench_coro = agent.bench(tokens=40)
    health, stats, bench = await asyncio.gather(health_coro, stats_coro, bench_coro)
    gpu = _gpu_stats()
    return health, stats, bench, gpu


def _build_stats_panel(config: Config, health: dict, stats: dict, bench: dict, gpu: dict):
    """Build the right-side system stats panel."""
    connected = health.get("status") in ("ok", "healthy")

    tbl = Table(show_header=False, show_edge=False, box=None, padding=(0, 1))
    tbl.add_column("key", style="dim", min_width=10)
    tbl.add_column("val", min_width=30)

    # Connection
    hive_style = "ok" if connected else "err"
    hive_label = "connected" if connected else "down"
    tbl.add_row("hivemind", f"[{hive_style}]{hive_label}[/] [dim]{config.hivemind_url}[/]")

    # Model + tok/sec
    model = stats.get("llm_model", "—")
    llm_status = stats.get("llm_status", "—")
    llm_style = "ok" if llm_status == "online" else "err"
    gen_tok = bench.get("gen_tok_s", 0)
    tok_info = f" [accent]{gen_tok} tok/s[/]" if gen_tok else ""
    tbl.add_row("model", f"[{llm_style}]{model}[/]{tok_info} [dim]{llm_status}[/]")

    # RAG
    rag = stats.get("rag_retrieval", {})
    if rag:
        hit_rate = rag.get("hit_rate", 0) * 100
        total = rag.get("total", 0)
        tbl.add_row("rag", f"{_bar(hit_rate)} [dim]{total} queries[/]")

    # Learning pipeline
    lp = stats.get("learning_pipeline", {})
    if lp:
        progress = lp.get("progress_pct", 0)
        samples = lp.get("filtered_samples", 0)
        threshold = lp.get("threshold", 50)
        tbl.add_row("learning", f"{_bar(progress)} [dim]{samples}/{threshold} samples[/]")
        est = lp.get("est_days_to_training")
        ver = lp.get("model_version", "")
        if est is not None:
            tbl.add_row("", f"[dim]~{est:.1f}d to next train · v{ver}[/]")

    # GPU
    if gpu:
        temp = gpu.get("temp", "?")
        vram = gpu.get("vram_pct", "?")
        gpu_use = gpu.get("gpu_pct", "?")
        try:
            vram_f = float(vram)
            tbl.add_row("gpu", f"{_bar(vram_f, 12)} vram [dim]{temp}°C · {gpu_use}% util[/]")
        except (ValueError, TypeError):
            tbl.add_row("gpu", f"[dim]vram {vram}% · {temp}°C · {gpu_use}% util[/]")

    # Redis
    mem = stats.get("used_memory_human", "")
    sessions = stats.get("total_sessions", 0)
    cluster = stats.get("cluster_mode", False)
    if mem:
        mode = "cluster" if cluster else "standalone"
        tbl.add_row("redis", f"[ok]{mode}[/] [dim]{mem} · {sessions} sessions[/]")

    # Vault
    if config.obsidian_vault:
        vault_exists = Path(config.obsidian_vault).is_dir()
        v_style = "ok" if vault_exists else "err"
        v_label = "found" if vault_exists else "missing"
        tbl.add_row("vault", f"[{v_style}]{v_label}[/] [dim]{config.obsidian_vault}[/]")

    return Panel(
        tbl,
        border_style=COLORS["muted"],
        title="[dim]system[/]",
        title_align="left",
        padding=(0, 1),
    )


def _build_logo_panel():
    """Build the left-side logo panel."""
    from talos import __version__

    logo_text = Text.from_ansi(f"\033[38;2;205;127;50m{LOGO}\033[0m")
    version_line = Text(f"  v{__version__} — the bronze guardian", style="dim")
    left_content = Group(logo_text, version_line)
    return Panel(
        left_content,
        border_style=COLORS["bronze"],
        padding=(0, 1),
        width=30,
    )


def render_full(config: Config, health: dict, stats: dict, bench: dict, gpu: dict):
    """Render the full banner with logo + stats side by side."""
    left_panel = _build_logo_panel()
    right_panel = _build_stats_panel(config, health, stats, bench, gpu)

    layout = Table(show_header=False, show_edge=False, box=None, padding=0, expand=True)
    layout.add_column(width=32)
    layout.add_column(ratio=1)
    layout.add_row(left_panel, right_panel)

    console.clear()
    console.print()
    console.print(layout)
    console.print(
        f"  [dim]arrows/history · tab-complete · !cmd for shell "
        f"· ctrl-r search · F2 toggle stats[/]\n"
    )


def render_minimal():
    """Render the minimal banner — logo only, no stats panel."""
    from talos import __version__

    console.clear()
    console.print()
    console.print(f"  [prompt]⚙ talos {__version__}[/] [dim]— the bronze guardian[/]")
    console.print(
        f"  [dim]arrows/history · tab-complete · !cmd for shell "
        f"· ctrl-r search · F2 toggle stats[/]\n"
    )


async def show(config: Config, agent: Agent) -> tuple[dict, dict, dict, dict]:
    """Clear screen, display the full startup banner. Returns cached stats."""
    health, stats, bench, gpu = await _fetch_stats(agent)
    render_full(config, health, stats, bench, gpu)
    return health, stats, bench, gpu


async def refresh(config: Config, agent: Agent):
    """Re-fetch stats and redraw the full banner."""
    health, stats, bench, gpu = await _fetch_stats(agent)
    render_full(config, health, stats, bench, gpu)
    return health, stats, bench, gpu
