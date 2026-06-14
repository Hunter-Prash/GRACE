import numpy as np
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor

from gui.theme import CYAN, GREEN, PINK, BG, BORDER, mono, parse_color
from gui.components import GlowLabel, CyberPanel, CyberButton
from core.biometrics import enroll_voice, has_voice_profile

class VoiceEnrollmentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GRACE // VOICE ENROLLMENT")
        self.setFixedSize(400, 350)
        self.setStyleSheet(f"background: {BG}; border: 1px solid {BORDER};")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        
        # Audio capture state
        self.is_recording = False
        self.frames = []
        self.record_time = 0
        
        self._build_ui()
        
    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(15)
        
        # Title
        title = GlowLabel("VOICE BIOMETRICS ENROLLMENT", CYAN, 12, True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)
        
        # Status text
        self.lbl_status = GlowLabel("STATUS: READY", GREEN, 9)
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.lbl_status)
        
        # Instructions
        panel = CyberPanel("◈ INSTRUCTIONS", CYAN)
        p_lay = QVBoxLayout(panel)
        p_lay.setContentsMargins(15, 20, 15, 15)
        
        instructions = (
            "To restrict GRACE to your voice only, we need a voice sample.\n\n"
            "1. Click 'START RECORDING'\n"
            "2. Say: 'Hey Mycroft, this is my voice profile for GRACE.'\n"
            "3. Speak clearly for about 5 seconds.\n"
            "4. The system will automatically process and save your profile."
        )
        lbl_inst = QLabel(instructions)
        lbl_inst.setFont(mono(9))
        lbl_inst.setStyleSheet(f"color: {CYAN}; background: transparent; border: none;")
        lbl_inst.setWordWrap(True)
        p_lay.addWidget(lbl_inst)
        lay.addWidget(panel)
        
        # Buttons
        btn_lay = QHBoxLayout()
        self.btn_record = CyberButton("START RECORDING", PINK)
        self.btn_record.clicked.connect(self._start_recording)
        
        self.btn_cancel = CyberButton("CLOSE", CYAN)
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_lay.addWidget(self.btn_cancel)
        btn_lay.addWidget(self.btn_record)
        lay.addLayout(btn_lay)
        
        # Timer for recording
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._record_tick)

    def _start_recording(self):
        self.is_recording = True
        self.frames = []
        self.record_time = 0
        self.lbl_status.setText("STATUS: RECORDING (5s)...")
        self.lbl_status.setStyleSheet(f"color: {PINK};")
        self.btn_record.setEnabled(False)
        self.timer.start(100)  # 100ms ticks
        
        # We need to drain the mic_queue to get fresh audio
        from core.audio import mic_queue
        with mic_queue.mutex:
            mic_queue.queue.clear()

    def _record_tick(self):
        from core.audio import mic_queue
        import queue
        
        # Pull any available frames from the mic queue
        while not mic_queue.empty():
            try:
                data = mic_queue.get_nowait()
                pcm = np.frombuffer(data, dtype=np.int16)
                self.frames.extend(pcm)
            except queue.Empty:
                break
                
        self.record_time += 1
        
        # 50 ticks = 5 seconds
        if self.record_time >= 50:
            self.timer.stop()
            self._process_audio()

    def _process_audio(self):
        self.lbl_status.setText("STATUS: EXTRACTING VOICE PROFILE...")
        self.lbl_status.setStyleSheet(f"color: {GREEN};")
        # Process in UI thread is blocking, but it's okay for a 1-time enrollment dialog
        # Or we can do it in a background thread if we wanted to be perfectly smooth.
        # Let's just do it directly.
        QTimer.singleShot(100, self._do_enroll)
        
    def _do_enroll(self):
        if not self.frames:
            self.lbl_status.setText("STATUS: FAILED - NO AUDIO CAPTURED")
            self.lbl_status.setStyleSheet(f"color: {PINK};")
            self.btn_record.setEnabled(True)
            return
            
        audio_data = np.array(self.frames, dtype=np.int16)
        try:
            enroll_voice(audio_data, sample_rate=16000)
            self.lbl_status.setText("STATUS: PROFILE SAVED SUCCESSFULLY")
            self.btn_record.setText("RE-RECORD")
            self.btn_record.setEnabled(True)
        except Exception as e:
            self.lbl_status.setText(f"STATUS: ERROR - {str(e)}")
            self.lbl_status.setStyleSheet(f"color: {PINK};")
            self.btn_record.setEnabled(True)
