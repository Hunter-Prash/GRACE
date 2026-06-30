import re

with open(r"d:\PERSONAL\GRACE\gui\components.py", "r", encoding="utf-8") as f:
    code = f.read()

# Replace class definition and init
old_init = r'''class HoloSearchWindow\(QDialog\):
    WINDOW_W = 820
    WINDOW_H = 750

    def __init__\(self, search_data, parent=None\):
        super\(\)\.__init__\(parent\)
        self.search_data = search_data
        self._drag_pos = None
        self._card_widgets = \[\]

        # Frameless, translucent, always-on-top
        self.setWindowFlags\(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        \)
        self.setAttribute\(Qt.WidgetAttribute.WA_TranslucentBackground\)

        self.network_manager = QNetworkAccessManager\(self\)

        self.init_ui\(\)
        self.populate_data\(\)

.*?self\.anim_group\.addAnimation\(geom\)

    def showEvent\(self, event\):
        super\(\)\.showEvent\(event\)
        self\.anim_group\.start\(\)'''

new_init = '''class HoloSearchWindow(QWidget):
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
        self.anim.start()'''

code = re.sub(old_init, new_init, code, flags=re.DOTALL)

with open(r"d:\PERSONAL\GRACE\gui\components.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Patched!")
