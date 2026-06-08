import math
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QLabel, QFrame, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy, QGraphicsOpacityEffect
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
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

