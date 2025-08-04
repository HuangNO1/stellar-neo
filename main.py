import os
import sys

sys.path.append(os.path.dirname(__file__))

from pathlib import Path

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

from app import MainWindow
from core.env_patch import patch_qt_platform
from core.utils import resource_path_str


def setup_application(app: QApplication):
    """
    執行應用程式啟動前的所有設定任務，包括字體和樣式表。
    """
    current_dir = Path(__file__).parent

    # --- 1. 設定全域應用程式字體 ---
    font_path = resource_path_str("assets/fonts/font.ttf")
    if os.path.exists(font_path):
        font_id = QFontDatabase.addApplicationFont(str(font_path))
        if font_id != -1:
            font_families = QFontDatabase.applicationFontFamilies(font_id)
            if font_families:
                font_family = font_families[0]
                print(f"成功載入預設字體：'{font_family}'，路徑：{font_path}")
                default_font = QFont(font_family)
                app.setFont(default_font)
            else:
                print(f"警告：無法從 {font_path} 獲取字體家族名稱。")
        else:
            print(f"警告：無法載入字體檔案：{font_path}")
    else:
        print(f"警告：預設字體檔案未找到：{font_path}")

    # --- 2. 載入並套用 QSS 樣式表 ---
    qss_file_path = resource_path_str("assets/style/splitter.qss")
    try:
        with open(qss_file_path, "r", encoding="utf-8") as f:
            splitter_style = f.read()
            app.setStyleSheet(splitter_style)
    except FileNotFoundError:
        print(f"警告: 樣式表檔案未找到: {qss_file_path}")
    except Exception as e:
        print(f"錯誤: 無法讀取樣式表檔案: {e}")


def main():
    """
    應用程式主入口點。
    """
    # 平台修補
    patch_qt_platform()

    # 建立應用程式實例
    app = QApplication(sys.argv)

    # 執行所有設定任務
    setup_application(app)

    # 實例化並顯示主視窗
    window = MainWindow()
    window.show()

    # 進入應用程式主循環
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
