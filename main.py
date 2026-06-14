import sys
import threading
import os
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import qInstallMessageHandler
from gui.hud import GraceHUD
from core.pipeline import run_pipeline, latency_monitor_thread, rag_monitor_thread

# Suppress harmless QPainter threading warnings that flood the terminal.
# These are caused by background threads emitting signals that trigger
# UI repaints which occasionally collide with active paint cycles.
_SUPPRESSED = ("QPainter", "QBackingStore", "QPaintDevice", "QWidgetEffectSourcePrivate")

def _qt_msg_handler(mode, context, message):
    if any(s in message for s in _SUPPRESSED):
        return
    print(message)

qInstallMessageHandler(_qt_msg_handler)

load_dotenv(os.path.join("backend", ".env"))

def main():
    app = QApplication(sys.argv)
    hud = GraceHUD()
    hud.show()

    pipeline_thread = threading.Thread(target=run_pipeline, args=(hud,), daemon=True)
    pipeline_thread.start()

    latency_thread = threading.Thread(target=latency_monitor_thread, args=(hud,), daemon=True)
    latency_thread.start()
    
    rag_thread = threading.Thread(target=rag_monitor_thread, args=(hud,), daemon=True)
    rag_thread.start()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
