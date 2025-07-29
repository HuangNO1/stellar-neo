import os
import shutil
from pathlib import Path
from PyQt6.QtGui import QFontDatabase


class AssetManager:
    """
    管理使用者上傳的 Logo 和字體資源。
    """

    def __init__(self):
        # 獲取使用者主目錄下的 .yourappname 資料夾作為根目錄
        self.base_dir = Path.home() / ".stellar-neo"
        self.logos_dir = self.base_dir / "logos"
        self.fonts_dir = self.base_dir / "fonts"

        # 建立必要的資料夾
        self.logos_dir.mkdir(parents=True, exist_ok=True)
        self.fonts_dir.mkdir(parents=True, exist_ok=True)

        # 應用程式啟動時載入所有已儲存的字體
        self.load_all_fonts()

    # ... (add_logo, get_logos, delete_logo 函式不變) ...
    def add_logo(self, source_path: str) -> (bool, str):
        """將 Logo 檔案複製到資源目錄"""
        source = Path(source_path)
        destination = self.logos_dir / source.name
        try:
            shutil.copy(source, destination)
            return True, str(destination)
        except Exception as e:
            print(f"無法複製 Logo: {e}")
            return False, ""

    def get_logos(self) -> list[str]:
        """獲取所有已儲存的 Logo 路徑"""
        return [str(f) for f in self.logos_dir.iterdir() if f.is_file()]

    def delete_logo(self, logo_path: str):
        """刪除指定的 Logo"""
        try:
            os.remove(logo_path)
            return True
        except Exception as e:
            print(f"無法刪除 Logo: {e}")
            return False

    def add_font(self, source_path: str) -> (bool, str):
        """將字體檔案複製到資源目錄並載入到應用程式"""
        source = Path(source_path)
        destination = self.fonts_dir / source.name
        try:
            shutil.copy(source, destination)
            # 將字體添加到應用程式的字體資料庫
            if QFontDatabase.addApplicationFont(str(destination)) != -1:
                return True, destination.stem  # 返回字體名
            else:
                # 如果添加失敗，最好刪除已複製的檔案
                os.remove(destination)
                return False, "Failed to load font"
        except Exception as e:
            print(f"無法複製字體: {e}")
            return False, str(e)

    def get_fonts(self) -> list[str]:
        """獲取所有可用的應用程式與系統字體家族名稱"""
        # 【核心修正】
        # 直接在 QFontDatabase 類別上呼叫靜態方法 .families()
        # 這會回傳一個包含所有可用字體 (系統 + 應用程式) 的列表，且無需實例化物件。
        # 這樣就完全避免了 "TypeError: not enough arguments" 的問題。
        families = QFontDatabase.families()
        return sorted(list(set(families)))

    def delete_font(self, font_path: str):
        """刪除字體檔案 (注意：可能需要重啟應用才能完全從 QFontDatabase 移除)"""
        try:
            # 從應用程式資料庫移除
            # 注意：removeApplicationFont 的效果可能因平台和 Qt 版本而異
            if QFontDatabase.removeApplicationFont(font_path):
                 os.remove(font_path)
                 return True
            return False
        except Exception as e:
            print(f"無法刪除字體: {e}")
            return False

    def load_all_fonts(self):
        """載入字體目錄中的所有字體到應用程式"""
        for font_file in self.fonts_dir.glob("*.*"):
            if font_file.is_file():
                QFontDatabase.addApplicationFont(str(font_file))