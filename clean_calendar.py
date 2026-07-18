import re

with open(r"d:\PERSONAL\GRACE\gui\components.py", "r", encoding="utf-8") as f:
    content = f.read()

# The corruption is:
#             Qt.WindowType.Dialog |class HoloSearchWindow(QWidget):
# ...
#         self.anim.start()|
#             Qt.WindowType.FramelessWindowHint |
#             Qt.WindowType.WindowStaysOnTopHint

# Wait, the exact end of the block in my Get-Content output was:
#         self.anim.start()|
#             Qt.WindowType.WindowStaysOnTopHint

# Let's find "Qt.WindowType.Dialog |class HoloSearchWindow"
start_marker = "Qt.WindowType.Dialog |class HoloSearchWindow"
end_marker = "self.anim.start()|"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx != -1 and end_idx != -1:
    before = content[:start_idx]
    # The clean code for what was supposed to be there:
    clean_code = "Qt.WindowType.Dialog |\n            Qt.WindowType.FramelessWindowHint |"
    
    # We skip past `self.anim.start()|`
    after = content[end_idx + len(end_marker):]
    
    with open(r"d:\PERSONAL\GRACE\gui\components.py", "w", encoding="utf-8") as f:
        f.write(before + clean_code + after)
    print("Cleaned HoloCalendarWidget!")
else:
    print("Could not find HoloCalendarWidget corruption markers.")
