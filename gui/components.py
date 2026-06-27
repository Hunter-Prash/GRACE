import os
import math
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QConicalGradient, QRadialGradient, QLinearGradient, QPixmap, QGuiApplication, QPainterPath, QPolygon, QPolygonF, QBrush, QDesktopServices
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtCore import QUrl, pyqtSignal, Qt, QTimer, QPropertyAnimation, QParallelAnimationGroup, QSequentialAnimationGroup, QVariantAnimation, QEasingCurve, QRectF, QRect, QPoint, QPointF
from PyQt6.QtWidgets import QLabel, QFrame, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy, QGraphicsOpacityEffect, QStackedWidget, QDialog, QScrollArea, QGraphicsDropShadowEffect
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
        self.header_widgets = []
        
        self._phase = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(50)
        
    def add_header_widget(self, widget):
        widget.setParent(self)
        self.header_widgets.append(widget)
        self._reposition_header_widgets()
        widget.show()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._reposition_header_widgets()

    def _reposition_header_widgets(self):
        offset_right = 10
        for w in reversed(self.header_widgets):
            w.move(self.width() - offset_right - w.width(), 4)
            offset_right += w.width() + 5

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
        self.is_user = speaker == "YOU"
        
        if self.is_user:
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
        
        if not self.is_user:
            self._scan_pos = -0.2
            self.scan_timer = QTimer(self)
            self.scan_timer.timeout.connect(self._tick_scan)
            self.scan_timer.start(40)
            
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
        if not self.is_user:
            self.lbl_txt.setText("")
            self.type_idx = 0
            self.type_timer = QTimer(self)
            self.type_timer.timeout.connect(self._type_next_char)
            self.type_timer.start(10)  # Type very fast (10ms per loop)
            
    def _tick_scan(self):
        self._scan_pos += 0.016
        if self._scan_pos > 1.2:
            self._scan_pos = -0.2
        self.update()
        
    def paintEvent(self, e):
        super().paintEvent(e)
        if hasattr(self, 'is_user') and not self.is_user:
            p = QPainter(self)
            h = self.height()
            w = self.width()
            y = int(self._scan_pos * h)
            beam_h = max(30, h // 2)
            
            grad = QLinearGradient(0, y - beam_h//2, 0, y + beam_h//2)
            grad.setColorAt(0.0, QColor(0,0,0,0))
            grad.setColorAt(0.5, parse_color(self.color, 12))
            grad.setColorAt(1.0, QColor(0,0,0,0))
            
            p.fillRect(0, y - beam_h//2, w, beam_h, grad)
            p.fillRect(0, y, w, 1, parse_color(self.color, 25))
            
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
        self.set_color(color)
        
    def set_color(self, color):
        self.color = color
        border_color = "rgba(0, 212, 255, 0.2)" if color == CYAN else f"rgba(255, 255, 255, 0.2)"
        hover_bg = "rgba(0, 212, 255, 0.1)" if color == CYAN else f"rgba(255, 255, 255, 0.1)"
        if color == PINK: border_color = "rgba(255, 45, 120, 0.2)"; hover_bg = "rgba(255, 45, 120, 0.1)"
        if color == GREEN: border_color = "rgba(0, 255, 136, 0.2)"; hover_bg = "rgba(0, 255, 136, 0.1)"
        if color == AMBER: border_color = "rgba(255, 170, 0, 0.2)"; hover_bg = "rgba(255, 170, 0, 0.1)"
        
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
# CONTEXT SATURATION RING
# ──────────────────────────────────────────
class ContextSaturationRing(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.max_val = 50
        self.current_val = 0
        self._anim_val = 0.0
        
        self.setFixedHeight(60)
        self.setMinimumWidth(200)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(30)
        
    def _tick(self):
        self._anim_val += (self.current_val - self._anim_val) * 0.1
        if abs(self.current_val - self._anim_val) < 0.1:
            self._anim_val = self.current_val
        self.update()
        
    def set_value(self, val):
        self.current_val = min(val, self.max_val)
        
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        
        perc = self._anim_val / max(1, self.max_val)
        
        if perc < 0.5:
            color = CYAN
        elif perc < 0.85:
            color = AMBER
        else:
            color = PINK
            
        c = parse_color(color)
        c_bg = parse_color(color, 40)
        
        ring_size = h - 16
        cx = 10 + ring_size // 2
        cy = h // 2
        
        # Background ring
        p.setPen(QPen(c_bg, 4))
        p.drawEllipse(10, cy - ring_size // 2, ring_size, ring_size)
        
        # Foreground arc
        arc_pen = QPen(c, 4)
        arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(arc_pen)
        
        start_angle = 90 * 16
        span_angle = int(-perc * 360 * 16)
        if span_angle != 0:
            p.drawArc(10, cy - ring_size // 2, ring_size, ring_size, start_angle, span_angle)
            
        # Text
        tx = 10 + ring_size + 16
        p.setFont(mono(14, True))
        p.setPen(c)
        actual_perc = int((self.current_val / max(1, self.max_val)) * 100)
        p.drawText(tx, cy + 2, f"{actual_perc}%")
        
        p.setFont(mono(8))
        p.setPen(parse_color(TEXT_DIM))
        p.drawText(tx, cy + 18, "CONTEXT")

# ──────────────────────────────────────────
# ANIMATED SIDE PANE (API QUOTA CAROUSEL)
# ──────────────────────────────────────────
import random

KATAKANA = [chr(i) for i in range(0x30A0, 0x30FF)] + [str(i) for i in range(10)]

class MatrixDrop:
    def __init__(self, x, h):
        self.x = x
        self.y = random.randint(-100, h)
        self.speed = random.uniform(2, 5)
        self.chars = [random.choice(KATAKANA) for _ in range(random.randint(6, 16))]

class MatrixRain(QWidget):
    def __init__(self, color=CYAN_DIM, parent=None):
        super().__init__(parent)
        self.color = color
        self.mode = "CALM"
        self.drops = []
        self._init_drops = False
        self.font_size = 11
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(40)

    def set_color(self, color):
        self.color = color
        self.update()

    def set_speed(self, mode):
        self.mode = mode

    def _tick(self):
        h = self.height()
        w = self.width()
        
        if not self._init_drops and w > 0:
            cols = w // 14
            for i in range(cols):
                if random.random() > 0.3:
                    self.drops.append(MatrixDrop(i * 14 + 4, h))
            self._init_drops = True
            
        # Speed modifier based on Grace's state
        speed_mult = 1.0
        if self.mode == "PROCESSING":
            speed_mult = 0.3
        elif self.mode in ("LISTENING", "SPEAKING"):
            speed_mult = 2.0
            
        for drop in self.drops:
            drop.y += drop.speed * speed_mult
            
            # Reset if off screen
            if drop.y - (len(drop.chars) * 14) > h:
                drop.y = random.randint(-50, -10)
                drop.chars = [random.choice(KATAKANA) for _ in range(random.randint(6, 16))]
                
            # Randomly mutate chars
            if random.random() > 0.8:
                idx = random.randint(0, len(drop.chars) - 1)
                drop.chars[idx] = random.choice(KATAKANA)
                
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(mono(self.font_size))
        
        for drop in self.drops:
            for i, char in enumerate(drop.chars):
                char_y = drop.y - (i * 14)
                if char_y < -14 or char_y > self.height() + 14:
                    continue
                    
                if i == 0:
                    p.setPen(QColor(255, 255, 255))
                else:
                    alpha = max(0, 255 - (i * 20))
                    p.setPen(parse_color(self.color, alpha))
                    
                p.drawText(drop.x, int(char_y), char)

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
# DAILY BRIEFING PANEL (Frosted Glass UI)
# ──────────────────────────────────────────
class DailyBriefingPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumWidth(0)
        self.setMinimumWidth(0)
        self.is_open = False
        
        # Frosted glass styling with a border
        self.setStyleSheet(f"background: rgba(20, 20, 30, 210); border-left: 1px solid {CYAN_DIM};")
        
        self.main_lay = QVBoxLayout(self)
        self.main_lay.setContentsMargins(15, 20, 15, 20)
        self.main_lay.setSpacing(15)
        
        # Header
        header_lay = QHBoxLayout()
        header_lay.setContentsMargins(0,0,0,0)
        title = GlowLabel("MORNING BRIEFING", CYAN, 12, True)
        self.btn_close = CyberButton("X", PINK)
        self.btn_close.setFixedWidth(30)
        self.btn_close.clicked.connect(self.slide_out)
        
        header_lay.addWidget(title, 1)
        header_lay.addWidget(self.btn_close, 0)
        self.main_lay.addLayout(header_lay)
        
        # We will populate the goals dynamically here
        self.content_lay = QVBoxLayout()
        self.content_lay.setSpacing(15)
        self.main_lay.addLayout(self.content_lay)
        
        self.main_lay.addStretch()
        
        # Animation
        self.anim = QPropertyAnimation(self, b"maximumWidth")
        self.anim.setDuration(600)
        self.anim.setEasingCurve(QEasingCurve.Type.OutExpo)
        
    def populate_data(self, goals_data):
        # Clear old content
        while self.content_lay.count():
            child = self.content_lay.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        goals = goals_data.get("goals", [])[:2] # Top 2 goals
        
        for goal in goals:
            goal_id = goal.get("goalId", "UNKNOWN")
            milestones = goal.get("milestones", {})
            total = len(milestones)
            completed = sum(1 for v in milestones.values() if v)
            perc = int((completed / max(1, total)) * 100)
            
            # Goal Container
            g_widget = QWidget()
            g_widget.setStyleSheet(f"background: rgba(0, 212, 255, 0.05); border: 1px solid {BORDER}; border-radius: 4px;")
            g_lay = QVBoxLayout(g_widget)
            g_lay.setContentsMargins(10, 10, 10, 10)
            
            lbl_title = GlowLabel(goal_id.upper().replace("-", " "), CYAN, 10, True)
            g_lay.addWidget(lbl_title)
            
            # Custom Progress Bar using StatBar
            bar = StatBar(f"{completed}/{total}", CYAN)
            bar.setValue(perc)
            g_lay.addWidget(bar)
            
            self.content_lay.addWidget(g_widget)

        # Static Metrics Icons Row (visual flair)
        metrics_widget = QWidget()
        m_lay = QHBoxLayout(metrics_widget)
        m_lay.setContentsMargins(0, 10, 0, 0)
        
        lbl_m = GlowLabel("METRICS: ", TEXT_DIM, 8)
        m_lay.addWidget(lbl_m)
        m_lay.addWidget(PulsingDot(GREEN, 8)) # Energy
        m_lay.addWidget(PulsingDot(CYAN, 8))  # Focus
        m_lay.addWidget(PulsingDot(PINK, 8))  # Mood
        m_lay.addStretch()
        
        self.content_lay.addWidget(metrics_widget)

    def slide_in(self, goals_data=None):
        if goals_data:
            self.populate_data(goals_data)
        if not self.is_open:
            self.anim.setStartValue(0)
            self.anim.setEndValue(300)
            self.is_open = True
            self.anim.start()
            
    def slide_out(self):
        if self.is_open:
            self.anim.setStartValue(300)
            self.anim.setEndValue(0)
            self.is_open = False
            self.anim.start()

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

# ──────────────────────────────────────────
# HOLO SEARCH CUSTOM WIDGETS
# ──────────────────────────────────────────
class HoloThumbnail(QWidget):
    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
        self.setFixedSize(160, 100)
        self.pixmap = None
        self._scan_y = 0.0
        self._scan_dir = 1
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(30)
        
    def set_pixmap(self, pixmap):
        self.pixmap = pixmap
        self.update()
        
    def _animate(self):
        pass
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        
        path = QPainterPath()
        c = 12
        path.moveTo(0, 0)
        path.lineTo(w - c, 0)
        path.lineTo(w, c)
        path.lineTo(w, h)
        path.lineTo(c, h)
        path.lineTo(0, h - c)
        path.closeSubpath()
        
        painter.setClipPath(path)
        
        if self.pixmap:
            painter.drawPixmap(self.rect(), self.pixmap)
        else:
            # Pure dark fallback
            painter.fillRect(self.rect(), QColor(5, 5, 5, 255))
            
        painter.setClipping(False)
        
        # Draw thin dim border
        pen = QPen(parse_color(CYAN_DIM))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        
        # Draw bright bottom cyan border glow/scan
        pen = QPen(parse_color(CYAN))
        pen.setWidth(3)
        painter.setPen(pen)
        painter.drawLine(c, h, w, h)

class HoloCard(QWidget):
    def __init__(self, title, url, content, is_new=False, parent=None):
        super().__init__(parent)
        self.is_new = is_new
        self.url = url
        self.is_selected = False
        
        # Setup layout
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(6)
        
        # Title (Pink)
        t_lbl = GlowLabel(title, PINK, 10, True)
        t_lbl.setWordWrap(True)
        lay.addWidget(t_lbl)
        
        # Source (Cyan)
        import urllib.parse
        domain = urllib.parse.urlparse(url).netloc.upper()
        s_lbl = QLabel(f"VERIFIED SOURCE // {domain}")
        s_lbl.setFont(mono(8))
        s_lbl.setStyleSheet(f"color: {CYAN}; border: none; background: transparent;")
        lay.addWidget(s_lbl)
        
        # Snippet
        c_lbl = QLabel(content)
        c_lbl.setFont(sans(9))
        c_lbl.setStyleSheet(f"color: {TEXT_DIM}; border: none; background: transparent; line-height: 1.4;")
        c_lbl.setWordWrap(True)
        lay.addWidget(c_lbl)
        
        # Link
        self.link = QLabel(f'[ ACCESS SECURE DATALINK ]')
        self.link.setFont(mono(8))
        self.link.setStyleSheet(f"color: {PINK}; border: none; background: transparent; font-weight: bold;")
        self.link.setCursor(Qt.CursorShape.PointingHandCursor)
        def _open_link(e, u=self.url):
            QDesktopServices.openUrl(QUrl(u))
            
            win = self.window()
            if hasattr(win, '_card_widgets'):
                for card in win._card_widgets:
                    if card is not self:
                        card.is_selected = False
                        card.link.setStyleSheet(f"color: {PINK}; border: none; background: transparent; font-weight: bold;")
                        card.link.setText('[ ACCESS SECURE DATALINK ]')
                        card.update()
                        
            self.is_selected = True
            self.link.setStyleSheet(f"color: {GREEN}; border: none; background: transparent; font-weight: bold;")
            self.link.setText('[ DATALINK ACCESSED ]')
            self.update()
            
        self.link.mousePressEvent = _open_link
        lay.addWidget(self.link)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        
        path = QPainterPath()
        c = 16
        path.moveTo(0, 0)
        path.lineTo(w - c, 0)
        path.lineTo(w, c)
        path.lineTo(w, h)
        path.lineTo(c, h)
        path.lineTo(0, h - c)
        path.closeSubpath()
        
        # Background pure black/dark
        if self.is_selected:
            painter.fillPath(path, QColor(0, 255, 0, 15))
        else:
            painter.fillPath(path, QColor(8, 8, 12, 240))
        
        # Border gradient
        pen_grad = QLinearGradient(0, 0, w, h)
        if self.is_selected:
            pen_grad.setColorAt(0, parse_color(GREEN))
            pen_grad.setColorAt(1, parse_color(GREEN))
        else:
            pen_grad.setColorAt(0, parse_color(PINK))
            pen_grad.setColorAt(0.35, parse_color(CYAN))
            pen_grad.setColorAt(1, parse_color(CYAN))
        
        pen = QPen(pen_grad, 2)
        painter.setPen(pen)
        painter.drawPath(path)
        
        if self.is_new:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(parse_color(CYAN))
            tag = QPolygonF([
                QPointF(w - 40, 0),
                QPointF(w - c, 0),
                QPointF(w, c),
                QPointF(w, 24),
                QPointF(w - 40, 24)
            ])
            painter.drawPolygon(tag)
            
            painter.setPen(QColor(0,0,0))
            painter.setFont(mono(8, True))
            painter.drawText(QRect(w - 36, 4, 32, 16), Qt.AlignmentFlag.AlignCenter, "NEW")

# ──────────────────────────────────────────
# HOLOGRAPHIC SEARCH WINDOW (Cyberpunk HUD)
# ──────────────────────────────────────────
import random

class CyberBorderFrame(QFrame):
    """A frame that draws animated cyberpunk corner brackets and pulsing neon border."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._phase = 0.0
        self._bracket_len = 20
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(30)

    def _tick(self):
        self._phase += 0.04
        self.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        bl = self._bracket_len

        # Pulsing border alpha
        pulse = int(80 + 40 * math.sin(self._phase * 2))
        border_color = QColor(255, 60, 120, pulse)
        pen = QPen(border_color, 1.5)
        p.setPen(pen)
        p.drawRect(1, 1, w - 2, h - 2)

        # Corner brackets — bright cyan
        bracket_alpha = int(200 + 55 * math.sin(self._phase * 3))
        bp = QPen(QColor(0, 212, 255, bracket_alpha), 2)
        p.setPen(bp)

        # Top-left
        p.drawLine(0, 0, bl, 0)
        p.drawLine(0, 0, 0, bl)
        # Top-right
        p.drawLine(w, 0, w - bl, 0)
        p.drawLine(w - 1, 0, w - 1, bl)
        # Bottom-left
        p.drawLine(0, h - 1, bl, h - 1)
        p.drawLine(0, h - 1, 0, h - 1 - bl)
        # Bottom-right
        p.drawLine(w - 1, h - 1, w - 1 - bl, h - 1)
        p.drawLine(w - 1, h - 1, w - 1, h - 1 - bl)

        # Animated data-stream line at the top
        stream_x = int((math.sin(self._phase) + 1) / 2 * w)
        p.setPen(QPen(QColor(0, 212, 255, 100), 1))
        p.drawLine(0, 0, stream_x, 0)

        p.end()


class GlitchOverlay(QWidget):
    """Chromatic aberration + horizontal tearing glitch during open/close."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.is_glitching = False
        self._intensity = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(33)  # ~30fps

    def start_glitch(self, duration_ms=600):
        self.is_glitching = True
        self._intensity = 8
        QTimer.singleShot(duration_ms, self._stop)

    def _stop(self):
        self.is_glitching = False
        self.update()

    def _tick(self):
        if self.is_glitching:
            self._intensity = random.randint(4, 12)
            self.update()

    def paintEvent(self, e):
        if not self.is_glitching:
            return
        p = QPainter(self)
        w, h = self.width(), self.height()
        intensity = self._intensity

        # Horizontal tear slices
        for _ in range(random.randint(3, 8)):
            y = random.randint(0, h)
            bh = random.randint(1, 6)
            shift = random.randint(-intensity, intensity)
            # Cyan channel shift
            p.fillRect(shift, y, w, bh, QColor(0, 255, 255, 35))
            # Pink/red channel shift (opposite direction)
            p.fillRect(-shift, y + random.randint(-2, 2), w, bh, QColor(255, 0, 80, 30))

        # Random block displacement
        for _ in range(random.randint(1, 3)):
            bx = random.randint(0, w - 80)
            by = random.randint(0, h - 20)
            bw = random.randint(40, 120)
            bbh = random.randint(5, 15)
            p.fillRect(bx + random.randint(-6, 6), by, bw, bbh, QColor(0, 212, 255, 20))

        p.end()


class ScanlineOverlay(QWidget):
    """CRT scanline that sweeps down with a gradient bloom trail."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._y = 0.0
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(3000)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setLoopCount(-1)
        self.anim.valueChanged.connect(self._update_y)
        self.anim.start()

    def _update_y(self, val):
        self._y = val
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        y = int(self._y * h)

        # Gradient bloom trail above the scanline
        trail_h = 60
        grad = QLinearGradient(0, max(0, y - trail_h), 0, y)
        grad.setColorAt(0, QColor(0, 212, 255, 0))
        grad.setColorAt(1, QColor(0, 212, 255, 8))
        p.fillRect(0, max(0, y - trail_h), w, trail_h, grad)

        # Main bright scanline
        p.fillRect(0, y, w, 1, QColor(0, 212, 255, 70))
        # Subtle secondary line
        p.fillRect(0, y + 2, w, 1, QColor(0, 212, 255, 15))

        # Faint static noise lines (every ~4 pixels)
        p.setPen(QPen(QColor(0, 212, 255, 4), 1))
        for sy in range(0, h, 4):
            p.drawLine(0, sy, w, sy)

        p.end()


class TelemetrySidePane(QFrame):
    """Rapidly updating hex/memory readout panel on the right side."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(150)
        self.setStyleSheet(
            f"background: #020304;"
            f"border: 1px solid rgba(0, 212, 255, 60);"
            f"border-left: 1px solid rgba(255, 60, 120, 80);"
        )
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(10, 14, 10, 14)
        self.lay.setSpacing(4)

        # Header
        header = GlowLabel("◈ SYS_TELEMETRY", PINK, 8, True)
        header.setStyleSheet(
            f"color: {PINK}; border: none; border-bottom: 1px solid rgba(255,60,120,80); padding-bottom: 6px;"
        )
        self.lay.addWidget(header)

        self.lay.addSpacing(4)

        # Status indicators
        self._status_lbl = GlowLabel("● LINK ACTIVE", CYAN, 7, True)
        self._status_lbl.setStyleSheet(f"color: {CYAN}; border: none;")
        self.lay.addWidget(self._status_lbl)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: rgba(0, 212, 255, 30);")
        self.lay.addWidget(div)

        self.lay.addSpacing(2)

        # Data labels
        self.labels = []
        for _ in range(18):
            l = GlowLabel("0x0000", CYAN_MID, 7, True)
            l.setStyleSheet(f"color: {CYAN_MID}; border: none; padding: 1px 0px;")
            l.setFixedHeight(14)
            self.lay.addWidget(l)
            self.labels.append(l)

        self.lay.addStretch()

        # Footer with "progress"
        self._progress_lbl = GlowLabel("DECRYPTING...", PINK, 7, True)
        self._progress_lbl.setStyleSheet(f"color: {PINK}; border: none;")
        self.lay.addWidget(self._progress_lbl)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._scramble)
        self.timer.start(60)
        self._tick_count = 0

    def _scramble(self):
        self._tick_count += 1
        prefixes = ["MEM_", "NET_", "0x", "REG:", "I/O:", "PTR_", "BUF_"]
        suffixes = ["OK", "--", ">>", "<<", "██"]
        for lbl in self.labels:
            if random.random() > 0.6:
                prefix = random.choice(prefixes)
                val = f"{random.randint(0, 0xFFFF):04X}"
                suffix = random.choice(suffixes) if random.random() > 0.7 else ""
                lbl.setText(f"{prefix}{val} {suffix}")

        # Cycle status
        if self._tick_count % 30 == 0:
            statuses = ["● LINK ACTIVE", "● SCANNING...", "● SYNC OK", "● PACKET IN"]
            self._status_lbl.setText(random.choice(statuses))

        # Progress bar effect
        bars = "█" * random.randint(2, 8) + "░" * random.randint(1, 4)
        self._progress_lbl.setText(f"{bars} {random.randint(40, 99)}%")

class HoloSearchWindow(QDialog):
    WINDOW_W = 820
    WINDOW_H = 750

    def __init__(self, search_data, parent=None):
        super().__init__(parent)
        self.search_data = search_data
        self._drag_pos = None
        self._card_widgets = []

        # Frameless, translucent, always-on-top
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.network_manager = QNetworkAccessManager(self)

        self.init_ui()
        self.populate_data()

        # ── Left-Side Expanding Animation ──────────────────
        screen = QGuiApplication.primaryScreen().geometry()
        self._x_pos = 30
        self._y_pos = max(20, screen.height() // 2 - self.WINDOW_H // 2)

        self.setGeometry(self._x_pos, self._y_pos, 4, self.WINDOW_H)
        self.setWindowOpacity(0.0)

        self.anim_group = QSequentialAnimationGroup(self)

        # Step 1: Flash in as a thin vertical sliver
        op = QPropertyAnimation(self, b"windowOpacity")
        op.setDuration(120)
        op.setStartValue(0.0)
        op.setEndValue(1.0)

        # Step 2: Expand horizontally from left
        geom = QPropertyAnimation(self, b"geometry")
        geom.setDuration(350)
        geom.setStartValue(QRect(self._x_pos, self._y_pos, 4, self.WINDOW_H))
        geom.setEndValue(QRect(self._x_pos, self._y_pos, self.WINDOW_W, self.WINDOW_H))
        geom.setEasingCurve(QEasingCurve.Type.OutExpo)

        self.anim_group.addAnimation(op)
        self.anim_group.addAnimation(geom)

    def showEvent(self, event):
        super().showEvent(event)
        self.anim_group.start()

        # Trigger glitch during opening
        self.glitch_overlay.start_glitch(600)

        # Sequential card pop-in after expansion finishes
        QTimer.singleShot(550, self._animate_cards_in)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep overlays matching window size
        if hasattr(self, 'scanline'):
            self.scanline.setGeometry(0, 0, self.width(), self.height())
        if hasattr(self, 'glitch_overlay'):
            self.glitch_overlay.setGeometry(0, 0, self.width(), self.height())

    def init_ui(self):
        # Root layout — no margins, the CyberBorderFrame IS the visual boundary
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # The main bordered frame with animated corner brackets
        self.cyber_frame = CyberBorderFrame(self)
        self.cyber_frame.setStyleSheet("background-color: #020305;")
        root.addWidget(self.cyber_frame)

        # Inside the cyber frame: HBox for [Main Content | Telemetry]
        outer_h = QHBoxLayout(self.cyber_frame)
        outer_h.setContentsMargins(2, 2, 2, 2)
        outer_h.setSpacing(0)

        # ═══════ LEFT: Main Search Panel ═══════
        self.bg_frame = QFrame()
        self.bg_frame.setStyleSheet(
            "background-color: #030406;"
            "border: none;"
        )

        frame_layout = QVBoxLayout(self.bg_frame)
        frame_layout.setContentsMargins(20, 16, 16, 16)
        frame_layout.setSpacing(8)

        # ── Header bar ────────────────────────────────────
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # Title Area
        t_lay = QHBoxLayout()
        t_lay.setContentsMargins(0, 0, 0, 0)
        icon = GlowLabel("◈", CYAN, 12, True)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(22, 22)
        icon.setStyleSheet(f"color: {CYAN}; border: 1px solid {CYAN}; border-radius: 11px;")
        t_lay.addWidget(icon)
        title = GlowLabel("HOLO-SEARCH", PINK, 11, True)
        title.setStyleSheet(f"color: {PINK}; letter-spacing: 4px; font-weight: bold; border: none;")
        t_lay.addWidget(title)
        header_layout.addLayout(t_lay)

        header_layout.addStretch()

        # Signal Area
        s_lay = QHBoxLayout()
        s_lay.setContentsMargins(0, 0, 0, 0)
        dot = PulsingDot(CYAN, 7)
        s_lay.addWidget(dot)
        signal = GlowLabel("SIGNAL: STRONG", CYAN, 9, True)
        signal.setStyleSheet(f"color: {CYAN}; border: none;")
        s_lay.addWidget(signal)
        header_layout.addLayout(s_lay)

        header_layout.addSpacing(12)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                color: {PINK}; background: transparent;
                border: 1px solid {PINK}; border-radius: 0px;
                font-size: 12px; font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(255,60,120,0.25);
                border: 1px solid {PINK};
            }}
        """)
        btn_close.clicked.connect(self.close_window)
        header_layout.addWidget(btn_close)
        frame_layout.addLayout(header_layout)

        # ── Divider line ──
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: rgba(0, 212, 255, 40);")
        frame_layout.addWidget(div)

        # ── Query label (Box) ──────────────────────────────
        query = self.search_data.get('query', '')
        q_frame = QFrame()
        q_frame.setStyleSheet(f"border: 1px solid rgba(0, 212, 255, 40); border-radius: 0px; background: rgba(0, 212, 255, 8);")
        q_lay = QHBoxLayout(q_frame)
        q_lay.setContentsMargins(12, 6, 12, 6)
        q_prefix = GlowLabel("QUERY >", PINK, 9, True)
        q_prefix.setStyleSheet(f"color: {PINK}; border: none;")
        q_prefix.setFixedWidth(60)
        q_lay.addWidget(q_prefix)
        q_lbl = GlowLabel(f"{query.lower()}", CYAN, 9, True)
        q_lbl.setStyleSheet(f"color: {CYAN}; border: none;")
        q_lay.addWidget(q_lbl)
        frame_layout.addWidget(q_frame)

        # ── Main Scroll Area ──────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: rgba(0, 0, 0, 0);
                width: 5px;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {CYAN};
                border-radius: 2px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.setContentsMargins(0, 4, 4, 4)

        scroll.setWidget(self.scroll_content)
        frame_layout.addWidget(scroll)

        # ── Footer Stats ──────────────────────────────────
        footer_div = QFrame()
        footer_div.setFixedHeight(1)
        footer_div.setStyleSheet("background: rgba(0, 212, 255, 25);")
        frame_layout.addWidget(footer_div)

        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(4, 6, 4, 0)
        res_count = len(self.search_data.get('results', []))
        self.lbl_results = GlowLabel(f"RESULTS:  {res_count}", CYAN_DIM, 8, True)

        lat = random.randint(180, 420)
        self.lbl_latency = GlowLabel(f"LATENCY:  {lat}ms", CYAN_DIM, 8, True)

        self.lbl_uplink = GlowLabel("UPLINK:  ENCRYPTED", CYAN_DIM, 8, True)

        footer_layout.addWidget(self.lbl_results)
        footer_layout.addStretch()
        footer_layout.addWidget(self.lbl_latency)
        footer_layout.addStretch()
        footer_layout.addWidget(self.lbl_uplink)

        frame_layout.addLayout(footer_layout)

        outer_h.addWidget(self.bg_frame, 1)  # stretches to fill

        # ═══════ RIGHT: Telemetry Side Pane ═══════
        self.telemetry_pane = TelemetrySidePane()
        outer_h.addWidget(self.telemetry_pane, 0)  # fixed width, no stretch

        from PyQt6.QtWidgets import QSizeGrip
        self.size_grip = QSizeGrip(self)
        self.size_grip.setStyleSheet("background: transparent;")
        self.telemetry_pane.lay.addWidget(self.size_grip, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)

        # ═══════ Overlays (on top of everything) ═══════
        self.scanline = ScanlineOverlay(self)
        self.scanline.setGeometry(0, 0, self.WINDOW_W, self.WINDOW_H)
        self.glitch_overlay = GlitchOverlay(self)
        self.glitch_overlay.setGeometry(0, 0, self.WINDOW_W, self.WINDOW_H)
        self.scanline.raise_()
        self.glitch_overlay.raise_()

    @staticmethod
    def _clean_text(text):
        """Strip markdown formatting from snippet text."""
        import re
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # [text](url) -> text
        text = re.sub(r'#{1,6}\s*', '', text)                   # headings
        text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)   # bold/italic
        text = re.sub(r'`([^`]+)`', r'\1', text)                # inline code
        text = re.sub(r'\n{3,}', '\n\n', text)                  # excess newlines
        return text.strip()

    def populate_data(self):
        images = self.search_data.get('images', [])
        
        # ── HOLOGRAPHIC IMAGE STRIP ──
        if images:
            img_scroll = QScrollArea()
            img_scroll.setFixedHeight(145)
            img_scroll.setWidgetResizable(True)
            img_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            img_scroll.setStyleSheet(f"""
                QScrollArea {{ border: none; background: transparent; }}
                QScrollBar:horizontal {{
                    background: rgba(0,0,0,0); height: 5px; border-radius: 2px;
                }}
                QScrollBar::handle:horizontal {{
                    background: {CYAN}; border-radius: 2px;
                }}
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
            """)
            img_container = QWidget()
            img_container.setStyleSheet("background: transparent;")
            img_lay = QHBoxLayout(img_container)
            img_lay.setContentsMargins(0, 0, 0, 0)
            img_lay.setSpacing(12)
            
            for url in images[:6]:
                thumb = HoloThumbnail(url)
                # Drop shadow on the whole thumbnail widget
                glow = QGraphicsDropShadowEffect(self)
                glow.setBlurRadius(15)
                glow.setColor(parse_color(CYAN_DIM))
                glow.setOffset(0, 0)
                thumb.setGraphicsEffect(glow)
                
                img_lay.addWidget(thumb)
                self.fetch_image(url, thumb)
            
            img_lay.addStretch()
            img_scroll.setWidget(img_container)
            self.scroll_layout.addWidget(img_scroll)

        # ── JARVIS STYLE RESULTS CARDS ──
        results = self.search_data.get('results', [])
        for i, res in enumerate(results[:5]):
            title = self._clean_text(res.get('title', 'Unknown'))
            url = res.get('url', '#')
            content = self._clean_text(res.get('content', ''))
            if len(content) > 300:
                content = content[:297] + "..."
            
            is_new = (i == 0) # Only tag the first as NEW for aesthetic
            
            card = HoloCard(title, url, content, is_new)
            
            # Subtle Drop shadow instead of massive glow
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(8)
            shadow.setColor(QColor(255, 60, 120, 40)) # Faint pink shadow
            shadow.setOffset(0, 0)
            card.setGraphicsEffect(shadow)
            
            card.hide() # Hidden for pop-in animation
            self._card_widgets.append(card)
            self.scroll_layout.addWidget(card)
            
        self.scroll_layout.addStretch()

    def _animate_cards_in(self):
        for i, card in enumerate(self._card_widgets):
            QTimer.singleShot(i * 120, card.show)

    # ── DRAGGING LOGIC ──
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        
    def fetch_image(self, url, label):
        req = QNetworkRequest(QUrl(url))
        req.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, b"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        reply = self.network_manager.get(req)
        # Using a default argument trick to capture reply and label inside lambda
        reply.finished.connect(lambda r=reply, l=label: self.on_image_fetched(r, l))
        
    def on_image_fetched(self, reply, label):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            if not pixmap.isNull():
                if hasattr(label, 'set_pixmap'):
                    label.set_pixmap(pixmap)
                else:
                    label.setPixmap(pixmap)
            else:
                if hasattr(label, 'setText'):
                    label.setText("Invalid Image")
        else:
            if hasattr(label, 'setText'):
                label.setText("Image Error")
        reply.deleteLater()
        
    def close_window(self):
        self.glitch_overlay.start_glitch(400)
        
        # Update animation to close from CURRENT size/position if resized
        geom_anim = self.anim_group.animationAt(1)
        geom_anim.setStartValue(QRect(self.x(), self.y(), 4, self.height()))
        geom_anim.setEndValue(self.geometry())

        self.anim_group.setDirection(QPropertyAnimation.Direction.Backward)
        self.anim_group.finished.connect(self.accept)
        self.anim_group.start()

    # Make frameless window draggable
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

# ──────────────────────────────────────────
# CYBERPUNK PIPELINE TERMINAL (Aesthetic System Monitor)
# ──────────────────────────────────────────
class CyberTerminalLine(QWidget):
    """A single line in the terminal with typewriter animation."""
    def __init__(self, text, color_type="dim", parent=None):
        super().__init__(parent)
        self.setFixedHeight(18)
        self._full_text = text
        self._visible_chars = 0
        self._color_type = color_type

        self.label = QLabel(self)
        self.label.setFont(mono(8))
        self.label.setStyleSheet(f"color: {self._get_color()}; background: transparent; border: none; padding: 0px 4px;")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.label)

        # Typewriter timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._type_next)
        self._timer.start(12)  # ~12ms per character

    def _get_color(self):
        colors = {
            "api": AMBER,
            "tool": PINK,
            "db": GREEN,
            "rag": CYAN,
            "tts": "#B388FF",
            "dim": CYAN_DIM,
            "system": CYAN,
            "error": "#FF5252",
            "separator": "rgba(0, 212, 255, 30)",
        }
        return colors.get(self._color_type, CYAN_DIM)

    def _type_next(self):
        self._visible_chars += 2  # 2 chars at a time for speed
        if self._visible_chars >= len(self._full_text):
            self._visible_chars = len(self._full_text)
            self._timer.stop()
        self.label.setText(self._full_text[:self._visible_chars])


class CyberTerminal(QWidget):
    """Aesthetic pipeline terminal that visualizes Grace's backend operations."""
    def __init__(self, parent=None):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Outer border frame with cyberpunk styling
        self.frame = CyberBorderFrame(self)
        self.frame.setStyleSheet("background-color: #020305;")
        root.addWidget(self.frame)

        frame_lay = QVBoxLayout(self.frame)
        frame_lay.setContentsMargins(12, 14, 12, 12)
        frame_lay.setSpacing(6)

        # Header
        header = QHBoxLayout()
        header.setSpacing(6)
        icon = GlowLabel("▣", CYAN, 10, True)
        icon.setStyleSheet(f"color: {CYAN}; border: none;")
        header.addWidget(icon)
        title = GlowLabel("PIPELINE TERMINAL", PINK, 10, True)
        title.setStyleSheet(f"color: {PINK}; letter-spacing: 3px; font-weight: bold; border: none;")
        header.addWidget(title)
        header.addStretch()

        self._status_dot = PulsingDot(GREEN, 6)
        header.addWidget(self._status_dot)
        self._status_lbl = GlowLabel("STANDBY", CYAN_DIM, 8, True)
        self._status_lbl.setStyleSheet(f"color: {CYAN_DIM}; border: none;")
        header.addWidget(self._status_lbl)

        frame_lay.addLayout(header)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: rgba(0, 212, 255, 40);")
        frame_lay.addWidget(div)

        # Scrollable terminal area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: rgba(0, 0, 0, 0);
                width: 4px;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {CYAN};
                border-radius: 2px;
                min-height: 15px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        self.terminal_content = QWidget()
        self.terminal_content.setStyleSheet("background: transparent;")
        self.terminal_layout = QVBoxLayout(self.terminal_content)
        self.terminal_layout.setContentsMargins(4, 4, 4, 4)
        self.terminal_layout.setSpacing(2)
        self.terminal_layout.addStretch()

        self.scroll.setWidget(self.terminal_content)
        frame_lay.addWidget(self.scroll)

        # Footer with animated data-flow bar
        footer = QHBoxLayout()
        footer.setContentsMargins(4, 4, 4, 0)
        self._footer_lbl = GlowLabel("AWAITING PIPELINE EVENT...", CYAN_DIM, 7, True)
        self._footer_lbl.setStyleSheet(f"color: {CYAN_DIM}; border: none;")
        footer.addWidget(self._footer_lbl)
        footer.addStretch()
        self._line_count_lbl = GlowLabel("LINES: 0", CYAN_DIM, 7, True)
        self._line_count_lbl.setStyleSheet(f"color: {CYAN_DIM}; border: none;")
        footer.addWidget(self._line_count_lbl)
        frame_lay.addLayout(footer)

        self._line_count = 0
        self._max_lines = 200  # Keep memory in check

        # Boot sequence
        from datetime import datetime
        boot_time = datetime.now().strftime("%H:%M:%S")
        self._add_line_internal(f"[{boot_time}] ◈ GRACE PIPELINE TERMINAL v2.0", "system")
        self._add_line_internal(f"[{boot_time}] ◈ CONNECTED TO BACKEND NODE.JS SERVER", "system")
        self._add_line_internal("─" * 52, "separator")

    def add_line(self, text, color_type="dim"):
        """Public API — called via signal from the pipeline."""
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self._add_line_internal(f"[{ts}] {text}", color_type)

    def _add_line_internal(self, text, color_type):
        # Remove oldest lines if too many
        if self._line_count > self._max_lines:
            item = self.terminal_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
            self._line_count -= 1

        line = CyberTerminalLine(text, color_type, self.terminal_content)
        # Insert before the stretch
        self.terminal_layout.insertWidget(self.terminal_layout.count() - 1, line)
        self._line_count += 1
        self._line_count_lbl.setText(f"LINES: {self._line_count}")

        # Auto-scroll to bottom
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        vbar = self.scroll.verticalScrollBar()
        vbar.setValue(vbar.maximum())

    def set_active(self):
        """Called when the pipeline starts processing."""
        self._status_lbl.setText("ACTIVE")
        self._status_lbl.setStyleSheet(f"color: {GREEN}; border: none;")
        self._footer_lbl.setText("PROCESSING PIPELINE...")

    def set_idle(self):
        """Called when the pipeline finishes processing."""
        self._status_lbl.setText("STANDBY")
        self._status_lbl.setStyleSheet(f"color: {CYAN_DIM}; border: none;")
        self._footer_lbl.setText("AWAITING PIPELINE EVENT...")

    def add_separator(self):
        """Add a visual separator line."""
        self._add_line_internal("─" * 52, "separator")

# ──────────────────────────────────────────
# CIRCUIT BOARD BACKGROUND (Animated Faint Traces)
# ──────────────────────────────────────────
class CircuitBoardBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._phase = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(50)
        
    def _animate(self):
        self._phase += 0.05
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Faint cyan traces
        pen = QPen(QColor(0, 212, 255, 12)) 
        pen.setWidth(1)
        painter.setPen(pen)
        
        w = self.width()
        h = self.height()
        if w == 0 or h == 0: return
        
        # Hardcoded proportional paths for circuit traces
        lines = [
            (0.1*w, 0.2*h, 0.3*w, 0.2*h),
            (0.3*w, 0.2*h, 0.3*w, 0.5*h),
            (0.3*w, 0.5*h, 0.6*w, 0.5*h),
            
            (0.8*w, 0.1*h, 0.8*w, 0.4*h),
            (0.8*w, 0.4*h, 0.5*w, 0.4*h),
            (0.5*w, 0.4*h, 0.5*w, 0.8*h),
            
            (0.15*w, 0.8*h, 0.35*w, 0.8*h),
            (0.35*w, 0.8*h, 0.35*w, 0.6*h),
            
            (0.9*w, 0.7*h, 0.7*w, 0.7*h),
            (0.7*w, 0.7*h, 0.7*w, 0.9*h)
        ]
        
        for lx1, ly1, lx2, ly2 in lines:
            painter.drawLine(int(lx1), int(ly1), int(lx2), int(ly2))
            
        # Draw microchips (rectangles)
        painter.setBrush(QColor(0, 0, 0, 0)) # transparent fill
        painter.drawRect(int(0.05*w), int(0.15*h), int(0.05*w), int(0.1*h))
        painter.drawRect(int(0.75*w), int(0.35*h), int(0.08*w), int(0.1*h))
        painter.drawRect(int(0.45*w), int(0.75*h), int(0.06*w), int(0.06*h))
        
        # Draw animated data packets moving along paths
        packet_color = QColor(0, 212, 255, 40) # Slightly brighter than traces
        painter.setBrush(packet_color)
        painter.setPen(Qt.PenStyle.NoPen)
        
        for i, (lx1, ly1, lx2, ly2) in enumerate(lines):
            # smooth back and forth movement using sin
            t = (math.sin(self._phase + i*1.3) + 1) / 2.0
            px = lx1 + (lx2 - lx1) * t
            py = ly1 + (ly2 - ly1) * t
            painter.drawEllipse(QPoint(int(px), int(py)), 2, 2)


# ──────────────────────────────────────────
# PRESENCE ORB WIDGET (Expanding Ripple Rings)
# ──────────────────────────────────────────
class PresenceOrb(QWidget):
    NUM_RINGS = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 140)
        self._phase = 0.0
        self._amplitude = 0.0
        self._color = CYAN
        self._core_radius = 28
        self._max_ring_expand = 30  # how far rings travel outward

        # 60fps internal timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def _tick(self):
        # Speed scales with amplitude: idle ~0.01, speaking ~0.02-0.035
        speed = 0.01 + self._amplitude * 0.025
        self._phase += speed
        self.update()

    def set_phase(self, phase):
        # Keep for compatibility but internal timer drives animation
        pass

    def set_amplitude(self, amp):
        self._amplitude = min(1.0, max(0.0, amp))

    def set_color(self, hex_color):
        self._color = hex_color

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2

        amp = self._amplitude
        phase = self._phase

        # Dynamic core: breathes gently, swells with amplitude
        breath = (math.sin(phase * 2.0) + 1) / 2  # 0..1
        core_r = self._core_radius + breath * 3 + amp * 6

        # Soft inner glow fill
        glow_alpha = int(15 + breath * 20 + amp * 40)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(parse_color(self._color, glow_alpha))
        gr = core_r + 8 + amp * 12
        p.drawEllipse(QPointF(cx, cy), gr, gr)

        # Core circle outline
        core_alpha = int(160 + breath * 40 + amp * 55)
        core_width = 1.5 + amp * 0.5
        p.setPen(QPen(parse_color(self._color, min(255, core_alpha)), core_width))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), core_r, core_r)

        # --- Three expanding ripple rings ---
        # Each ring is staggered by 1/3 of a cycle
        max_expand = self._max_ring_expand + amp * 20
        for i in range(self.NUM_RINGS):
            # Stagger each ring evenly across the cycle
            ring_phase = (phase + i * (2 * math.pi / self.NUM_RINGS)) % (2 * math.pi)
            # Normalize to 0..1 (one full expansion cycle)
            t = ring_phase / (2 * math.pi)

            ring_r = core_r + t * max_expand
            # Fade out as ring expands: full alpha at t=0, zero at t=1
            ring_alpha = int((1.0 - t) * (100 + amp * 100))
            ring_width = max(0.5, (1.0 - t) * (1.5 + amp * 1.0))

            if ring_alpha > 2:
                p.setPen(QPen(parse_color(self._color, min(255, ring_alpha)), ring_width))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(QPointF(cx, cy), ring_r, ring_r)

        p.end()

# ──────────────────────────────────────────
# CONTEXT PANEL (Togglable Split View)
# ──────────────────────────────────────────
class ContextPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mode = "presence"
        self._orb_phase = 0.0
        self.setMaximumWidth(0) # Initially hidden
        self.setMinimumWidth(0)
        
        self.setStyleSheet(f"background: #020404; border-left: 1px solid {CYAN};")
        
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(14, 14, 14, 14)
        
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("border: none; background: transparent;")
        self.lay.addWidget(self.stack)
        
        self.presence_widget = QWidget()
        p_lay = QVBoxLayout(self.presence_widget)
        p_lay.addStretch()
        
        self.orb = PresenceOrb()
        p_lay.addWidget(self.orb, 0, Qt.AlignmentFlag.AlignHCenter)
        
        lbl_grace = GlowLabel("GRACE", CYAN_DIM, 9)
        lbl_grace.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p_lay.addWidget(lbl_grace)
        
        p_lay.addStretch()
        self.stack.addWidget(self.presence_widget)
        
        self.scene_widget = QWidget()
        s_lay = QVBoxLayout(self.scene_widget)
        s_lay.setContentsMargins(0, 0, 0, 0)
        
        spaced_text = " ".join("◆ DETECTED CONTEXT: FILE OPERATION")
        self.lbl_scene_top = GlowLabel(spaced_text, CYAN, 9)
        s_lay.addWidget(self.lbl_scene_top)
        
        card = QWidget()
        card.setStyleSheet(f"background: rgba(10, 22, 34, 0.4); border: 1px solid {BORDER}; border-radius: 4px;")
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(0, 0, 0, 0)
        
        header = QWidget()
        header.setStyleSheet("background: #0a1622; border-bottom: 1px solid rgba(0, 212, 255, 0.2);")
        h_lay = QVBoxLayout(header)
        h_lay.setContentsMargins(8, 6, 8, 6)
        lbl_preview = GlowLabel("[ DIRECTORY PREVIEW ]", CYAN_MID, 9)
        lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_lay.addWidget(lbl_preview)
        c_lay.addWidget(header)
        
        self.lbl_tree = QLabel()
        self.lbl_tree.setFont(mono(10))
        self.lbl_tree.setStyleSheet("color: rgba(0, 212, 255, 0.8); background: transparent; border: none; padding: 10px;")
        c_lay.addWidget(self.lbl_tree)
        
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {BORDER};")
        c_lay.addWidget(div)
        
        stats_widget = QWidget()
        stats_widget.setStyleSheet("background: transparent; border: none;")
        st_lay = QHBoxLayout(stats_widget)
        st_lay.setContentsMargins(10, 8, 10, 8)
        
        self.lbl_free_space = GlowLabel("FREE SPACE: ---", CYAN_MID, 8)
        self.lbl_last_backup = GlowLabel("LAST BACKUP: ---", CYAN_MID, 8)
        st_lay.addWidget(self.lbl_free_space)
        st_lay.addStretch()
        st_lay.addWidget(self.lbl_last_backup)
        c_lay.addWidget(stats_widget)
        
        s_lay.addWidget(card)
        s_lay.addStretch()
        self.stack.addWidget(self.scene_widget)

    def update_audio(self, wave_data):
        if self.mode == "presence" and wave_data:
            amp = max(wave_data)
            self.orb.set_amplitude(amp)

    def paintEvent(self, e):
        super().paintEvent(e)
        if self.mode == "presence" and self.width() > 10:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(QPen(parse_color(CYAN, 30), 1))
            
            path = QPainterPath()
            w, h = self.width(), self.height()
            
            path.moveTo(w*0.1, h*0.2)
            path.lineTo(w*0.3, h*0.2)
            path.lineTo(w*0.4, h*0.3)
            
            path.moveTo(w*0.8, h*0.7)
            path.lineTo(w*0.6, h*0.7)
            path.lineTo(w*0.5, h*0.6)
            
            p.drawPath(path)

    sig_scene_done = pyqtSignal()

    def set_presence_mode(self):
        self.mode = "presence"
        self.stack.setCurrentWidget(self.presence_widget)
        self.sig_scene_done.emit()

    def set_scene_mode(self, directory, file_changed, operation="NEW"):
        import os
        import shutil
        from datetime import datetime
        
        self.mode = "scene"
        
        # Build REAL directory tree from the actual filesystem
        self.lbl_tree.setTextFormat(Qt.TextFormat.RichText)
        cyan_rgba = "rgba(0, 212, 255, 0.8)"
        dim_cyan = "rgba(0, 212, 255, 0.5)"
        
        # Resolve actual directory path
        real_dir = directory if os.path.isdir(directory) else os.path.dirname(directory)
        dir_display = os.path.basename(real_dir) or real_dir
        
        tree_text = f"<span style='color:{cyan_rgba}'>└─ {dir_display}/</span><br>"
        
        # List REAL contents from the filesystem
        try:
            entries = sorted(os.listdir(real_dir))
            dirs = [e for e in entries if os.path.isdir(os.path.join(real_dir, e)) and not e.startswith('.')]
            files = [e for e in entries if os.path.isfile(os.path.join(real_dir, e)) and not e.startswith('.')]
            
            # Show up to 5 directories
            for i, d in enumerate(dirs[:5]):
                connector = "├" if (i < len(dirs[:5]) - 1 or files) else "└"
                tree_text += f"&nbsp;&nbsp;&nbsp;<span style='color:{dim_cyan}'>{connector}─ {d}/</span><br>"
            if len(dirs) > 5:
                tree_text += f"&nbsp;&nbsp;&nbsp;<span style='color:{dim_cyan}'>├─ ... +{len(dirs) - 5} more</span><br>"
            
            # Show up to 5 files, highlight the changed one
            shown_files = files[:5]
            for i, f in enumerate(shown_files):
                is_last = (i == len(shown_files) - 1 and len(files) <= 5)
                connector = "└" if is_last else "├"
                if f == file_changed:
                    op_color = PINK if operation in ["NEW", "DELETE"] else AMBER
                    tree_text += f"&nbsp;&nbsp;&nbsp;{connector}─ <span style='color:{cyan_rgba}'>{f}</span> <span style='color:{op_color}; font-size: 10px; font-weight: bold;'>[{operation}]</span><br>"
                else:
                    tree_text += f"&nbsp;&nbsp;&nbsp;<span style='color:{dim_cyan}'>{connector}─ {f}</span><br>"
            
            if len(files) > 5:
                tree_text += f"&nbsp;&nbsp;&nbsp;<span style='color:{dim_cyan}'>└─ ... +{len(files) - 5} more files</span><br>"
            
            # If the changed file wasn't in the listing, add it at the bottom
            if file_changed not in files and file_changed not in dirs:
                op_color = PINK if operation in ["NEW", "DELETE"] else AMBER
                tree_text += f"&nbsp;&nbsp;&nbsp;└─ <span style='color:{cyan_rgba}'>{file_changed}</span> <span style='color:{op_color}; font-size: 10px; font-weight: bold;'>[{operation}]</span><br>"
                
        except (PermissionError, FileNotFoundError):
            tree_text += f"&nbsp;&nbsp;&nbsp;└─ <span style='color:{cyan_rgba}'>{file_changed}</span> <span style='color:{PINK}; font-size: 10px; font-weight: bold;'>[{operation}]</span><br>"
        
        self.lbl_tree.setText(tree_text)
        
        # Get REAL free space
        try:
            usage = shutil.disk_usage(real_dir)
            free_gb = usage.free / (1024 ** 3)
            if free_gb >= 1000:
                free_str = f"{free_gb / 1024:.1f} TB"
            else:
                free_str = f"{free_gb:.1f} GB"
        except Exception:
            free_str = "N/A"
        self.lbl_free_space.setText(f"FREE SPACE: {free_str}")
        
        # Get REAL last modified time of the file
        try:
            file_path = os.path.join(real_dir, file_changed)
            if os.path.exists(file_path):
                mtime = os.path.getmtime(file_path)
                dt = datetime.fromtimestamp(mtime)
                mod_str = dt.strftime("%Y-%m-%d %H:%M")
            else:
                mod_str = "JUST NOW"
        except Exception:
            mod_str = "N/A"
        self.lbl_last_backup.setText(f"MODIFIED: {mod_str}")
        
        self.stack.setCurrentWidget(self.scene_widget)
        
        # Auto-revert to presence mode after 8 seconds
        if hasattr(self, '_revert_timer'):
            self._revert_timer.stop()
        else:
            self._revert_timer = QTimer(self)
            self._revert_timer.setSingleShot(True)
            self._revert_timer.timeout.connect(self.set_presence_mode)
        self._revert_timer.start(8000)


# ──────────────────────────────────────────
# HOLOGRAPHIC CALENDAR WINDOW (Slim Cyberpunk)
# ──────────────────────────────────────────

class HoloCalendarWidget(QDialog):
    WINDOW_W = 420

    def __init__(self, calendar_data, parent=None):
        super().__init__(parent)
        self.calendar_data = calendar_data
        self._drag_pos = None
        self._scan_phase = 0.0
        self._border_phase = 0.0

        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.init_ui()

        # Calculate height dynamically based on event count (slim!)
        event_count = len(calendar_data.get('events', []))
        base_h = 120  # header + footer
        per_event = 72
        self.WINDOW_H = min(550, max(200, base_h + event_count * per_event))

        # Position: right side of screen
        screen = QGuiApplication.primaryScreen().geometry()
        self._x_pos = screen.width() - self.WINDOW_W - 40
        self._y_pos = max(60, screen.height() // 2 - self.WINDOW_H // 2)

        self.setGeometry(self._x_pos, self._y_pos, 4, self.WINDOW_H)
        self.setWindowOpacity(0.0)

        # ── Opening Animation ──
        self.anim_group = QSequentialAnimationGroup(self)

        op = QPropertyAnimation(self, b"windowOpacity")
        op.setDuration(150)
        op.setStartValue(0.0)
        op.setEndValue(1.0)

        geom = QPropertyAnimation(self, b"geometry")
        geom.setDuration(300)
        geom.setStartValue(QRect(self._x_pos + self.WINDOW_W, self._y_pos, 4, self.WINDOW_H))
        geom.setEndValue(QRect(self._x_pos, self._y_pos, self.WINDOW_W, self.WINDOW_H))
        geom.setEasingCurve(QEasingCurve.Type.OutExpo)

        self.anim_group.addAnimation(op)
        self.anim_group.addAnimation(geom)

        # ── Animated scanline & border pulse ──
        self._scan_timer = QTimer(self)
        self._scan_timer.timeout.connect(self._tick_scan)
        self._scan_timer.start(30)

    def _tick_scan(self):
        self._scan_phase += 0.008
        if self._scan_phase > 1.3:
            self._scan_phase = -0.3
        self._border_phase += 0.03
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        self.anim_group.start()
        self.glitch_overlay.start_glitch(500)
        QTimer.singleShot(450, self.populate_data)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        if w < 10 or h < 10:
            return

        # ── Deep radial gradient background ──
        radial = QRadialGradient(w * 0.5, h * 0.3, max(w, h) * 0.8)
        radial.setColorAt(0.0, QColor(5, 15, 25, 240))
        radial.setColorAt(0.4, QColor(2, 5, 10, 245))
        radial.setColorAt(1.0, QColor(1, 2, 4, 250))
        p.setBrush(QBrush(radial))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, w, h, 6, 6)

        # ── Subtle horizontal scanline sweep ──
        scan_y = int(self._scan_phase * h)
        scan_grad = QLinearGradient(0, scan_y - 30, 0, scan_y + 30)
        scan_grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        scan_grad.setColorAt(0.5, QColor(0, 212, 255, 18))
        scan_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(0, scan_y - 30, w, 60, scan_grad)
        # Thin bright line at center
        p.setPen(QPen(QColor(0, 212, 255, 35), 1))
        p.drawLine(0, scan_y, w, scan_y)

        # ── Glowing animated border ──
        pulse = int(25 + 15 * math.sin(self._border_phase))
        border_color = QColor(0, 212, 255, pulse)
        p.setPen(QPen(border_color, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(1, 1, w - 2, h - 2, 6, 6)

        # ── Corner accents (bright blue tick marks) ──
        accent = QColor(0, 212, 255, 150)
        p.setPen(QPen(accent, 2))
        corner_len = 18
        # Top-left
        p.drawLine(2, 2, 2 + corner_len, 2)
        p.drawLine(2, 2, 2, 2 + corner_len)
        # Top-right
        p.drawLine(w - 2, 2, w - 2 - corner_len, 2)
        p.drawLine(w - 2, 2, w - 2, 2 + corner_len)
        # Bottom-left
        p.drawLine(2, h - 2, 2 + corner_len, h - 2)
        p.drawLine(2, h - 2, 2, h - 2 - corner_len)
        # Bottom-right
        p.drawLine(w - 2, h - 2, w - 2 - corner_len, h - 2)
        p.drawLine(w - 2, h - 2, w - 2, h - 2 - corner_len)

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(0)

        # ── Header ──
        header = QHBoxLayout()
        header.setSpacing(8)

        icon = QLabel("◈")
        icon.setFont(mono(10, True))
        icon.setFixedSize(20, 20)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("color: #00D4FF; border: 1px solid rgba(0,212,255,0.6); border-radius: 10px; background: rgba(0,212,255,0.08);")
        header.addWidget(icon)

        title = QLabel("CHRONOS")
        title.setFont(mono(10, True))
        title.setStyleSheet("color: #00D4FF; letter-spacing: 3px; background: transparent; border: none;")
        header.addWidget(title)

        # Subtle status dot
        dot = QLabel("●")
        dot.setFont(mono(6))
        dot.setStyleSheet("color: #00D4FF; background: transparent; border: none;")
        header.addWidget(dot)

        subtitle = QLabel("LIVE")
        subtitle.setFont(mono(7, True))
        subtitle.setStyleSheet("color: rgba(0,212,255,0.6); letter-spacing: 2px; background: transparent; border: none;")
        header.addWidget(subtitle)

        header.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(24, 24)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton { color: #00D4FF; background: transparent; border: 1px solid rgba(0,212,255,0.3); font-size: 11px; font-weight: bold; }
            QPushButton:hover { background: rgba(0,212,255,0.2); border: 1px solid #00D4FF; }
        """)
        btn_close.clicked.connect(self.close_window)
        header.addWidget(btn_close)

        root.addLayout(header)

        # ── Divider ──
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 transparent, stop:0.3 rgba(0,212,255,80), stop:0.7 rgba(0,212,255,80), stop:1 transparent);")
        root.addSpacing(6)
        root.addWidget(div)
        root.addSpacing(8)

        # ── Scroll Area for events ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background: transparent; width: 4px; }
            QScrollBar::handle:vertical { background: rgba(0,212,255,0.4); border-radius: 2px; min-height: 20px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(6)
        self.scroll_layout.setContentsMargins(0, 0, 4, 0)

        scroll.setWidget(self.scroll_content)
        root.addWidget(scroll)

        # ── Footer ──
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 6, 0, 0)
        f_lbl = QLabel("◇ GOOGLE CALENDAR API")
        f_lbl.setFont(mono(7))
        f_lbl.setStyleSheet("color: rgba(0,212,255,0.35); background: transparent; border: none; letter-spacing: 1px;")
        footer.addWidget(f_lbl)
        footer.addStretch()

        from datetime import datetime
        ts_lbl = QLabel(datetime.now().strftime("%H:%M:%S IST"))
        ts_lbl.setFont(mono(7))
        ts_lbl.setStyleSheet("color: rgba(0,212,255,0.35); background: transparent; border: none;")
        footer.addWidget(ts_lbl)
        root.addLayout(footer)

        # ── Glitch overlay ──
        self.glitch_overlay = GlitchOverlay(self)
        self.glitch_overlay.setGeometry(0, 0, self.WINDOW_W, 600)
        self.glitch_overlay.raise_()

    def populate_data(self):
        events = self.calendar_data.get('events', [])
        if not events:
            lbl = QLabel("NO EVENTS FOUND")
            lbl.setFont(mono(9))
            lbl.setStyleSheet("color: rgba(0,212,255,0.5); background: transparent; border: none;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.scroll_layout.addWidget(lbl)
        else:
            from datetime import datetime
            for i, ev in enumerate(events):
                card = QFrame()
                card.setStyleSheet("""
                    QFrame {
                        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                            stop:0 rgba(0,212,255,0.06), stop:1 rgba(0,212,255,0.02));
                        border-left: 2px solid rgba(0,212,255,0.5);
                        border-bottom: 1px solid rgba(0,212,255,0.08);
                    }
                """)
                card_lay = QHBoxLayout(card)
                card_lay.setContentsMargins(10, 8, 10, 8)
                card_lay.setSpacing(10)

                # ── Time badge ──
                start_str = ev.get('start', '')
                try:
                    dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                    time_str = dt.strftime("%I:%M %p")
                    date_str = dt.strftime("%b %d")
                except Exception:
                    time_str = "—"
                    date_str = start_str[:10] if len(start_str) >= 10 else "—"

                time_badge = QFrame()
                time_badge.setFixedWidth(62)
                time_badge.setStyleSheet("background: rgba(0,212,255,0.1); border: 1px solid rgba(0,212,255,0.2); border-radius: 3px;")
                tb_lay = QVBoxLayout(time_badge)
                tb_lay.setContentsMargins(4, 4, 4, 4)
                tb_lay.setSpacing(0)

                t1 = QLabel(time_str)
                t1.setFont(mono(8, True))
                t1.setStyleSheet("color: #00D4FF; background: transparent; border: none;")
                t1.setAlignment(Qt.AlignmentFlag.AlignCenter)
                tb_lay.addWidget(t1)

                t2 = QLabel(date_str)
                t2.setFont(mono(7))
                t2.setStyleSheet("color: rgba(0,212,255,0.6); background: transparent; border: none;")
                t2.setAlignment(Qt.AlignmentFlag.AlignCenter)
                tb_lay.addWidget(t2)

                card_lay.addWidget(time_badge)

                # ── Event info ──
                info_lay = QVBoxLayout()
                info_lay.setSpacing(2)

                summary = ev.get('summary', 'Untitled')
                s_lbl = QLabel(summary)
                s_lbl.setFont(mono(9, True))
                s_lbl.setStyleSheet("color: #E0F7FA; background: transparent; border: none;")
                s_lbl.setWordWrap(True)
                info_lay.addWidget(s_lbl)

                desc = ev.get('description', '')
                if desc:
                    d_lbl = QLabel(desc[:80] + ("…" if len(desc) > 80 else ""))
                    d_lbl.setFont(sans(8))
                    d_lbl.setStyleSheet("color: rgba(224,247,250,0.55); background: transparent; border: none;")
                    d_lbl.setWordWrap(True)
                    info_lay.addWidget(d_lbl)

                card_lay.addLayout(info_lay)

                # ── Fade-in animation per card ──
                opacity_fx = QGraphicsOpacityEffect(card)
                card.setGraphicsEffect(opacity_fx)
                opacity_fx.setOpacity(0.0)
                anim = QPropertyAnimation(opacity_fx, b"opacity")
                anim.setDuration(300)
                anim.setStartValue(0.0)
                anim.setEndValue(1.0)
                anim.setEasingCurve(QEasingCurve.Type.InOutSine)
                QTimer.singleShot(i * 120, anim.start)
                # prevent garbage collection
                card._fade_anim = anim

                self.scroll_layout.addWidget(card)

        self.scroll_layout.addStretch()

    def close_window(self):
        self.glitch_overlay.start_glitch(350)
        # Reverse slide animation
        close_anim = QPropertyAnimation(self, b"geometry")
        close_anim.setDuration(250)
        close_anim.setStartValue(self.geometry())
        close_anim.setEndValue(QRect(self.x() + self.WINDOW_W, self.y(), 4, self.height()))
        close_anim.setEasingCurve(QEasingCurve.Type.InExpo)

        fade = QPropertyAnimation(self, b"windowOpacity")
        fade.setDuration(200)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)

        group = QParallelAnimationGroup(self)
        group.addAnimation(close_anim)
        group.addAnimation(fade)
        group.finished.connect(self.accept)
        group.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'glitch_overlay'):
            self.glitch_overlay.setGeometry(0, 0, self.width(), self.height())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if hasattr(self, '_drag_pos') and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()
