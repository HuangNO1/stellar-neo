import sys
from PyQt6.QtWidgets import QApplication
# 從 app.py 匯入 MainWindow
from app import MainWindow
from pathlib import Path
from core.env_patch import patch_qt_platform

def load_stylesheet(file_path: Path) -> str:
    """從檔案讀取樣式表，並處理可能的錯誤。"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"警告: 樣式表檔案未找到: {file_path}")
        return ""
    except Exception as e:
        print(f"錯誤: 無法讀取樣式表檔案: {e}")
        return ""

def main():
    patch_qt_platform()
    app = QApplication(sys.argv)

    # 獲取當前 main.py 檔案所在的目錄
    current_dir = Path(__file__).parent
    # 組合出 splitter.qss 的絕對路徑
    qss_file_path = current_dir / "assets" / "style" / "splitter.qss"

    splitter_style = load_stylesheet(qss_file_path)
    if splitter_style:
        app.setStyleSheet(splitter_style)

    # 實例化 MainWindow
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
