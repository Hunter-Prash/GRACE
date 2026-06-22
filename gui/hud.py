import time
import math
import os
import GPUtil
import psutil
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame, QTabWidget, QPushButton
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QPen, QFont, QShortcut, QKeySequence
from gui.theme import CYAN, GREEN, PINK, AMBER, BG, BG2, TEXT_DIM, BORDER, CYAN_DIM, CYAN_MID, mono, parse_color
from gui.components import ContextPanel, GlowLabel, CyberPanel, StatBar, AudioMonitorWidget, SmallWaveformWidget, StateIndicator, StatusRing, ChatBubble, CyberButton, TelemetryBar, TelemetryMetric, PulsingDot, MatrixRain, ContextSaturationRing, AnimatedSidePane, AnimatedMapPane, MapToggleTab, DangerConfirmDialog, ToasterMessage, DailyBriefingPanel, HoloSearchWindow, CircuitBoardBackground
from gui.enrollment import VoiceEnrollmentDialog

class GraceHUD(QMainWindow):
    sig_state   = pyqtSignal(str)
    sig_message = pyqtSignal(str, str, list)
    sig_wave    = pyqtSignal(list)
    sig_attach_play = pyqtSignal(object)
    sig_metrics     = pyqtSignal(int, float)
    sig_latency     = pyqtSignal(str)
    sig_text_input  = pyqtSignal(str)
    sig_clear_dynamo = pyqtSignal()
    sig_clear_pinecone = pyqtSignal()
    sig_db_latency  = pyqtSignal(int)
    sig_context_saturation = pyqtSignal(int)
    sig_rag_stats   = pyqtSignal(dict)
    sig_force_sleep = pyqtSignal()
    sig_alert_toaster = pyqtSignal(str)
    sig_clear_context = pyqtSignal()
    sig_map_update  = pyqtSignal(dict)
    sig_search_update = pyqtSignal(dict)
    sig_show_briefing_panel = pyqtSignal(dict)
    sig_env_toggle = pyqtSignal(str)
    sig_context_scene = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GRACE // CORE HUD")
        self.setMinimumSize(1100, 660)
        self.session_start = time.time()
        self.latest_bubble = None
        self.state = "IDLE"
        self.bubble_count  = 0
        self.metrics_pane = None
        self._loading_history = False
        self.search_windows = [] # Keep references to prevent GC

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
                width: 8px;
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
        QShortcut(QKeySequence("Ctrl+Shift+L"), self).activated.connect(self._toggle_context_panel)
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

        self.api_pane = AnimatedSidePane()
        self.map_pane = AnimatedMapPane()
        self.briefing_pane = DailyBriefingPanel()
        
        self.map_tab = MapToggleTab()
        self.map_tab.clicked.connect(self._on_map_tab_clicked)
        
        # Center the tab vertically in its own little layout
        tab_lay = QVBoxLayout()
        tab_lay.addStretch()
        tab_lay.addWidget(self.map_tab)
        tab_lay.addStretch()

        body = QHBoxLayout()
        body.setSpacing(10)
        body.addWidget(self._left_panel(),  0)
        body.addWidget(self._center_panel(), 1)
        body.addWidget(self._right_panel(), 0)
        body.addWidget(self.api_pane, 0)
        body.addWidget(self.map_pane, 0)
        body.addWidget(self.briefing_pane, 0)
        body.addLayout(tab_lay, 0)
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

        # Right Indicator Dots (pulsing animated)
        lights = QWidget()
        lights_lay = QHBoxLayout(lights)
        lights_lay.setContentsMargins(10, 0, 0, 0)
        lights_lay.setSpacing(2)

        # Green = system online, two dim cyan = secondary systems
        dot_online = PulsingDot(GREEN, 7)
        dot_net    = PulsingDot(CYAN,  6)
        dot_ai     = PulsingDot(CYAN,  6)
        # Offset phases so they don't pulse in sync
        dot_net._phase = 1.0
        dot_ai._phase  = 2.1
        for dot in (dot_online, dot_net, dot_ai):
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

        # Network Telemetry Panel
        net_panel = CyberPanel("◈ NETWORK", CYAN)
        nl = QVBoxLayout(net_panel)
        nl.setContentsMargins(12, 16, 12, 12)
        nl.setSpacing(8)
        self.metric_api_latency = TelemetryMetric("GEMINI API", "---ms", AMBER)
        nl.addWidget(self.metric_api_latency)
        self.metric_db_latency = TelemetryMetric("AWS DYNAMODB", "---ms", GREEN)
        nl.addWidget(self.metric_db_latency)
        self.metric_pc_latency = TelemetryMetric("PINECONE DB", "---ms", CYAN)
        nl.addWidget(self.metric_pc_latency)
        lay.addWidget(net_panel)

        lay.addStretch()
        return w

    def _center_panel(self):
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar::tab {{
                background: {BG2};
                color: {CYAN_DIM};
                border: 1px solid {BORDER};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 12px;
                font-family: Consolas, monospace;
                font-size: 10px;
                letter-spacing: 1px;
            }}
            QTabBar::tab:selected {{
                background: transparent;
                color: {CYAN};
                border: 1px solid {CYAN};
                border-bottom: none;
            }}
            QTabBar::tab:hover:!selected {{
                background: rgba(0, 212, 255, 0.1);
            }}
        """)
        
        # Tab 1: CONVERSATION LOG
        self.panel_log = CyberPanel("◈ CONVERSATION LOG", CYAN)
        main_lay = QHBoxLayout(self.panel_log)
        main_lay.setContentsMargins(12, 24, 12, 12)
        main_lay.setSpacing(0)

        # Toggle Button
        self.btn_toggle_context = QPushButton("⛶")
        self.btn_toggle_context.setFixedSize(22, 22)
        self.btn_toggle_context.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_context.setStyleSheet(f"""
            QPushButton {{
                color: {CYAN};
                background: transparent;
                border: 1px solid {BORDER};
                border-radius: 2px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: rgba(0, 212, 255, 0.15);
                border: 1px solid {CYAN};
            }}
        """)
        self.btn_toggle_context.clicked.connect(self._toggle_context_panel)
        self.panel_log.add_header_widget(self.btn_toggle_context)

        # Left Container
        self.left_log_container = QWidget()
        lay = QVBoxLayout(self.left_log_container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        # Context Window Saturation Arc Ring at the very top
        self.bar_context = ContextSaturationRing()
        lay.addWidget(self.bar_context)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_layout.setSpacing(8)
        self.chat_layout.addStretch()
        
        scroll.setWidget(self.chat_container)
        self.scroll_area = scroll
        
        # Overlay container to place animated circuit board behind the transparent scroll area
        from PyQt6.QtWidgets import QGridLayout
        overlap_container = QWidget()
        overlap_lay = QGridLayout(overlap_container)
        overlap_lay.setContentsMargins(0, 0, 0, 0)
        
        self.circuit_bg = CircuitBoardBackground()
        overlap_lay.addWidget(self.circuit_bg, 0, 0)
        overlap_lay.addWidget(scroll, 0, 0)
        
        lay.addWidget(overlap_container, 1)

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
        
        # Right Container (ContextPanel)
        self.context_panel = ContextPanel()
        
        main_lay.addWidget(self.left_log_container, 1)
        main_lay.addWidget(self.context_panel, 0)
        
        self.context_anim = QPropertyAnimation(self.context_panel, b"maximumWidth")
        self.context_anim.setDuration(200)
        self.context_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.context_panel_open = False
        self.context_panel_manual_override = False
        self.context_auto_opened = False

        tabs.addTab(self.panel_log, "LOG")
        # Tab 2: MANAGE CONVERSATION HISTORY
        tab2 = CyberPanel("◈ MANAGE CONTEXT", PINK)
        lay2 = QVBoxLayout(tab2)
        lay2.setContentsMargins(12, 16, 12, 12)
        
        lbl_info = GlowLabel("Manage your Short-Term (DynamoDB) and Long-Term (Pinecone) memory independently.", TEXT_DIM, 9)
        lbl_info.setWordWrap(True)
        lay2.addWidget(lbl_info)
        lay2.addSpacing(10)
        
        self.btn_delete_dynamo = CyberButton("CLEAR DYNAMODB (SHORT-TERM)", AMBER)
        self.btn_delete_dynamo.clicked.connect(self._prompt_clear_dynamo)
        lay2.addWidget(self.btn_delete_dynamo)

        self.btn_delete_pinecone = CyberButton("CLEAR PINECONE (LONG-TERM)", PINK)
        self.btn_delete_pinecone.clicked.connect(self._prompt_clear_pinecone)
        lay2.addWidget(self.btn_delete_pinecone)
        
        lay2.addStretch()
        
        tabs.addTab(tab2, "CONTEXT")
        
        # Tab 3: DATABASES (Pinecone & DynamoDB)
        tab3 = CyberPanel("◈ DATABASE METRICS", GREEN)
        lay3 = QVBoxLayout(tab3)
        lay3.setContentsMargins(12, 16, 12, 12)
        lay3.setSpacing(10)
        
        h1 = QHBoxLayout()
        self.metric_pc_vectors = TelemetryMetric("PINECONE MEMORIES", "---", CYAN)
        self.metric_pc_full    = TelemetryMetric("INDEX FULLNESS", "---%", AMBER)
        h1.addWidget(self.metric_pc_vectors)
        h1.addWidget(self.metric_pc_full)
        lay3.addLayout(h1)
        
        h2 = QHBoxLayout()
        self.metric_dy_rcu = TelemetryMetric("DYNAMODB RCU", "---", PINK)
        self.metric_dy_wcu = TelemetryMetric("DYNAMODB WCU", "---", PINK)
        h2.addWidget(self.metric_dy_rcu)
        h2.addWidget(self.metric_dy_wcu)
        lay3.addLayout(h2)
        
        lay3.addStretch()
        tabs.addTab(tab3, "DATABASES")

        return tabs

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
        r, self.lbl_tokens  = row("TOKENS",   "0")
        sl.addLayout(r)
        r, self.lbl_cost    = row("COST",     "$0.0000", GREEN)
        sl.addLayout(r)
        r, _ = row("MODEL",   "3.1-FLASH-LITE", CYAN_MID)
        sl.addLayout(r)
        r, _ = row("TTS",     "KOKORO-82M", GREEN)
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
        self.btn_train    = CyberButton("TRAIN VOICE", GREEN)
        self.btn_env      = CyberButton("ENV: LOCAL", GREEN)
        self.btn_api_quota = CyberButton("API QUOTA", AMBER)
        self.btn_shutdown = CyberButton("SHUTDOWN", PINK)
        
        self.btn_api_quota.clicked.connect(self.api_pane.toggle)
        self.btn_env.clicked.connect(self._prompt_env_toggle)
        
        ac_lay.addWidget(self.btn_sleep)
        ac_lay.addWidget(self.btn_train)
        ac_lay.addWidget(self.btn_env)
        ac_lay.addWidget(self.btn_api_quota)
        ac_lay.addWidget(self.btn_shutdown)
        lay.addWidget(actions)

        # Matrix Data Stream
        stream_panel = CyberPanel("◈ RAW DATA STREAM", CYAN)
        stream_lay = QVBoxLayout(stream_panel)
        stream_lay.setContentsMargins(12, 16, 12, 12)
        self.matrix_stream = MatrixRain(CYAN_DIM)
        self.matrix_stream.setFixedHeight(90)
        stream_lay.addWidget(self.matrix_stream)
        lay.addWidget(stream_panel)

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
        self.sig_alert_toaster.connect(self.show_toaster)
        self.sig_metrics.connect(self._on_metrics)
        self.sig_latency.connect(self._on_latency)
        self.sig_wave.connect(self.audio_monitor.update_bars)
        self.sig_wave.connect(self.small_wave.update_bars)
        self.sig_wave.connect(self.context_panel.update_audio)
        self.sig_map_update.connect(self.map_pane.process_map_data)
        self.sig_search_update.connect(self._show_search_hologram)
        self.map_pane.sig_data_ready.connect(lambda: self.map_tab.set_glow(True))
        self.sig_db_latency.connect(lambda lat: self.metric_db_latency.set_value(f"{lat}ms"))
        self.sig_context_saturation.connect(lambda count: self.bar_context.set_value(count))
        self.sig_rag_stats.connect(self._on_rag_stats)
        self.sig_clear_context.connect(self.clear_chat_ui)
        self.sig_show_briefing_panel.connect(self.briefing_pane.slide_in)
        self.sig_context_scene.connect(self._on_context_scene)
        self.context_panel.sig_scene_done.connect(self._on_scene_done)
        self.btn_shutdown.clicked.connect(self.close)
        self.btn_train.clicked.connect(self._open_enrollment)
        self.btn_sleep.clicked.connect(self.sig_force_sleep.emit)
        
    def _on_map_tab_clicked(self):
        if self.map_pane.is_open:
            self.map_pane.slide_out()
        else:
            self.map_tab.set_glow(False)
            self.map_pane.slide_in()

    def _open_enrollment(self):
        self.is_enrolling = True
        dialog = VoiceEnrollmentDialog(self)
        dialog.exec()
        self.is_enrolling = False
        
        # Clear backlog audio to prevent accidental triggers from stale mic data
        from core.audio import mic_queue
        with mic_queue.mutex:
            mic_queue.queue.clear()

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
        
        # Revert back to tracking total system RAM so it matches Windows Task Manager exactly
        try:
            self.bar_ram.setValue(int(psutil.virtual_memory().percent))
        except Exception as e:
            print("RAM STAT ERROR:", e)
            self.bar_ram.setValue(0)
            
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                self.bar_gpu.setValue(int(gpus[0].load * 100))
                self.bar_vram.setValue(int(gpus[0].memoryUtil * 100))
        except Exception as e:
            print("GPU STAT ERROR:", e)
            pass

    def _tick_wave(self):
        self._wave_phase += 0.3
        bars = [
            max(0.05, abs(math.sin(self._wave_phase + i * 0.7)) * 0.35)
            for i in range(20)
        ]
        self.audio_monitor.update_bars(bars)
        self.small_wave.update_bars(bars)
        
        # Orb animations
        if hasattr(self, 'state') and self.context_panel_open:
            if self.state == "SPEAKING":
                # Dramatic pulsing while speaking (PINK)
                self.context_panel.orb.set_amplitude(bars[0] * 3.0)
                self.context_panel.orb.set_color(PINK)
            elif self.state == "LISTENING":
                # Gentle pulsing while listening (GREEN)
                self.context_panel.orb.set_amplitude(bars[0] * 1.5)
                self.context_panel.orb.set_color(GREEN)
            else:
                self.context_panel.orb.set_amplitude(0)
                self.context_panel.orb.set_color(CYAN)

    # ── PUBLIC API (state and pipeline) ───
    def _on_state(self, state: str):
        self.state = state
        self.state_ind.set_state(state)
        self.state_ring.set_state(state)
        
        if state == "IDLE":
            self.lbl_input_state.setText("AWAITING INPUT...")
            self.lbl_input_state.setStyleSheet(f"color: {TEXT_DIM}; background: transparent;")
            self.matrix_stream.set_speed("CALM")
            self.matrix_stream.set_color(CYAN_DIM)
            self.context_panel.orb.set_color(CYAN)
            self.context_panel.orb.set_amplitude(0)
        elif state == "LISTENING":
            self.lbl_input_state.setText("LISTENING...")
            self.lbl_input_state.setStyleSheet(f"color: {GREEN}; background: transparent;")
            self.matrix_stream.set_speed("FAST")
            self.matrix_stream.set_color(CYAN_DIM)
            self.context_panel.orb.set_color(GREEN)
        elif state == "PROCESSING":
            self.lbl_input_state.setText("THINKING...")
            self.lbl_input_state.setStyleSheet(f"color: {AMBER}; background: transparent;")
            self.matrix_stream.set_speed("FAST")
            self.matrix_stream.set_color(CYAN_DIM)
            self.context_panel.orb.set_color(AMBER)
        elif state == "SPEAKING":
            self.lbl_input_state.setText("SPEAKING...")
            self.lbl_input_state.setStyleSheet(f"color: {PINK}; background: transparent;")
            self.matrix_stream.set_speed("FAST")
            self.matrix_stream.set_color(PINK)
            self.context_panel.orb.set_color(PINK)
        elif state == "REJECTED":
            self.lbl_input_state.setText("UNKNOWN SPEAKER REJECTED")
            self.lbl_input_state.setStyleSheet(f"color: {PINK}; background: transparent;")
            self.matrix_stream.set_speed("CALM")
            self.matrix_stream.set_color(PINK)
            self.context_panel.orb.set_color(PINK)
            
        self.timer_wave.setInterval(50 if state == "LISTENING" else 40 if state == "SPEAKING" else 80)
        
        # Auto-open ContextPanel when speaking (if not manually overridden)
        if hasattr(self, 'context_panel_manual_override'):
            if state == "SPEAKING":
                if not self.context_panel_open and not self.context_panel_manual_override:
                    self._toggle_context_panel(is_auto=True)
            elif state in ["IDLE", "LISTENING"]:
                # Only auto-close if showing presence orb, NOT if showing a file scene
                if (self.context_panel_open
                        and getattr(self, 'context_auto_opened', False)
                        and not self.context_panel_manual_override
                        and self.context_panel.mode == "presence"):
                    self._toggle_context_panel(is_auto=True)
        
    def _on_rag_stats(self, stats: dict):
        if "pinecone" in stats and stats["pinecone"]:
            pc = stats["pinecone"]
            self.metric_pc_vectors.set_value(str(pc.get("totalVectorCount", 0)))
            self.metric_pc_full.set_value(f"{pc.get('indexFullness', 0) * 100:.1f}%")
            self.metric_pc_latency.set_value(f"{pc.get('latencyMs', 0)}ms")
        if "dynamo" in stats and stats["dynamo"]:
            dy = stats["dynamo"]
            self.metric_dy_rcu.set_value(f"{dy.get('rcu', 0):.1f}")
            self.metric_dy_wcu.set_value(f"{dy.get('wcu', 0):.1f}")

    def _on_message(self, speaker: str, text: str, tools: list):
        if self.latest_bubble:
            try:
                self.latest_bubble.remove_play_button()
            except Exception:
                pass
            self.latest_bubble = None

        if tools:
            tools_str = ", ".join(tools)
            badge_html = f"<br><br><span style='color: gray; font-size: 10px;'><i>🛠️ Tools: {tools_str}</i></span>"
            text += badge_html

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
        
        if speaker == "YOU" or speaker == "GRACE":
            self.bubble_count += 1
            self.lbl_queries.setText(str(self.bubble_count))
            self.api_pane.update_usage(self.bubble_count)
            
        # Only auto-scroll if we're not bulk-loading history
        if not self._loading_history:
            QTimer.singleShot(50, self._smart_scroll)

    def _smart_scroll(self):
        """Only scroll to bottom if user is already near the bottom (within 60px).
        This prevents yanking the user back down when they've scrolled up to re-read."""
        sb = self.scroll_area.verticalScrollBar()
        near_bottom = (sb.maximum() - sb.value()) < 60
        if near_bottom:
            sb.setValue(sb.maximum())

    def _scroll_bottom(self):
        """Force scroll to absolute bottom (used after history load)."""
        sb = self.scroll_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def finish_history_load(self):
        """Called by pipeline after all history bubbles are added."""
        self._loading_history = False
        QTimer.singleShot(100, self._scroll_bottom)

    def clear_chat_ui(self):
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.latest_bubble = None
        self.bubble_count = 0
        self.lbl_queries.setText("0")
        self.api_pane.update_usage(0)

    # ── THREAD-SAFE SETTERS ───────────────
    def set_state(self, state: str):
        self.sig_state.emit(state)

    def add_message(self, speaker: str, text: str, tools: list = None):
        self.sig_message.emit(speaker, text, tools or [])

    def set_waveform(self, bars: list):
        self.sig_wave.emit(bars)

    def _on_attach_play(self, callback):
        if self.latest_bubble:
            self.latest_bubble.add_play_button(callback)

    def _prompt_clear_dynamo(self):
        from PyQt6.QtWidgets import QDialog
        dlg = DangerConfirmDialog("Are you sure you want to erase the current short-term session memory from DynamoDB? You will lose recent context.", self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.sig_clear_dynamo.emit()

    def _prompt_clear_pinecone(self):
        from PyQt6.QtWidgets import QDialog
        dlg = DangerConfirmDialog("Are you sure you want to PERMANENTLY erase ALL long-term memories from Pinecone? This action CANNOT BE UNDONE.", self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.sig_clear_pinecone.emit()
            
    def _prompt_env_toggle(self):
        if "LOCAL" in self.btn_env.text():
            self.btn_env.setText("ENV: CLOUD")
            self.btn_env.set_color(AMBER)
            self.sig_env_toggle.emit("CLOUD")
        else:
            self.btn_env.setText("ENV: LOCAL")
            self.btn_env.glow_color = GREEN
            self.btn_env.update()
            self.sig_env_toggle.emit("LOCAL")

    def _show_search_hologram(self, search_data):
        print(f"[DEBUG] _show_search_hologram TRIGGERED! Data keys: {list(search_data.keys())}", flush=True)
        try:
            hw = HoloSearchWindow(search_data)
            self.search_windows.append(hw)
            hw.finished.connect(lambda: self.search_windows.remove(hw) if hw in self.search_windows else None)
            hw.show()
            print("[DEBUG] HoloSearchWindow instantiated and show() called successfully.", flush=True)
        except Exception as e:
            print(f"[DEBUG] ERROR in _show_search_hologram: {e}", flush=True)

    def show_toaster(self, message):
        self.toaster = ToasterMessage(message, self)

    def attach_play_button_to_latest(self, callback):
        self.sig_attach_play.emit(callback)

    def _on_metrics(self, tokens: int, cost: float):
        self.lbl_tokens.setText(f"{tokens:,}")
        self.lbl_cost.setText(f"${cost:.4f}")

    def _on_latency(self, val):
        self.metric_api_latency.set_value(val)

    def _on_text_send(self):
        text = self.text_input.text().strip()
        if text:
            self.sig_text_input.emit(text)
            self.text_input.clear()



    def _toggle_context_panel(self, is_auto=False):
        self.context_panel_open = not self.context_panel_open
        if not is_auto:
            self.context_panel_manual_override = self.context_panel_open
        else:
            self.context_auto_opened = self.context_panel_open
        self.context_anim.stop()
        
        if self.context_panel_open:
            # Approx 50% width
            target_w = self.panel_log.width() // 2
            self.context_anim.setStartValue(self.context_panel.width())
            self.context_anim.setEndValue(target_w)
            try:
                self.context_anim.finished.disconnect()
            except TypeError:
                pass
            self.context_anim.finished.connect(lambda: self.context_panel.setMaximumWidth(16777215))
            self.context_anim.start()
        else:
            self.context_panel.setMaximumWidth(self.context_panel.width())
            self.context_anim.setStartValue(self.context_panel.width())
            self.context_anim.setEndValue(0)
            try:
                self.context_anim.finished.disconnect()
            except TypeError:
                pass
            self.context_anim.start()

    def _on_context_scene(self, data):
        if not self.context_panel_open:
            self._toggle_context_panel(is_auto=True)
        self.context_panel.set_scene_mode(
            directory=data.get('directory', '.'),
            file_changed=data.get('file_changed', 'unknown'),
            operation=data.get('operation', 'NEW')
        )

    def _on_scene_done(self):
        """Called when scene auto-reverts to presence after 8s. Close panel if not manually pinned."""
        if (self.context_panel_open
                and not self.context_panel_manual_override
                and self.state in ["IDLE", "LISTENING"]):
            self._toggle_context_panel(is_auto=True)

# ──────────────────────────────────────────
# STANDALONE DEMO RUN
