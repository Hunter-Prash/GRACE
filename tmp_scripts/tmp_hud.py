import re

with open('d:/PERSONAL/GRACE/gui/hud.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the literal \n from previous script
content = content.replace('sig_env_toggle = pyqtSignal(str)\\n    sig_context_scene = pyqtSignal(dict)', 
                          'sig_env_toggle = pyqtSignal(str)\n    sig_context_scene = pyqtSignal(dict)')
content = content.replace('self.sig_context_scene.connect(self._on_context_scene)\\n        self.sig_env_toggle.connect(',
                          'self.sig_context_scene.connect(self._on_context_scene)\n        self.sig_env_toggle.connect(')

# Add shortcut to __init__
content = content.replace('self._build_ui()', 'self._build_ui()\n        QShortcut(QKeySequence("Ctrl+Shift+L"), self).activated.connect(self._toggle_context_panel)')

# Replace _center_panel
center_panel_code = '''    def _center_panel(self):
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

        tabs.addTab(self.panel_log, "LOG")'''

start_idx = content.find('    def _center_panel(self):')
end_idx = content.find('        # Tab 2: MANAGE CONVERSATION HISTORY')
if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + center_panel_code + '\n' + content[end_idx:]
else:
    print('Failed to find _center_panel bounds')

# Add missing methods at the bottom of the class
methods_code = '''
    def _toggle_context_panel(self):
        self.context_panel_open = not self.context_panel_open
        self.context_anim.stop()
        
        if self.context_panel_open:
            # Approx 50% width
            target_w = self.panel_log.width() // 2
            self.context_anim.setStartValue(self.context_panel.width())
            self.context_anim.setEndValue(target_w)
            # Remove old connections
            self.context_anim.finished.disconnect() if self.context_anim.receivers(self.context_anim.Signal("finished")) else None
            self.context_anim.finished.connect(lambda: self.context_panel.setMaximumWidth(16777215))
            self.context_anim.start()
        else:
            self.context_panel.setMaximumWidth(self.context_panel.width())
            self.context_anim.setStartValue(self.context_panel.width())
            self.context_anim.setEndValue(0)
            self.context_anim.finished.disconnect() if self.context_anim.receivers(self.context_anim.Signal("finished")) else None
            self.context_anim.start()

    def _on_context_scene(self, data):
        if not self.context_panel_open:
            self._toggle_context_panel()
        self.context_panel.set_scene_mode(
            directory=data.get('directory', 'UNKNOWN DIR'),
            file_changed=data.get('file_changed', 'UNKNOWN FILE'),
            free_space=data.get('free_space', 'UNKNOWN'),
            last_backup=data.get('last_backup', 'UNKNOWN')
        )
'''

end_of_class = content.find('# ──────────────────────────────────────────\n# STANDALONE DEMO RUN')
if end_of_class != -1:
    content = content[:end_of_class] + methods_code + '\n' + content[end_of_class:]
else:
    print("Failed to find STANDALONE DEMO RUN")
    content += methods_code

with open('d:/PERSONAL/GRACE/gui/hud.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done modifying hud.py')
