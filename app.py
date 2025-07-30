# app.py (重構後的主框架)
import os
from PyQt6.QtCore import QSize, QEventLoop, QTimer, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFrame, QHBoxLayout
from qfluentwidgets import (FluentWindow, NavigationInterface, FluentIcon,
                            setTheme, SystemThemeListener, SplashScreen,
                            NavigationItemPosition, SubtitleLabel, setFont, MessageBox)

# 匯入核心元件和新建立的頁面
from core.config import THEMES
from core.settings_manager import SettingsManager
from core.translator import Translator
from core.asset_manager import AssetManager  # 導入資源管理器

# 導入所有頁面
from ui.pages.view_settings import SettingsView
from ui.pages.view_gallery import GalleryView
from ui.pages.view_logo import LogoView  # 導入 Logo 頁面
from ui.pages.view_font import FontView  # 導入字體頁面


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()

        # --- 1. 核心元件初始化 ---
        self.settings = SettingsManager()
        self.translator = Translator()
        self.asset_manager = AssetManager()  # 實例化資源管理器
        self.themeListener = SystemThemeListener(self)

        # --- 2. 啟動介面邏輯 ---
        self.splashScreen = SplashScreen(QIcon('assets/logos/canon.png'), self)
        self.splashScreen.setIconSize(QSize(102, 102))
        self.show()

        # --- 3. 載入初始設定 ---
        self._load_initial_settings()

        # --- 4. 初始化主視窗和導覽 ---
        self.init_window()
        # 注意：FluentWindow 會自動建立 self.navigationInterface
        self.init_navigation()

        # --- 5. 模擬載入並關閉啟動介面 ---
        self.createSubInterface()
        self.splashScreen.finish()

    def _load_initial_settings(self):
        """在建立任何UI之前載入設定"""
        lang_code = self.settings.get("language", "en")
        self.translator.load(lang_code, os.path.abspath("i18n"))

        theme_name = self.settings.get("theme", "System")
        setTheme(THEMES.get(theme_name, THEMES["System"]))
        if theme_name == "System":
            self.themeListener.start()

    def init_window(self):
        """設定主視窗屬性"""
        self.resize(1500, 800)
        self.setWindowIcon(QIcon("assets/logos/canon.png"))
        self.setWindowTitle("Stellar NEO")

    def init_navigation(self):
        tr = self.translator.get
        """建立並新增所有子頁面到導覽列"""
        # 實例化子頁面，並傳入需要的管理器
        self.gallery_view = GalleryView(self.translator, self)
        self.logo_view = LogoView(self.asset_manager,self.translator, self)
        self.font_view = FontView(self.asset_manager,self.translator,  self)
        self.settings_view = SettingsView(self.translator, self.settings, self.themeListener, self)

        # 新增主要頁面
        self.addSubInterface(self.gallery_view, FluentIcon.PHOTO, tr("gallery", "圖片工坊"))
        self.addSubInterface(self.logo_view, FluentIcon.BRUSH, tr("logo_management", "Logo 管理"))
        self.addSubInterface(self.font_view, FluentIcon.FONT, tr("font_management", "字體管理"))

        self.navigationInterface.addSeparator()

        # 新增底部的設定頁面
        self.addSubInterface(
            self.settings_view,
            FluentIcon.SETTING,
            tr("settings", "Settings"),
            position=NavigationItemPosition.BOTTOM
        )

        # 連接設定頁面發出的信號
        self.settings_view.languageChanged.connect(self._show_restart_dialog)

    def _show_restart_dialog(self):
        """顯示一個提示框，告知使用者需要重啟"""
        tr = self.translator.get
        title = tr("language_changed_title", "Language Changed")
        content = tr("language_changed_body",
                     "The language setting has been saved. Please restart the application for the changes to take full effect.")
        w = MessageBox(title, content, self)
        w.yesButton.setText(tr("ok", "OK"))
        w.cancelButton.setText(tr("cancel", "Cancel"))

        # 當對話方塊被接受 (使用者點擊 "OK") 時，關閉應用程式
        if w.exec():
            self.close()

    def createSubInterface(self):
        """模擬耗時的初始化操作"""
        loop = QEventLoop(self)
        QTimer.singleShot(1000, loop.quit)
        loop.exec()

    def closeEvent(self, e):
        """關閉應用程式時，確保監聽器執行緒被終止"""
        if self.themeListener.isRunning():
            self.themeListener.quit()
            self.themeListener.wait()
        super().closeEvent(e)
