import sys
sys.path.append('d:/PERSONAL/GRACE')
from PyQt6.QtWidgets import QApplication
from gui.components import HoloSearchWindow
import traceback

app = QApplication(sys.argv)
search_data = {'query': 'AC 4 Black Flag Resynced game remake release date details', 'results': [{'title': 'Test', 'content': 'Test', 'url': 'Test'}], 'images': []}
try:
    hw = HoloSearchWindow(search_data)
    print("Success!")
except Exception as e:
    traceback.print_exc()
