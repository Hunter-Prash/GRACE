import os
import math
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QPropertyAnimation, QEasingCurve, QRectF, QRect, QPoint
from PyQt6.QtWidgets import QLabel, QFrame, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy, QGraphicsOpacityEffect, QStackedWidget, QDialog
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QConicalGradient, QRadialGradient
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineSettings
except ImportError:
    QWebEngineView = None

from gui.theme import CYAN, GREEN, PINK, AMBER, BG2, TEXT_DIM, BORDER, CYAN_DIM, CYAN_MID, mono, parse_color, sans

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
        
        self._phase = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(50)
        
    def _tick(self):
        self._phase = (self._phase + 0.05) % (2 * math.pi)
        self.update()

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
        pulse = (math.sin(self._phase) + 1) / 2
        c_glow = parse_color(self.glow, int(60 + pulse * 140))
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
# PULSING DOT (Topbar / Status Indicator)
# ──────────────────────────────────────────
class PulsingDot(QWidget):
    """A small dot that pulses with a soft breathing glow animation."""
    def __init__(self, color=GREEN, size=8, parent=None):
        super().__init__(parent)
        self.color_str = color
        self.dot_size  = size
        self.setFixedSize(size + 6, size + 6)
        self._phase = 0.0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(40)  # ~25fps

    def _tick(self):
        self._phase = (self._phase + 0.12) % (2 * math.pi)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = self.width() // 2
        cy = self.height() // 2
        ds = self.dot_size

        pulse = (math.sin(self._phase) + 1) / 2   # 0..1
        # Outer glow halo
        halo_r = int(ds // 2 + 3 + pulse * 3)
        halo_alpha = int(20 + pulse * 60)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(parse_color(self.color_str, halo_alpha))
        p.drawEllipse(cx - halo_r, cy - halo_r, halo_r * 2, halo_r * 2)

        # Solid core dot
        core_alpha = int(160 + pulse * 95)
        p.setBrush(parse_color(self.color_str, core_alpha))
        p.drawEllipse(cx - ds // 2, cy - ds // 2, ds, ds)

# ──────────────────────────────────────────
# STAT BAR (with shimmer scan animation)
# ──────────────────────────────────────────
class StatBar(QWidget):
    def __init__(self, label, color=CYAN, parent=None):
        super().__init__(parent)
        self.label = label
        self.color = color
        self._value = 0
        self._scan_pos = 0.0   # 0..1, shimmer position
        self.setFixedHeight(22)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(50)

    def _tick(self):
        self._scan_pos = (self._scan_pos + 0.025) % 1.0
        self.update()

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
        c_track = parse_color(self.color, 24)
        p.setBrush(c_track)
        p.drawRoundedRect(tx, h // 2 - 2, tw, 4, 2, 2)
        
        fill_w = int(tw * self._value / 100)
        if fill_w > 0:
            p.setBrush(parse_color(self.color))
            p.drawRoundedRect(tx, h // 2 - 2, fill_w, 4, 2, 2)

            # Shimmer scan highlight within filled area
            scan_x = tx + int(fill_w * self._scan_pos)
            shimmer_w = max(6, fill_w // 4)
            # Clamp shimmer to filled region
            scan_x = min(scan_x, tx + fill_w - 2)
            shim_start = max(tx, scan_x - shimmer_w // 2)
            shim_end   = min(tx + fill_w, scan_x + shimmer_w // 2)
            if shim_end > shim_start:
                p.setBrush(parse_color(self.color, 90))
                p.drawRoundedRect(shim_start, h // 2 - 3, shim_end - shim_start, 6, 2, 2)
            
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
# STATE INDICATOR (with breathing pulse dot)
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
        self._pulse = 0.0
        self.setFixedHeight(30)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(40)

    def _tick(self):
        # Speed up pulse for active states
        speed = 0.18 if self._state in ("LISTENING", "PROCESSING", "SPEAKING") else 0.08
        self._pulse = (self._pulse + speed) % (2 * math.pi)
        self.update()
        
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

        pulse = (math.sin(self._pulse) + 1) / 2   # 0..1

        # Outer breathing halo
        halo_r = int(7 + pulse * 4)
        halo_alpha = int(30 + pulse * 80)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(parse_color(color, halo_alpha))
        cx_dot = start_x + 4
        cy_dot = h // 2
        p.drawEllipse(cx_dot - halo_r + 4, cy_dot - halo_r, halo_r * 2, halo_r * 2)

        # Middle glow ring
        p.setBrush(parse_color(color, int(60 + pulse * 60)))
        p.drawEllipse(start_x - 1, h // 2 - 5, 10, 10)
        
        # Solid core dot
        p.setBrush(parse_color(color, int(180 + pulse * 75)))
        p.drawEllipse(start_x, h // 2 - 4, 8, 8)
        
        # State text
        p.setPen(parse_color(color))
        p.drawText(start_x + 16, (h - th) // 2 + fm.ascent(), text)

# ──────────────────────────────────────────
# STATUS RING (Dual orbit dots + arc sweep)
# ──────────────────────────────────────────
class StatusRing(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "IDLE"
        self.setFixedSize(80, 80)
        self._angle  = 0      # primary dot angle
        self._angle2 = 180    # secondary dot (counter-rotating)
        self._arc_span = 0    # animated arc span
        self._arc_growing = True
        
        # Rotating dot timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._rotate)
        self.timer.start(28)
        
    def set_state(self, state):
        self._state = state
        self.update()
        
    def _rotate(self):
        speed = 3 if self._state == "PROCESSING" else 2 if self._state in ("LISTENING", "SPEAKING") else 1
        self._angle  = (self._angle  + speed) % 360
        self._angle2 = (self._angle2 - speed) % 360  # counter-rotate

        # Arc breathes in/out
        arc_speed = 3 if self._state == "PROCESSING" else 2
        if self._arc_growing:
            self._arc_span += arc_speed
            if self._arc_span >= 120:
                self._arc_growing = False
        else:
            self._arc_span -= arc_speed
            if self._arc_span <= 20:
                self._arc_growing = True

        self.update()
        
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color_str = (
            CYAN  if self._state in ("LISTENING", "IDLE") else
            AMBER if self._state == "PROCESSING" else
            PINK
        )
        color = parse_color(color_str)
        
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        
        r_outer  = 32
        r_mid    = 24
        r_inner  = 16

        # ── Outermost dim ring ──────────────────
        p.setPen(QPen(parse_color(CYAN_DIM, 60), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(cx - r_outer, cy - r_outer, r_outer * 2, r_outer * 2)

        # ── Animated glowing arc on outer ring ─
        arc_pen = QPen(parse_color(color_str, 140), 2)
        arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(arc_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        arc_rect = QRectF(cx - r_outer, cy - r_outer, r_outer * 2, r_outer * 2)
        # Qt arc: start & span in 1/16ths of a degree
        arc_start = int((self._angle - self._arc_span // 2) * 16)
        p.drawArc(arc_rect, arc_start, int(self._arc_span * 16))

        # ── Mid ring ────────────────────────────
        p.setPen(QPen(parse_color(BORDER, 80), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(cx - r_mid, cy - r_mid, r_mid * 2, r_mid * 2)

        # ── Inner ring (tiny tick marks) ────────
        p.setPen(QPen(parse_color(color_str, 45), 1))
        p.drawEllipse(cx - r_inner, cy - r_inner, r_inner * 2, r_inner * 2)

        # Tick marks on inner ring (4 cardinal points)
        for deg in (0, 90, 180, 270):
            rad = math.radians(deg)
            x1 = cx + (r_inner - 2) * math.cos(rad)
            y1 = cy + (r_inner - 2) * math.sin(rad)
            x2 = cx + (r_inner + 3) * math.cos(rad)
            y2 = cy + (r_inner + 3) * math.sin(rad)
            p.setPen(QPen(parse_color(color_str, 90), 1))
            p.drawLine(int(x1), int(y1), int(x2), int(y2))

        # ── Center Text "GRACE" ──────────────────
        p.setPen(parse_color(TEXT_DIM))
        p.setFont(mono(8, True))
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance("GRACE")
        th = fm.height()
        p.drawText(cx - tw // 2, cy + th // 2 - fm.descent() - 2, "GRACE")
        
        # ── Primary revolving dot (outer ring) ──
        rad = math.radians(self._angle)
        dot_x = cx + r_outer * math.cos(rad)
        dot_y = cy + r_outer * math.sin(rad)

        p.setPen(Qt.PenStyle.NoPen)
        # Glow halo
        p.setBrush(parse_color(color_str, 70))
        p.drawEllipse(int(dot_x - 5), int(dot_y - 5), 10, 10)
        # Bright core
        p.setBrush(color)
        p.drawEllipse(int(dot_x - 3), int(dot_y - 3), 6, 6)

        # ── Secondary counter-rotating dot (mid ring) ──
        rad2 = math.radians(self._angle2)
        dot2_x = cx + r_mid * math.cos(rad2)
        dot2_y = cy + r_mid * math.sin(rad2)

        p.setBrush(parse_color(color_str, 55))
        p.drawEllipse(int(dot2_x - 4), int(dot2_y - 4), 8, 8)
        p.setBrush(parse_color(color_str, 160))
        p.drawEllipse(int(dot2_x - 2), int(dot2_y - 2), 4, 4)

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
        
        self.setMinimumWidth(450)
        self.setMaximumWidth(680)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        self.setStyleSheet(f"""
            QFrame {{
                background: {bg};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
        """)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(10, 8, 10, 8)
        self.lay.setSpacing(4)
        
        lbl_who = QLabel(speaker)
        lbl_who.setFont(mono(8, True))
        lbl_who.setStyleSheet(f"color: {who_color}; background: transparent; border: none; letter-spacing: 2px;")
        
        lbl_txt = QLabel(text)
        lbl_txt.setFont(sans(10))
        lbl_txt.setStyleSheet(f"color: {text_color}; background: transparent; border: none; line-height: 1.5; padding: 2px;")
        lbl_txt.setWordWrap(True)
        lbl_txt.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        self.lay.addWidget(lbl_who)
        self.lay.addWidget(lbl_txt)
        
        self.color = color
        
        # --- FADE IN ANIMATION ---
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(400)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.fade_anim.start()
        
        # --- TYPING EFFECT ---
        self.full_text = text
        self.lbl_txt = lbl_txt
        if not is_user:
            self.lbl_txt.setText("")
            self.type_idx = 0
            self.type_timer = QTimer(self)
            self.type_timer.timeout.connect(self._type_next_char)
            self.type_timer.start(10)  # Type very fast (10ms per loop)
            
    def _type_next_char(self):
        if self.type_idx < len(self.full_text):
            # Type chunks to speed it up if it's too long
            chars_to_type = 2 if len(self.full_text) > 100 else 1
            self.type_idx += chars_to_type
            current_text = self.full_text[:self.type_idx]
            # Add a blinking cursor block at the end
            self.lbl_txt.setText(current_text + " █")
        else:
            self.lbl_txt.setText(self.full_text)
            self.type_timer.stop()

    def add_play_button(self, callback):
        self.btn_play = QPushButton("🔊 PLAY AUDIO")
        self.btn_play.setFont(mono(8, True))
        self.btn_play.setFixedWidth(110)
        self.btn_play.setFixedHeight(20)
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        
        btn_color = self.color
        border_rgba = "rgba(0, 255, 136, 0.2)" if btn_color == GREEN else "rgba(0, 212, 255, 0.2)"
        hover_bg_rgba = "rgba(0, 255, 136, 0.15)" if btn_color == GREEN else "rgba(0, 212, 255, 0.15)"
        normal_bg_rgba = "rgba(0, 255, 136, 0.08)" if btn_color == GREEN else "rgba(0, 212, 255, 0.08)"
        
        self.btn_play.setStyleSheet(f"""
            QPushButton {{
                color: {btn_color};
                background: {normal_bg_rgba};
                border: 1px solid {border_rgba};
                border-radius: 3px;
                text-align: center;
            }}
            QPushButton:hover {{
                background: {hover_bg_rgba};
                border: 1px solid {btn_color};
            }}
            QPushButton:pressed {{
                background: rgba(255, 255, 255, 0.1);
            }}
        """)
        self.btn_play.clicked.connect(callback)
        self.lay.addWidget(self.btn_play)

    def remove_play_button(self):
        if hasattr(self, 'btn_play') and self.btn_play:
            self.lay.removeWidget(self.btn_play)
            self.btn_play.deleteLater()
            self.btn_play = None

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
# TELEMETRY DASHBOARD COMPONENTS
# ──────────────────────────────────────────
class TelemetryMetric(QWidget):
    """Network latency display with a sweeping scan-line animation."""
    def __init__(self, title, value="--", color=CYAN, parent=None):
        super().__init__(parent)
        self.color_str = color
        self._scan = 0.0   # 0..1 horizontal sweep position
        self.setMinimumHeight(60)

        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(10, 10, 10, 10)
        self.lay.setSpacing(4)
        
        self.lbl_title = GlowLabel(title, TEXT_DIM, 8)
        self.lbl_value = GlowLabel(value, color, 18, True)
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lay.addWidget(self.lbl_title)
        self.lay.addWidget(self.lbl_value)
        
        self.setStyleSheet(f"background: rgba(0, 212, 255, 0.03); border: 1px solid {BORDER}; border-radius: 4px;")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(40)

    def _tick(self):
        self._scan = (self._scan + 0.018) % 1.0
        self.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Sweep scan line across the widget
        scan_x = int(self._scan * (w + 40)) - 20
        grad = QConicalGradient(scan_x, h // 2, 0)
        c = parse_color(self.color_str, 0)
        c2 = parse_color(self.color_str, 28)
        # Draw a faint vertical sweep bar
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(parse_color(self.color_str, 18))
        bar_w = max(8, w // 6)
        p.drawRect(max(0, scan_x - bar_w // 2), 0, bar_w, h)

    def set_value(self, val):
        self.lbl_value.setText(str(val))

class TelemetryBar(QWidget):
    def __init__(self, title, max_val=100, color=CYAN, parent=None):
        super().__init__(parent)
        self.max_val = max_val
        self.current_val = 0
        self.color = color
        self._scan = 0.0
        
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(10, 10, 10, 10)
        self.lay.setSpacing(8)
        
        # Header layout
        h_lay = QHBoxLayout()
        self.lbl_title = GlowLabel(title, TEXT_DIM, 8)
        self.lbl_perc = GlowLabel("0%", color, 8, True)
        h_lay.addWidget(self.lbl_title)
        h_lay.addStretch()
        h_lay.addWidget(self.lbl_perc)
        
        self.lay.addLayout(h_lay)
        
        self.bar_space = QWidget()
        self.bar_space.setFixedHeight(12)
        self.lay.addWidget(self.bar_space)
        
        self.setStyleSheet(f"background: rgba(0, 212, 255, 0.03); border: 1px solid {BORDER}; border-radius: 4px;")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(45)

    def _tick(self):
        self._scan = (self._scan + 0.02) % 1.0
        self.update()

    def set_value(self, val):
        self.current_val = min(val, self.max_val)
        perc = int((self.current_val / self.max_val) * 100) if self.max_val > 0 else 0
        self.lbl_perc.setText(f"{perc}%")
        self.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        bx = self.bar_space.x()
        by = self.bar_space.y()
        bw = self.bar_space.width()
        bh = self.bar_space.height()
        
        # Track
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(parse_color(BG2))
        p.drawRoundedRect(bx, by, bw, bh, 2, 2)
        
        # Fill
        fill_w = int(bw * (self.current_val / max(1, self.max_val)))
        if fill_w > 0:
            p.setBrush(parse_color(self.color, 160))
            p.drawRoundedRect(bx, by, fill_w, bh, 2, 2)
            
            # Shimmer
            scan_x = bx + int(fill_w * self._scan)
            shim_w = 20
            scan_x = min(scan_x, bx + fill_w)
            shim_start = max(bx, scan_x - shim_w // 2)
            shim_end   = min(bx + fill_w, scan_x + shim_w // 2)
            if shim_end > shim_start:
                p.setBrush(parse_color(self.color, 255))
                p.drawRoundedRect(shim_start, by, shim_end - shim_start, bh, 2, 2)
        
        # Grid lines
        p.setPen(parse_color(BORDER, 80))
        for i in range(1, 10):
            gx = bx + (bw * i) // 10
            p.drawLine(gx, by, gx, by + bh)

# ──────────────────────────────────────────
# HEX MATRIX STREAMER
# ──────────────────────────────────────────
import random
class HexMatrixStream(QWidget):
    def __init__(self, color=CYAN_DIM, parent=None):
        super().__init__(parent)
        self.color = color
        self.lines = ["" for _ in range(6)]
        self.mode = "FAST"
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(80)

    def set_color(self, color):
        self.color = color
        self.update()

    def set_speed(self, mode):
        self.mode = mode
        if mode == "CALM":
            self.timer.setInterval(250)
        else:
            self.timer.setInterval(80)

    def _tick(self):
        chance = 0.05 if self.mode == "CALM" else 0.2
        for i in range(len(self.lines)):
            if random.random() > chance:
                self.lines[i] = " ".join(f"{random.randint(0, 255):02X}" for _ in range(8))
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(mono(7))
        h = self.height()
        w = self.width()
        step = h // max(1, len(self.lines))
        for i, text in enumerate(self.lines):
            # random opacity flicker
            base_alpha = 20 if self.mode == "CALM" else 40
            flicker = 30 if self.mode == "CALM" else 80
            alpha = int(base_alpha + random.random() * flicker)
            p.setPen(parse_color(self.color, alpha))
            p.drawText(0, i * step, w, step, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)

# ──────────────────────────────────────────
# ANIMATED SIDE PANE (API QUOTA CAROUSEL)
# ──────────────────────────────────────────
class AnimatedSidePane(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumWidth(0)
        self.setMinimumWidth(0)
        self.is_open = False
        
        self.setStyleSheet(f"background: {BG2}; border-left: 1px solid {BORDER};")
        
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(12, 16, 12, 12)
        main_lay.setSpacing(10)
        
        # Header
        header_lay = QHBoxLayout()
        header_lay.setContentsMargins(0,0,0,0)
        title = GlowLabel("API LIMITS", CYAN, 10, True)
        self.btn_close = CyberButton("X", PINK)
        self.btn_close.setFixedWidth(30)
        self.btn_close.clicked.connect(self.toggle)
        
        header_lay.addWidget(title, 1)
        header_lay.addWidget(self.btn_close, 0)
        main_lay.addLayout(header_lay)
        
        # Carousel
        self.carousel = QStackedWidget()
        self.carousel.setStyleSheet("background: transparent; border: none;")
        
        # Page 1: Indexer Model (2.5 Flash Lite)
        page1 = QWidget()
        p1_lay = QVBoxLayout(page1)
        p1_lay.setContentsMargins(0,10,0,0)
        p1_lay.addWidget(GlowLabel("INDEXER MODEL", PINK, 9, True))
        p1_lay.addWidget(GlowLabel("Gemini 2.5 Flash Lite", TEXT_DIM, 8))
        p1_lay.addSpacing(10)
        
        self.lbl_idx_usage = GlowLabel("UNINDEXED: 0 / 40", CYAN, 11, True)
        p1_lay.addWidget(self.lbl_idx_usage)
        p1_lay.addWidget(GlowLabel("Fires background summarizer every 40 msgs", TEXT_DIM, 8))
        p1_lay.addStretch()
        self.carousel.addWidget(page1)

        # Page 2: Main Model (3.1 Flash Lite)
        page2 = QWidget()
        p2_lay = QVBoxLayout(page2)
        p2_lay.setContentsMargins(0,10,0,0)
        p2_lay.addWidget(GlowLabel("MAIN MODEL", AMBER, 9, True))
        p2_lay.addWidget(GlowLabel("Gemini 3.1 Flash Lite", TEXT_DIM, 8))
        p2_lay.addSpacing(10)
        
        self.lbl_main_usage = GlowLabel("CONTEXT: 0 / 50", CYAN, 11, True)
        p2_lay.addWidget(self.lbl_main_usage)
        p2_lay.addWidget(GlowLabel("Max short-term memory capacity", TEXT_DIM, 8))
        p2_lay.addStretch()
        self.carousel.addWidget(page2)
        
        main_lay.addWidget(self.carousel, 1)
        
        # Nav row
        nav_lay = QHBoxLayout()
        nav_lay.setContentsMargins(0,0,0,0)
        self.btn_prev = CyberButton("<", CYAN_MID)
        self.btn_next = CyberButton(">", CYAN_MID)
        
        self.btn_prev.clicked.connect(self._prev)
        self.btn_next.clicked.connect(self._next)
        
        nav_lay.addWidget(self.btn_prev)
        nav_lay.addStretch()
        nav_lay.addWidget(self.btn_next)
        main_lay.addLayout(nav_lay)
        
        # Animation
        self.anim = QPropertyAnimation(self, b"maximumWidth")
        self.anim.setDuration(400)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuart)
        
    def toggle(self):
        if self.is_open:
            self.anim.setStartValue(250)
            self.anim.setEndValue(0)
            self.is_open = False
        else:
            self.anim.setStartValue(0)
            self.anim.setEndValue(250)
            self.is_open = True
        self.anim.start()
        
    def _prev(self):
        curr = self.carousel.currentIndex()
        if curr > 0:
            self.carousel.setCurrentIndex(curr - 1)
        
    def _next(self):
        curr = self.carousel.currentIndex()
        if curr < self.carousel.count() - 1:
            self.carousel.setCurrentIndex(curr + 1)
            
    def update_usage(self, bubble_count: int):
        self.lbl_main_usage.setText(f"CONTEXT: {bubble_count} / 50")
        unindexed = bubble_count % 40
        if bubble_count > 0 and bubble_count % 40 == 0:
            unindexed = 40
        self.lbl_idx_usage.setText(f"UNINDEXED: {unindexed} / 40")

# ──────────────────────────────────────────
# DANGER ZONE CONFIRMATION DIALOG
# ──────────────────────────────────────────
class DangerConfirmDialog(QDialog):
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DANGER ZONE")
        self.setFixedSize(400, 200)
        self.setStyleSheet(f"background-color: #0b0e14; border: 2px solid #ff4444; border-radius: 8px;")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(15)
        
        title = GlowLabel("⚠️ DANGER ZONE ⚠️", "#ff4444", 14, True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)
        
        msg = GlowLabel(message, "#8892b0", 10)
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(msg)
        
        lay.addStretch()
        
        btn_lay = QHBoxLayout()
        btn_lay.setSpacing(15)
        
        btn_no = CyberButton("CANCEL", "#00d4ff")
        btn_no.clicked.connect(self.reject)
        
        btn_yes = CyberButton("YES, NUKE IT", "#ff4444")
        btn_yes.clicked.connect(self.accept)
        
        btn_lay.addWidget(btn_no)
        btn_lay.addWidget(btn_yes)
        
        lay.addLayout(btn_lay)

# ──────────────────────────────────────────
# TOASTER MESSAGE
# ──────────────────────────────────────────
class ToasterMessage(QWidget):
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setFixedSize(300, 80)
        self.setStyleSheet(f"background-color: #0b0e14; border: 1px solid #ffb000; border-radius: 6px;")
        
        lay = QVBoxLayout(self)
        
        lbl = GlowLabel(message, "#ffb000", 9, True)
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)
        
        self.raise_()
        self.show()
        
        if parent:
            self.start_pos = parent.rect().topRight() + QPoint(-320, -100)
            self.end_pos = parent.rect().topRight() + QPoint(-320, 20)
            self.move(self.start_pos)
            
            self.anim = QPropertyAnimation(self, b"pos")
            self.anim.setDuration(400)
            self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.anim.setStartValue(self.start_pos)
            self.anim.setEndValue(self.end_pos)
            
            self.timer = QTimer(self)
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.hide_toaster)
            
            self.anim.finished.connect(lambda: self.timer.start(4000))
            self.anim.start()

    def hide_toaster(self):
        self.anim.setDirection(QPropertyAnimation.Direction.Backward)
        self.anim.finished.disconnect()
        self.anim.finished.connect(self.deleteLater)
        self.anim.start()

# ──────────────────────────────────────────
# MAP WIDGETS
# ──────────────────────────────────────────
class CyberMapWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        
        if QWebEngineView is None:
            lbl = QLabel("QWebEngineView not available")
            lbl.setStyleSheet(f"color: {PINK};")
            self.lay.addWidget(lbl)
            return

        self.view = QWebEngineView()
        self.view.page().settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        self.view.page().settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.lay.addWidget(self.view)
        
        self.api_key = os.getenv("TOMTOM_API_KEY", "")
        self.is_loaded = False
        self.view.loadFinished.connect(self._on_load_finished)
        self._load_html()

    def _load_html(self):
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset='utf-8' />
            <title>TomTom Map</title>
            <style>
                body {{ margin: 0; padding: 0; background-color: #0d1117; }}
                #map {{ width: 100vw; height: 100vh; }}
                .tt-popup-content {{ color: #00d4ff; background: #0d1117; border: 1px solid #00d4ff; font-family: monospace; font-size: 10px; }}
            </style>
            <link rel='stylesheet' type='text/css' href='https://api.tomtom.com/maps-sdk-for-web/cdn/6.x/6.25.0/maps/maps.css'>
            <script src='https://api.tomtom.com/maps-sdk-for-web/cdn/6.x/6.25.0/maps/maps-web.min.js'></script>
        </head>
        <body>
            <div id='map'></div>
            <script>
                var map;
                var routeLayerId = 'route_layer';
                var markers = [];

                function initMap() {{
                    map = tt.map({{
                        key: '{self.api_key}',
                        container: 'map',
                        style: 'https://api.tomtom.com/style/1/style/21.1.0-*?map=basic_night&poi=poi_main',
                        center: [80.22, 13.08],
                        zoom: 11,
                        pitch: 45
                    }});
                }}

                function drawRoute(origin, dest) {{
                    var [oLat, oLon] = origin.split(',');
                    var [dLat, dLon] = dest.split(',');
                    
                    fetch(`https://api.tomtom.com/routing/1/calculateRoute/${{origin}}:${{dest}}/json?key={self.api_key}`)
                    .then(r => r.json())
                    .then(data => {{
                        if (map.getLayer(routeLayerId)) {{
                            map.removeLayer(routeLayerId);
                            map.removeSource(routeLayerId);
                        }}
                        
                        var geojson = {{
                            type: 'Feature',
                            geometry: {{
                                type: 'LineString',
                                coordinates: data.routes[0].legs[0].points.map(p => [p.longitude, p.latitude])
                            }}
                        }};
                        
                        map.addLayer({{
                            id: routeLayerId,
                            type: 'line',
                            source: {{ type: 'geojson', data: geojson }},
                            paint: {{
                                'line-color': '#00d4ff',
                                'line-width': 4,
                                'line-opacity': 0.8
                            }}
                        }});

                        var bounds = new tt.LngLatBounds();
                        data.routes[0].legs[0].points.forEach(p => bounds.extend([p.longitude, p.latitude]));
                        map.fitBounds(bounds, {{ padding: 50, maxZoom: 14 }});
                    }})
                    .catch(e => console.error(e));
                }}

                function showPlaces(placesArray) {{
                    markers.forEach(m => m.remove());
                    markers = [];
                    
                    if (placesArray.length === 0) return;

                    var bounds = new tt.LngLatBounds();
                    
                    placesArray.forEach(p => {{
                        var [lat, lon] = p.coords.split(',');
                        var el = document.createElement('div');
                        el.style.width = '12px';
                        el.style.height = '12px';
                        el.style.borderRadius = '50%';
                        el.style.background = '#ff2d78';
                        el.style.boxShadow = '0 0 10px #ff2d78';
                        
                        var marker = new tt.Marker({{element: el}})
                            .setLngLat([parseFloat(lon), parseFloat(lat)])
                            .setPopup(new tt.Popup({{offset: 25}}).setHTML(`<b>${{p.name}}</b>`))
                            .addTo(map);
                        
                        markers.push(marker);
                        bounds.extend([parseFloat(lon), parseFloat(lat)]);
                    }});
                    
                    map.fitBounds(bounds, {{ padding: 50, maxZoom: 14 }});
                }}

                initMap();
            </script>
        </body>
        </html>
        """
        self.view.setHtml(html)

    def _on_load_finished(self):
        self.is_loaded = True

    def show_route(self, originCoords, destCoords):
        if not self.view or not self.is_loaded: return
        js = f"drawRoute('{originCoords}', '{destCoords}');"
        self.view.page().runJavaScript(js)

    def show_places(self, places):
        if not self.view or not self.is_loaded: return
        import json
        js = f"showPlaces({json.dumps(places)});"
        self.view.page().runJavaScript(js)


class MapToggleTab(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.is_glowing = False
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def set_glow(self, state):
        self.is_glowing = state
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if not painter.isActive():
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = parse_color(PINK) if self.is_glowing else parse_color(CYAN_DIM)
        bg_color = QColor(color.red(), color.green(), color.blue(), 50 if self.is_glowing else 15)

        painter.fillRect(self.rect(), bg_color)

        pen = QPen(color)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        painter.setFont(mono(9, True))
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(-90)

        text = "MAP READY" if self.is_glowing else "OPEN MAP"
        r = QRect(-60, -15, 120, 30)
        painter.drawText(r, Qt.AlignmentFlag.AlignCenter, text)
        painter.end()


class AnimatedMapPane(QFrame):
    sig_data_ready = pyqtSignal()
    sig_closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumWidth(0)
        self.setMinimumWidth(0)
        self.setStyleSheet(f"background: {BG2}; border-left: 1px solid {BORDER};")
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(1, 1, 1, 1)
        
        # Header
        hdr = QLabel("SATELLITE UPLINK // MAPS")
        hdr.setFont(mono(10, True))
        hdr.setStyleSheet(f"color: {CYAN}; padding: 10px; background: rgba(0,212,255,0.05); border-bottom: 1px solid {BORDER};")
        lay.addWidget(hdr)
        
        # Map Widget
        self.map_widget = CyberMapWidget()
        lay.addWidget(self.map_widget, 1)
        
        # Close Button
        self.btn_close = CyberButton("CLOSE UPLINK", PINK)
        self.btn_close.clicked.connect(self.slide_out)
        lay.addWidget(self.btn_close)
        
        self.is_open = False
        self.anim = QPropertyAnimation(self, b"maximumWidth")
        self.anim.setDuration(400)
        self.anim.setEasingCurve(QEasingCurve.Type.OutExpo)
        
    def slide_in(self):
        if self.is_open: return
        self.is_open = True
        self.anim.setStartValue(0)
        self.anim.setEndValue(380)
        self.anim.start()
        
    def slide_out(self):
        if not self.is_open: return
        self.is_open = False
        self.anim.setStartValue(380)
        self.anim.setEndValue(0)
        self.anim.start()
        self.sig_closed.emit()

    def process_map_data(self, data):
        if data.get('type') == 'route':
            self.map_widget.show_route(data['originCoords'], data['destCoords'])
        elif data.get('type') == 'places':
            self.map_widget.show_places(data['places'])
        
        self.sig_data_ready.emit()
