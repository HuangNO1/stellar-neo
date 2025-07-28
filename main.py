import sys

from PyQt6.QtCore import QSize, QEventLoop, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
# 從 app.py 匯入 MainWindow
from app import MainWindow
from qfluentwidgets import SplashScreen
from qframelesswindow import FramelessWindow, StandardTitleBar

def main():
    app = QApplication(sys.argv)
    # 實例化 MainWindow
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
