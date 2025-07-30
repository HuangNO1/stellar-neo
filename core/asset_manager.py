# asset_manager.py (修改後)

import os
import shutil
from pathlib import Path
from PyQt6.QtGui import QFontDatabase


class AssetManager:
    """
    管理使用者上傳的資源與應用程式的預設資源。
    """

    def __init__(self):
        # --- 使用者資源路徑 ---
        # 存放在使用者 home 目錄下，每個電腦使用者獨立
        self.base_dir = Path.home() / ".stellar-neo"
        self.user_logos_dir = self.base_dir / "logos"
        self.user_fonts_dir = self.base_dir / "fonts"
        self.user_logos_dir.mkdir(parents=True, exist_ok=True)
        self.user_fonts_dir.mkdir(parents=True, exist_ok=True)

        # --- 應用程式預設資源路徑 ---
        # 假設在應用程式執行檔同級有一個名為 assets 的資料夾
        # 這是唯讀的，用於存放內建資源
        self.default_assets_dir = Path("assets")
        self.default_logos_dir = self.default_assets_dir / "logos"
        # 應用程式應確保此路徑存在，例如在安裝時建立
        self.default_logos_dir.mkdir(parents=True, exist_ok=True)  # 確保路徑存在

        # 用來追蹤使用者上傳的字體路徑及其對應的家族名稱
        self.user_font_data = {}  # 格式: {font_path: [family1, family2], ...}

        # 應用程式啟動時載入所有已儲存的使用者字體
        self.load_all_user_fonts()

    # --- Logo 管理 ---

    def add_logo(self, source_path: str) -> (bool, str):
        """將使用者上傳的 Logo 複製到使用者專屬的 Logo 目錄"""
        source = Path(source_path)
        # 目標路徑變更為使用者 Logo 目錄
        destination = self.user_logos_dir / source.name
        try:
            shutil.copy(source, destination)
            return True, str(destination)
        except Exception as e:
            print(f"無法複製 Logo: {e}")
            return False, ""

    def get_user_logos(self) -> list[str]:
        """【新】獲取所有使用者上傳的 Logo 路徑"""
        if not self.user_logos_dir.exists():
            return []
        return [str(f) for f in self.user_logos_dir.iterdir() if f.is_file()]

    def get_default_logos(self) -> list[str]:
        """【新】獲取所有應用程式預設的 Logo 路徑"""
        if not self.default_logos_dir.exists():
            return []
        return [str(f) for f in self.default_logos_dir.iterdir() if f.is_file()]

    def delete_logo(self, logo_path: str):
        """刪除指定的使用者 Logo"""
        try:
            os.remove(logo_path)
            return True
        except Exception as e:
            print(f"無法刪除 Logo: {e}")
            return False

    # --- 字體管理 ---

    def add_font(self, source_path: str) -> (bool, str):
        """將使用者上傳的字體檔案複製到資源目錄並載入到應用程式"""
        source = Path(source_path)
        destination = self.user_fonts_dir / source.name

        if destination.exists():
            self._load_font_and_update_map(str(destination))
            return True, destination.stem

        try:
            shutil.copy(source, destination)
            font_id = QFontDatabase.addApplicationFont(str(destination))
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                self.user_font_data[str(destination)] = families
                return True, destination.stem
            else:
                os.remove(destination)
                return False, "Failed to load font"
        except Exception as e:
            print(f"無法複製字體: {e}")
            return False, str(e)

    def get_system_fonts(self) -> list[str]:
        """【新】獲取所有系統安裝的字體家族名稱"""
        # QFontDatabase.families() 返回系統和 addApplicationFont 加載的所有字體
        # 我們需要從中排除掉使用者上傳的字體
        system_families = set(QFontDatabase.families())
        user_families = set()
        for families in self.user_font_data.values():
            user_families.update(families)

        # 從所有字體中減去使用者字體，剩下的就是系統字體
        return sorted(list(system_families - user_families))

    def get_user_fonts(self) -> dict:
        """【新】獲取使用者上傳的字體路徑與其家族名稱的映射"""
        return self.user_font_data

    def delete_font(self, font_path: str):
        """刪除字體檔案 (注意：可能需要重啟應用才能完全從 QFontDatabase 移除)"""
        try:
            if font_path in self.user_font_data:
                del self.user_font_data[font_path]
            QFontDatabase.removeApplicationFont(font_path)
            os.remove(font_path)
            return True
        except Exception as e:
            print(f"無法刪除字體: {e}")
            return False

    def load_all_user_fonts(self):
        """載入使用者字體目錄中的所有字體到應用程式"""
        for font_file in self.user_fonts_dir.glob("*.*"):
            if font_file.is_file() and str(font_file) not in self.user_font_data:
                self._load_font_and_update_map(str(font_file))

    def _load_font_and_update_map(self, font_path: str):
        """輔助函式：載入單個字體並更新追蹤字典"""
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            self.user_font_data[font_path] = families