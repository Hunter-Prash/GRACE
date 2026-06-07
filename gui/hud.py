import time
import math
import psutil
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QPushButton, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient
from gui.theme import CYAN, GREEN, PINK, AMBER, BG, BG2, TEXT_DIM, BORDER, CYAN_DIM, CYAN_MID, mono, parse_color
from gui.components import GlowLabel, CyberPanel, StatBar, AudioMonitorWidget, SmallWaveformWidget, StateIndicator, StatusRing, ChatBubble, CyberButton

class GraceHUD(QMainWindow):
    sig_state   = pyqtSignal(str)
    sig_message = pyqtSignal(str, str)
    sig_wave    = pyqtSignal(list)
    sig_attach_play = pyqtSignal(object)
    sig_metrics     = pyqtSignal(int, float)
    sig_latency     = pyqtSignal(str)
    sig_text_input  = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GRACE // CORE HUD")
        self.setMinimumSize(1100, 660)
        self.session_start = time.time()
        self.query_count   = 0
        self.latest_bubble = None

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
        
        from PyQt6.QtWidgets import QLineEdit
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("TYPE MESSAGE...")
        self.text_input.setStyleSheet(f"background: rgba(0, 212, 255, 0.05); color: {CYAN}; border: 1px solid {BORDER}; border-radius: 4px; padding: 4px;")
        self.text_input.setFont(mono(9))
        self.text_input.setMinimumWidth(300)
        self.text_input.returnPressed.connect(self._on_text_send)
        bottom_lay.addWidget(self.text_input)

        self.btn_send = CyberButton("SEND", CYAN)
        self.btn_send.clicked.connect(self._on_text_send)
        bottom_lay.addWidget(self.btn_send)
        
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
        r, self.lbl_latency = row("LATENCY",  "---")
        sl.addLayout(r)
        r, self.lbl_tokens  = row("TOKENS",   "0")
        sl.addLayout(r)
        r, self.lbl_cost    = row("COST",     "$0.0000", GREEN)
        sl.addLayout(r)
        r, _ = row("MODEL",   "3.1-FLASH-LITE", CYAN_MID)
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
        self.sig_attach_play.connect(self._on_attach_play)
        self.sig_metrics.connect(self._on_metrics)
        self.sig_latency.connect(self._on_latency)
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

    def _tick_clock(self):
        # 1. Chennai (IST) local time
        maa_time = time.strftime('%H:%M:%S')
        
        # 2. Silicon Valley (SFO) time calculation (handles US DST approximation)
        now_utc = time.gmtime()
        month = now_utc.tm_mon
        day = now_utc.tm_mday
        
        is_dst = True
        if month < 3 or month > 11:
            is_dst = False
        elif month == 3:
            is_dst = (day >= 8)  # Approximate 2nd Sunday
        elif month == 11:
            is_dst = (day < 7)   # Approximate 1st Sunday
            
        offset_hours = -7 if is_dst else -8
        sfo_epoch = time.time() + (offset_hours * 3600)
        sfo_struct = time.gmtime(sfo_epoch)
        
        sfo_time = time.strftime("%H:%M:%S", sfo_struct)
        sfo_hour = sfo_struct.tm_hour
        
        # 9 AM to 6 PM SFO business hours
        if 9 <= sfo_hour < 18:
            sfo_status = "[ACTIVE]"
        else:
            sfo_status = "[OFF HOURS]"
            
        self.lbl_status.setText(f"SYS ONLINE  |  MAA: {maa_time}  |  SFO: {sfo_time} {sfo_status}")
        
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
        if self.latest_bubble:
            try:
                self.latest_bubble.remove_play_button()
            except Exception:
                pass
            self.latest_bubble = None

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
            self.latest_bubble = bubble
            
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

    def _on_attach_play(self, callback):
        if self.latest_bubble:
            self.latest_bubble.add_play_button(callback)

    def attach_play_button_to_latest(self, callback):
        self.sig_attach_play.emit(callback)

    def _on_metrics(self, tokens: int, cost: float):
        self.lbl_tokens.setText(f"{tokens:,}")
        self.lbl_cost.setText(f"${cost:.4f}")

    def _on_latency(self, latency: str):
        self.lbl_latency.setText(latency)

    def _on_text_send(self):
        text = self.text_input.text().strip()
        if text:
            self.sig_text_input.emit(text)
            self.text_input.clear()


# ──────────────────────────────────────────
# STANDALONE DEMO RUN
