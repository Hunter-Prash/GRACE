import sys
import time
import math
import psutil
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QScrollArea, QFrame, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient

# ──────────────────────────────────────────
# THEME CONSTANTS & COLORS
# ──────────────────────────────────────────
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

FONT_MONO   = "Courier New"

def mono(size=11, bold=False):
    f = QFont(FONT_MONO, size)
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

# ──────────────────────────────────────────
# GLOW LABEL
# ──────────────────────────────────────────
class GlowLabel(QLabel):
    def __init__(self, text="", color=CYAN, size=11, bold=False, parent=None):
        super().__init__(text, parent)
        self.glow_color = color
        self.setFont(mono(size, bold))
        self.setStyleSheet(f"color: {color}; background: transparent; border: none;")

# ──────────────────────────────────────────
# CYBER PANEL (bordered box with corner cuts)
# ──────────────────────────────────────────
class CyberPanel(QFrame):
    def __init__(self, label="", glow=CYAN, parent=None):
        super().__init__(parent)
        self.label = label
        self.glow  = glow
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Shift border down by 8px to leave space for label rendering at the top
        r = self.rect().adjusted(1, 8, -1, -1)
        
        # 1. Panel background
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(parse_color(BG2))
        p.drawRoundedRect(r, 6, 6)
        
        # 2. Panel border
        c_border = parse_color(self.glow, 34)  # ~ #00d4ff22
        p.setPen(QPen(c_border, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r, 6, 6)
        
        # 3. Corner brackets decoration
        c_glow = parse_color(self.glow, 120)
        p.setPen(QPen(c_glow, 1))
        cs = 8  # length of bracket
        offset = 4
        
        # Top-Left
        p.drawLine(r.left() + offset, r.top() + offset, r.left() + offset + cs, r.top() + offset)
        p.drawLine(r.left() + offset, r.top() + offset, r.left() + offset, r.top() + offset + cs)
        # Top-Right
        p.drawLine(r.right() - offset, r.top() + offset, r.right() - offset - cs, r.top() + offset)
        p.drawLine(r.right() - offset, r.top() + offset, r.right() - offset, r.top() + offset + cs)
        # Bottom-Left
        p.drawLine(r.left() + offset, r.bottom() - offset, r.left() + offset + cs, r.bottom() - offset)
        p.drawLine(r.left() + offset, r.bottom() - offset, r.left() + offset, r.bottom() - offset - cs)
        # Bottom-Right
        p.drawLine(r.right() - offset, r.bottom() - offset, r.right() - offset - cs, r.bottom() - offset)
        p.drawLine(r.right() - offset, r.bottom() - offset, r.right() - offset, r.bottom() - offset - cs)

        # 4. Label text header
        if self.label:
            p.setFont(mono(8, True))
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(self.label)
            th = fm.height()
            
            # Clear space on top border (center it vertically on r.top())
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(parse_color(BG2))
            p.drawRect(14, r.top() - th // 2, tw + 10, th)
            
            # Draw label centered vertically on r.top() with high intensity
            c_text = parse_color(self.glow, 220)
            p.setPen(QPen(c_text))
            p.drawText(19, r.top() - th // 2 + fm.ascent(), self.label)

# ──────────────────────────────────────────
# STAT BAR
# ──────────────────────────────────────────
class StatBar(QWidget):
    def __init__(self, label, color=CYAN, parent=None):
        super().__init__(parent)
        self.label = label
        self.color = color
        self._value = 0
        self.setFixedHeight(22)

    def setValue(self, v):
        self._value = max(0, min(100, v))
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        
        # 1. Label on left - widened to 42px to prevent clipping
        p.setFont(mono(9))
        p.setPen(parse_color(self.color, 180))
        p.drawText(0, 0, 42, h, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.label)
        
        # 2. Progress Bar Track & Fill
        tx = 44
        tw = w - tx - 44
        
        p.setPen(Qt.PenStyle.NoPen)
        c_track = parse_color(self.color, 24)  # faint transparent track background
        p.setBrush(c_track)
        p.drawRoundedRect(tx, h // 2 - 2, tw, 4, 2, 2)
        
        fill_w = int(tw * self._value / 100)
        if fill_w > 0:
            p.setBrush(parse_color(self.color))
            p.drawRoundedRect(tx, h // 2 - 2, fill_w, 4, 2, 2)
            
        # 3. Value on right
        p.setFont(mono(9, True))
        p.setPen(parse_color(self.color))
        p.drawText(w - 38, 0, 38, h, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, f"{int(self._value)}%")

# ──────────────────────────────────────────
# AUDIO MONITOR (Mic Level Visualizer)
# ──────────────────────────────────────────
class AudioMonitorWidget(QWidget):
    def __init__(self, color=CYAN, parent=None):
        super().__init__(parent)
        self.color = color
        self.bars = [0.1] * 8
        self.setFixedHeight(50)

    def update_bars(self, bars):
        if len(bars) >= 8:
            step = len(bars) / 8
            self.bars = [bars[int(i * step)] for i in range(8)]
        else:
            self.bars = bars + [0.1] * (8 - len(bars))
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        n = len(self.bars)
        
        bw = 6  # bar width
        gap = 4 # gap between bars
        total_w = n * bw + (n - 1) * gap
        start_x = (w - total_w) // 2
        
        for i, v in enumerate(self.bars):
            x = start_x + i * (bw + gap)
            bh = max(4, int(v * (h - 8)))
            y = h - bh - 2
            
            c = parse_color(self.color, int(70 + v * 150))
            p.setBrush(c)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x, y, bw, bh, 2, 2)

# ──────────────────────────────────────────
# SMALL WAVEFORM WIDGET (Chat Bottom Visualizer)
# ──────────────────────────────────────────
class SmallWaveformWidget(QWidget):
    def __init__(self, color=CYAN, parent=None):
        super().__init__(parent)
        self.color = color
        self.bars = [0.1] * 5
        self.setFixedSize(30, 16)
        
    def update_bars(self, bars):
        if len(bars) >= 5:
            step = len(bars) / 5
            self.bars = [bars[int(i * step)] for i in range(5)]
        else:
            self.bars = bars + [0.1] * (5 - len(bars))
        self.update()
        
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        n = len(self.bars)
        
        bw = 3  # bar width
        gap = 2 # gap
        total_w = n * bw + (n - 1) * gap
        start_x = (w - total_w) // 2
        
        for i, v in enumerate(self.bars):
            x = start_x + i * (bw + gap)
            bh = max(3, int(v * h))
            y = (h - bh) // 2
            
            c = parse_color(self.color, int(80 + v * 175))
            p.setBrush(c)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x, y, bw, bh, 1.5, 1.5)

# ──────────────────────────────────────────
# STATE INDICATOR
# ──────────────────────────────────────────
class StateIndicator(QWidget):
    STATES = {
        "IDLE":       (GREEN, "IDLE"),
        "LISTENING":  (CYAN,  "LISTENING"),
        "PROCESSING": (AMBER, "PROCESSING"),
        "SPEAKING":   (PINK,  "SPEAKING"),
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "IDLE"
        self.setFixedHeight(30)
        
    def set_state(self, s):
        self._state = s
        self.update()
        
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color, text = self.STATES.get(self._state, (GREEN, self._state))
        w, h = self.width(), self.height()
        
        p.setFont(mono(10, True))
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(text)
        th = fm.height()
        
        total_w = 8 + 8 + tw
        start_x = (w - total_w) // 2
        
        p.setPen(Qt.PenStyle.NoPen)
        c_glow = parse_color(color, 100)
        p.setBrush(c_glow)
        p.drawEllipse(start_x - 1, h // 2 - 5, 10, 10)
        
        p.setBrush(parse_color(color))
        p.drawEllipse(start_x, h // 2 - 4, 8, 8)
        
        p.setPen(parse_color(color))
        p.drawText(start_x + 16, (h - th) // 2 + fm.ascent(), text)

# ──────────────────────────────────────────
# STATUS RING (Concentric Animated HUD Circle)
# ──────────────────────────────────────────
class StatusRing(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "IDLE"
        self.setFixedSize(72, 72)
        self._angle = 0
        
        # Rotating dot timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._rotate)
        self.timer.start(30)
        
    def set_state(self, state):
        self._state = state
        self.update()
        
    def _rotate(self):
        self._angle = (self._angle + 2) % 360
        self.update()
        
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color_str = CYAN if self._state in ["LISTENING", "IDLE"] else (AMBER if self._state == "PROCESSING" else PINK)
        color = parse_color(color_str)
        
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        
        r_outer = 28
        r_inner = 20
        
        # Outer ring
        p.setPen(QPen(parse_color(CYAN_DIM), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(cx - r_outer, cy - r_outer, r_outer * 2, r_outer * 2)
        
        # Inner ring
        p.setPen(QPen(parse_color(BORDER), 1))
        p.drawEllipse(cx - r_inner, cy - r_inner, r_inner * 2, r_inner * 2)
        
        # Center Text "GRACE"
        p.setPen(parse_color(TEXT_DIM))
        p.setFont(mono(8, True))
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance("GRACE")
        th = fm.height()
        p.drawText(cx - tw // 2, cy + th // 2 - fm.descent() - 2, "GRACE")
        
        # Revolving dot on outer ring
        rad = math.radians(self._angle)
        dot_x = cx + r_outer * math.cos(rad)
        dot_y = cy + r_outer * math.sin(rad)
        
        p.setPen(Qt.PenStyle.NoPen)
        c_glow = parse_color(color_str, 100)
        p.setBrush(c_glow)
        p.drawEllipse(int(dot_x - 4), int(dot_y - 4), 8, 8)
        
        p.setBrush(color)
        p.drawEllipse(int(dot_x - 3), int(dot_y - 3), 6, 6)

# ──────────────────────────────────────────
# CHAT BUBBLE
# ──────────────────────────────────────────
class ChatBubble(QFrame):
    def __init__(self, speaker, text, parent=None):
        super().__init__(parent)
        is_user = speaker == "YOU"
        
        if is_user:
            color = CYAN
            bg = "rgba(0, 212, 255, 0.07)"
            border_color = "rgba(0, 212, 255, 0.2)"
            text_color = "rgba(0, 212, 255, 0.85)"
            who_color = "rgba(0, 212, 255, 0.5)"
        else:
            color = GREEN
            bg = "rgba(0, 255, 136, 0.05)"
            border_color = "rgba(0, 255, 136, 0.15)"
            text_color = "rgba(0, 255, 136, 0.85)"
            who_color = "rgba(0, 255, 136, 0.5)"
        
        self.setMaximumWidth(600)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        
        self.setStyleSheet(f"""
            QFrame {{
                background: {bg};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
        """)
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(4)
        
        lbl_who = QLabel(speaker)
        lbl_who.setFont(mono(8, True))
        lbl_who.setStyleSheet(f"color: {who_color}; background: transparent; border: none; letter-spacing: 2px;")
        
        lbl_txt = QLabel(text)
        lbl_txt.setFont(mono(9))
        lbl_txt.setStyleSheet(f"color: {text_color}; background: transparent; border: none; line-height: 1.4;")
        lbl_txt.setWordWrap(True)
        lbl_txt.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        lay.addWidget(lbl_who)
        lay.addWidget(lbl_txt)

# ──────────────────────────────────────────
# CYBER BUTTON
# ──────────────────────────────────────────
class CyberButton(QPushButton):
    def __init__(self, text, color=CYAN, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.setFont(mono(9, True))
        self.setFixedHeight(30)
        
        border_color = "rgba(0, 212, 255, 0.2)" if color == CYAN else "rgba(255, 45, 120, 0.2)"
        hover_bg = "rgba(0, 212, 255, 0.1)" if color == CYAN else "rgba(255, 45, 120, 0.1)"
        
        self.setStyleSheet(f"""
            QPushButton {{
                color: {color};
                background: transparent;
                border: 1px solid {border_color};
                border-radius: 4px;
                letter-spacing: 2px;
            }}
            QPushButton:hover {{
                color: {color};
                background: {hover_bg};
                border: 1px solid {color};
            }}
            QPushButton:pressed {{
                background: rgba(255, 255, 255, 0.1);
            }}
        """)

# ──────────────────────────────────────────
# MAIN HUD WINDOW
# ──────────────────────────────────────────
class GraceHUD(QMainWindow):
    sig_state   = pyqtSignal(str)
    sig_message = pyqtSignal(str, str)
    sig_wave    = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GRACE // CORE HUD")
        self.setMinimumSize(1100, 660)
        self.session_start = time.time()
        self.query_count   = 0

        self.setStyleSheet(f"""
            QMainWindow, QWidget#central_widget {{
                background: {BG};
            }}
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 4px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(0, 212, 255, 0.14);
                border-radius: 2px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(0, 212, 255, 0.27);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                border: none;
                background: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)

        self._build_ui()
        self._connect_signals()
        self._start_timers()

    # ── UI BUILD ──────────────────────────
    def _build_ui(self):
        root = QWidget()
        root.setObjectName("central_widget")
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(8)

        main.addWidget(self._topbar())

        body = QHBoxLayout()
        body.setSpacing(10)
        body.addWidget(self._left_panel(),  0)
        body.addWidget(self._center_panel(), 1)
        body.addWidget(self._right_panel(), 0)
        main.addLayout(body, 1)

        main.addWidget(self._bottombar())

    def _topbar(self):
        bar = QWidget()
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 4, 10, 6)

        # Left Logo "G R A C E"
        logo_lay = QHBoxLayout()
        logo_lay.setSpacing(2)
        logo_g = GlowLabel("G R ", CYAN, 18, True)
        logo_a = GlowLabel("A ", GREEN, 18, True)
        logo_ce = GlowLabel("C E", CYAN, 18, True)
        logo_lay.addWidget(logo_g)
        logo_lay.addWidget(logo_a)
        logo_lay.addWidget(logo_ce)
        lay.addLayout(logo_lay)

        lay.addStretch()

        # Center Status Info
        self.lbl_status = GlowLabel("SYSTEM v1.0  |  ONLINE  |  00:00:00", TEXT_DIM, 9)
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.lbl_status)

        lay.addStretch()

        # Right Indicator Dots
        lights = QWidget()
        lights_lay = QHBoxLayout(lights)
        lights_lay.setContentsMargins(10, 0, 0, 0)
        lights_lay.setSpacing(6)
        
        for i, color in enumerate([GREEN, CYAN, CYAN]):
            dot = QLabel()
            shade = color if i == 0 else "#00d4ff33"
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background: {shade}; border-radius: 4px;")
            lights_lay.addWidget(dot)
            
        lay.addWidget(lights)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {BORDER};")

        wrap = QVBoxLayout()
        wrap.setContentsMargins(0, 0, 0, 0)
        wrap.setSpacing(4)
        wrap.addWidget(bar)
        wrap.addWidget(div)

        w = QWidget()
        w.setLayout(wrap)
        return w

    def _left_panel(self):
        w = QWidget()
        w.setFixedWidth(190)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        # Stats Panel
        stats = CyberPanel("◈ SYSTEM STATS")
        sl = QVBoxLayout(stats)
        sl.setContentsMargins(12, 16, 12, 12)
        sl.setSpacing(4)
        self.bar_cpu  = StatBar("CPU", CYAN)
        self.bar_ram  = StatBar("RAM", CYAN)
        self.bar_gpu  = StatBar("GPU", GREEN)
        self.bar_vram = StatBar("VRAM", GREEN)
        for b in [self.bar_cpu, self.bar_ram, self.bar_gpu, self.bar_vram]:
            sl.addWidget(b)
        lay.addWidget(stats)

        # Pipeline State Panel
        sp_panel = CyberPanel("◈ PIPELINE STATE")
        sp = QVBoxLayout(sp_panel)
        sp.setContentsMargins(12, 16, 12, 12)
        sp.setSpacing(8)
        self.state_ind = StateIndicator()
        sp.addWidget(self.state_ind)
        self.state_ring = StatusRing()
        sp.addWidget(self.state_ring, 0, Qt.AlignmentFlag.AlignHCenter)
        
        hint = GlowLabel('SAY "HEY MYCROFT"', TEXT_DIM, 8)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sp.addWidget(hint)
        lay.addWidget(sp_panel)

        lay.addStretch()
        return w

    def _center_panel(self):
        panel = CyberPanel("◈ CONVERSATION LOG", CYAN)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(12, 16, 12, 12)
        lay.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_layout.setSpacing(8)
        self.chat_layout.addStretch()
        
        scroll.setWidget(self.chat_container)
        self.scroll_area = scroll
        lay.addWidget(scroll, 1)

        # Bottom Awaiting Input Separator & Layout
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {BORDER};")
        lay.addWidget(div)

        bottom_row = QWidget()
        bottom_lay = QHBoxLayout(bottom_row)
        bottom_lay.setContentsMargins(4, 2, 4, 2)
        bottom_lay.setSpacing(8)
        
        self.lbl_input_state = GlowLabel("AWAITING INPUT...", TEXT_DIM, 8)
        bottom_lay.addWidget(self.lbl_input_state)
        
        self.small_wave = SmallWaveformWidget(CYAN)
        bottom_lay.addWidget(self.small_wave)
        
        bottom_lay.addStretch()
        lay.addWidget(bottom_row)

        return panel

    def _right_panel(self):
        w = QWidget()
        w.setFixedWidth(190)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        # Session Info Panel
        sess = CyberPanel("◈ SESSION INFO")
        sl = QVBoxLayout(sess)
        sl.setContentsMargins(12, 16, 12, 12)
        sl.setSpacing(6)

        def row(lbl, val, color=CYAN):
            r = QHBoxLayout()
            r.setContentsMargins(0, 0, 0, 0)
            l = GlowLabel(lbl, CYAN_MID, 9)
            v = GlowLabel(val, color, 9, True)
            v.setAlignment(Qt.AlignmentFlag.AlignRight)
            r.addWidget(l)
            r.addWidget(v, 1)
            return r, v

        r, self.lbl_uptime  = row("UPTIME",   "00:00:00")
        sl.addLayout(r)
        r, self.lbl_queries = row("QUERIES",  "0")
        sl.addLayout(r)
        r, _ = row("MODEL",   "2.5-FLASH", CYAN_MID)
        sl.addLayout(r)
        r, _ = row("TTS",     "EDGE-TTS", GREEN)
        sl.addLayout(r)
        lay.addWidget(sess)

        # Audio Monitor Panel (Vertical visualizer)
        audio_panel = CyberPanel("◈ AUDIO MONITOR")
        al = QVBoxLayout(audio_panel)
        al.setContentsMargins(12, 16, 12, 12)
        al.setSpacing(4)
        
        self.audio_monitor = AudioMonitorWidget(CYAN)
        al.addWidget(self.audio_monitor)
        
        lbl_mic = GlowLabel("MIC LEVEL", TEXT_DIM, 8)
        lbl_mic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        al.addWidget(lbl_mic)
        
        lay.addWidget(audio_panel)

        # Quick Actions Panel (with distinct Pink/Red neon styling)
        actions = CyberPanel("◈ QUICK ACTIONS", PINK)
        ac_lay = QVBoxLayout(actions)
        ac_lay.setContentsMargins(12, 16, 12, 12)
        ac_lay.setSpacing(6)
        
        self.btn_sleep    = CyberButton("SLEEP", CYAN)
        self.btn_shutdown = CyberButton("SHUTDOWN", PINK)
        ac_lay.addWidget(self.btn_sleep)
        ac_lay.addWidget(self.btn_shutdown)
        lay.addWidget(actions)

        lay.addStretch()
        return w

    def _bottombar(self):
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {BORDER};")

        bar = QWidget()
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 4, 10, 4)

        left = GlowLabel("WHISPER: BASE.EN  |  OWW: HEY_MYCROFT  |  GPU: RTX 3050", TEXT_DIM, 8)
        right = GlowLabel("CHENNAI, IN  |  GRACE CORE PIPELINE", TEXT_DIM, 8)
        right.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        lay.addWidget(left)
        lay.addWidget(right)

        wrap = QVBoxLayout()
        wrap.setContentsMargins(0, 0, 0, 0)
        wrap.setSpacing(4)
        wrap.addWidget(div)
        wrap.addWidget(bar)
        
        w = QWidget()
        w.setLayout(wrap)
        return w

    # ── SIGNALS & TIMERS ──────────────────
    def _connect_signals(self):
        self.sig_state.connect(self._on_state)
        self.sig_message.connect(self._on_message)
        self.sig_wave.connect(self.audio_monitor.update_bars)
        self.sig_wave.connect(self.small_wave.update_bars)
        self.btn_shutdown.clicked.connect(self.close)

    def _start_timers(self):
        self.timer_clock = QTimer()
        self.timer_clock.timeout.connect(self._tick_clock)
        self.timer_clock.start(1000)

        self.timer_stats = QTimer()
        self.timer_stats.timeout.connect(self._tick_stats)
        self.timer_stats.start(2000)
        self._tick_stats()

        self._wave_phase = 0
        self.timer_wave = QTimer()
        self.timer_wave.timeout.connect(self._tick_wave)
        self.timer_wave.start(80)

    # ── TICK HANDLERS ─────────────────────
    def _tick_clock(self):
        self.lbl_status.setText(f"SYSTEM v1.0  |  ONLINE  |  {time.strftime('%H:%M:%S')}")
        elapsed = int(time.time() - self.session_start)
        h, r = divmod(elapsed, 3600)
        m, s = divmod(r, 60)
        self.lbl_uptime.setText(f"{h:02d}:{m:02d}:{s:02d}")

    def _tick_stats(self):
        self.bar_cpu.setValue(psutil.cpu_percent())
        self.bar_ram.setValue(psutil.virtual_memory().percent)
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                self.bar_gpu.setValue(gpus[0].load * 100)
                self.bar_vram.setValue(gpus[0].memoryUtil * 100)
        except Exception:
            pass

    def _tick_wave(self):
        self._wave_phase += 0.3
        bars = [
            max(0.05, abs(math.sin(self._wave_phase + i * 0.7)) * 0.35)
            for i in range(20)
        ]
        self.audio_monitor.update_bars(bars)
        self.small_wave.update_bars(bars)

    # ── PUBLIC API (state and pipeline) ───
    def _on_state(self, state: str):
        self.state_ind.set_state(state)
        self.state_ring.set_state(state)
        
        if state == "IDLE":
            self.lbl_input_state.setText("AWAITING INPUT...")
            self.lbl_input_state.setStyleSheet(f"color: {TEXT_DIM}; background: transparent;")
        elif state == "LISTENING":
            self.lbl_input_state.setText("LISTENING...")
            self.lbl_input_state.setStyleSheet(f"color: {GREEN}; background: transparent;")
        elif state == "PROCESSING":
            self.lbl_input_state.setText("THINKING...")
            self.lbl_input_state.setStyleSheet(f"color: {AMBER}; background: transparent;")
        elif state == "SPEAKING":
            self.lbl_input_state.setText("SPEAKING...")
            self.lbl_input_state.setStyleSheet(f"color: {PINK}; background: transparent;")
            
        self.timer_wave.setInterval(50 if state == "LISTENING" else 40 if state == "SPEAKING" else 80)

    def _on_message(self, speaker: str, text: str):
        bubble = ChatBubble(speaker, text)
        
        # Row container to handle left/right bubble alignments
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_lay = QHBoxLayout(row)
        row_lay.setContentsMargins(0, 4, 0, 4)
        row_lay.setSpacing(0)
        
        if speaker == "YOU":
            row_lay.addStretch(1)
            row_lay.addWidget(bubble)
        else:
            row_lay.addWidget(bubble)
            row_lay.addStretch(1)
            
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, row)
        
        if speaker == "YOU":
            self.query_count += 1
            self.lbl_queries.setText(str(self.query_count))
            
        QTimer.singleShot(50, self._scroll_bottom)

    def _scroll_bottom(self):
        sb = self.scroll_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ── THREAD-SAFE SETTERS ───────────────
    def set_state(self, state: str):
        self.sig_state.emit(state)

    def add_message(self, speaker: str, text: str):
        self.sig_message.emit(speaker, text)

    def set_waveform(self, bars: list):
        self.sig_wave.emit(bars)


# ──────────────────────────────────────────
# STANDALONE DEMO RUN
# ──────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    hud = GraceHUD()
    hud.show()

    # Demo message timers to preview HUD UI
    QTimer.singleShot(800,  lambda: hud.add_message("YOU",   "What is the difference between the Earth and the Sun?"))
    QTimer.singleShot(1600, lambda: hud.set_state("PROCESSING"))
    QTimer.singleShot(2800, lambda: hud.add_message("GRACE", "The Earth is a planet, while the Sun is a star. The Earth orbits the Sun, and the Sun is much, much larger and hotter than the Earth."))
    QTimer.singleShot(2900, lambda: hud.set_state("SPEAKING"))
    QTimer.singleShot(5800, lambda: hud.set_state("IDLE"))
    QTimer.singleShot(6300, lambda: hud.add_message("YOU",   "And the Moon?"))
    QTimer.singleShot(7200, lambda: hud.add_message("GRACE", "The Moon is Earth's natural satellite — much smaller, has no atmosphere, and orbits us roughly every 27 days."))

    sys.exit(app.exec())