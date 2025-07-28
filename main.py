import sys
from PyQt6.QtWidgets import QApplication
# 從 app.py 匯入 MainWindow
from app import MainWindow


def main():
    app = QApplication(sys.argv)
    # 實例化 MainWindow
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
