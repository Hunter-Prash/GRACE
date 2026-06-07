from PyQt6.QtGui import QColor, QFont
BG          = "#0a0e14"  # Deep cinematic dark blue-black
BG2         = "#0a0e14"
CYAN        = "#00d4ff"
CYAN_DIM    = "rgba(0, 212, 255, 0.15)"
CYAN_MID    = "rgba(0, 212, 255, 0.70)"
GREEN       = "#00ff88"
GREEN_DIM   = "rgba(0, 255, 136, 0.15)"
PINK        = "#ff2d78"
PINK_DIM    = "rgba(255, 45, 120, 0.15)"
AMBER       = "#ffaa00"
TEXT_DIM    = "rgba(0, 212, 255, 0.60)"
BORDER      = "rgba(0, 212, 255, 0.22)"
BORDER_HOT  = "rgba(0, 212, 255, 0.35)"

FONT_MONO   = "Consolas"
FONT_SANS   = "Segoe UI"

def mono(size=11, bold=False):
    f = QFont(FONT_MONO, size)
    f.setBold(bold)
    return f

def sans(size=11, bold=False):
    f = QFont(FONT_SANS, size)
    f.setBold(bold)
    return f

def parse_color(val, alpha=None):
    if val.startswith("#"):
        c = QColor(val)
    elif val.startswith("rgba"):
        parts = val.replace("rgba(", "").replace(")", "").split(",")
        r = int(parts[0].strip())
        g = int(parts[1].strip())
        b = int(parts[2].strip())
        a = int(float(parts[3].strip()) * 255)
        c = QColor(r, g, b, a)
    else:
        c = QColor(val)
    if alpha is not None:
        c.setAlpha(alpha)
    return c
