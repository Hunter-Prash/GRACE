import re

with open(r"d:\PERSONAL\GRACE\gui\components.py", "r", encoding="utf-8") as f:
    content = f.read()

# We need to find the correct `self.anim.start()` and remove the garbage that follows it.
# The garbage looks like: `|class HoloSearchWindow(QWidget): ... self.anim.start()|class HoloSearchWindow(QWidget): ... def showEvent(self, event): ... self.anim.start()`

# Let's just find everything from the FIRST `class HoloSearchWindow` down to `def resizeEvent`.
start_marker = "class HoloSearchWindow"
end_marker = "    def resizeEvent(self, event):"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx != -1 and end_idx != -1:
    before = content[:start_idx]
    after = content[end_idx:]
    
    clean_class = '''class HoloSearchWindow(QWidget):
    WINDOW_W = 820
    WINDOW_H = 750

    def __init__(self, search_data, parent=None):
        super().__init__(parent)
        self.search_data = search_data
        self._drag_pos = None
        self._card_widgets = []

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.network_manager = QNetworkAccessManager(self)

        self.init_ui()
        self.populate_data()

        parent_w = parent.width() if parent else 1920
        parent_h = parent.height() if parent else 1080
        
        self._y_pos = max(20, parent_h // 2 - self.WINDOW_H // 2)
        self._x_hidden = parent_w
        self._x_visible = parent_w - self.WINDOW_W - 30

        self.setGeometry(self._x_hidden, self._y_pos, self.WINDOW_W, self.WINDOW_H)

    def showEvent(self, event):
        super().showEvent(event)
        
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(400)
        self.anim.setStartValue(QPoint(self._x_hidden, self._y_pos))
        self.anim.setEndValue(QPoint(self._x_visible, self._y_pos))
        self.anim.setEasingCurve(QEasingCurve.Type.OutExpo)
        self.anim.start()

        # Trigger glitch during opening
        self.glitch_overlay.start_glitch(600)

        # Sequential card pop-in after expansion finishes
        QTimer.singleShot(450, self._animate_cards_in)

'''
    
    with open(r"d:\PERSONAL\GRACE\gui\components.py", "w", encoding="utf-8") as f:
        f.write(before + clean_class + after)
    print("Cleaned!")
else:
    print("Could not find markers.")
