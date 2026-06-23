
code = '''
# ──────────────────────────────────────────
# PRESENCE ORB WIDGET
# ──────────────────────────────────────────
class PresenceOrb(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 140)
        self._phase = 0.0

    def set_phase(self, phase):
        self._phase = phase
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() // 2, self.height() // 2
        
        pulse = (math.sin(self._phase) + 1) / 2
        glow_radius = 10 + pulse * 14
        
        orb_r = 35
        p.setPen(QPen(parse_color(CYAN, 200), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(cx - orb_r, cy - orb_r, orb_r * 2, orb_r * 2)
        
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(parse_color(CYAN, int(20 + pulse * 40)))
        p.drawEllipse(int(cx - orb_r - glow_radius/2), int(cy - orb_r - glow_radius/2), int(orb_r * 2 + glow_radius), int(orb_r * 2 + glow_radius))

        ring1_scale = 1.0 + (self._phase % (2 * math.pi)) / (2 * math.pi) * 0.15
        ring1_alpha = int(127 * (1.0 - (ring1_scale - 1.0) / 0.15))
        r1 = int(orb_r * ring1_scale)
        p.setPen(QPen(parse_color(CYAN, max(10, ring1_alpha)), 1))
        p.drawEllipse(cx - r1, cy - r1, r1 * 2, r1 * 2)

        phase2 = (self._phase + math.pi) % (2 * math.pi)
        ring2_scale = 1.0 + phase2 / (2 * math.pi) * 0.15
        ring2_alpha = int(127 * (1.0 - (ring2_scale - 1.0) / 0.15))
        r2 = int(orb_r * ring2_scale)
        p.setPen(QPen(parse_color(CYAN, max(10, ring2_alpha)), 1))
        p.drawEllipse(cx - r2, cy - r2, r2 * 2, r2 * 2)

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
        
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._tick)
        self.anim_timer.start(50)

    def _tick(self):
        if self.mode == "presence" and self.width() > 10:
            self._orb_phase = (self._orb_phase + 0.05)
            self.orb.set_phase(self._orb_phase)
            self.presence_widget.update()

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

    def set_presence_mode(self):
        self.mode = "presence"
        self.stack.setCurrentWidget(self.presence_widget)

    def set_scene_mode(self, directory, file_changed, free_space="UNKNOWN", last_backup="UNKNOWN"):
        self.mode = "scene"
        
        tree_text = f"└─ {directory}\n"
        tree_text += f"   ├─ config/\n"
        tree_text += f"   ├─ src/\n"
        
        self.lbl_tree.setTextFormat(Qt.TextFormat.RichText)
        cyan_rgba = "rgba(0, 212, 255, 0.8)"
        tree_text += f"   └─ <span style='color:{cyan_rgba}'>{file_changed}</span> <span style='color:{PINK}; font-size: 10px; font-weight: bold;'>[NEW]</span>"
        
        self.lbl_tree.setText(tree_text)
        self.lbl_free_space.setText(f"FREE SPACE: {free_space}")
        self.lbl_last_backup.setText(f"LAST BACKUP: {last_backup}")
        self.stack.setCurrentWidget(self.scene_widget)
'''

with open('d:/PERSONAL/GRACE/gui/components.py', 'a', encoding='utf-8') as f:
    f.write('\n' + code + '\n')
print('Appended ContextPanel')
