"""Color palette — bronze automaton."""

from rich.theme import Theme

COLORS = {
    "bronze": "#CD7F32",
    "amber": "#FFBF00",
    "verdigris": "#43B3AE",
    "oxidized": "#C1440E",
    "forge": "#1A1A2E",
    "warm": "#E8E0D4",
    "muted": "#8B7355",
}

THEME = Theme(
    {
        "prompt": f"bold {COLORS['bronze']}",
        "ok": f"bold {COLORS['verdigris']}",
        "err": f"bold {COLORS['oxidized']}",
        "dim": COLORS["muted"],
        "accent": COLORS["amber"],
        "panel": COLORS["bronze"],
    }
)
