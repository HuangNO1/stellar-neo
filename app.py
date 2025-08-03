# app.py (重構後的主框架)
import os

from PyQt6.QtCore import QSize, QEventLoop, QTimer, QByteArray
from PyQt6.QtGui import QIcon, QScreen
from qfluentwidgets import (FluentWindow, FluentIcon,
                            setTheme, SystemThemeListener, SplashScreen,
                            NavigationItemPosition)

from core.asset_manager import AssetManager  # 導入資源管理器
# 匯入核心元件和新建立的頁面
from core.config import THEMES
from core.settings_manager import SettingsManager
from core.translator import Translator
from ui.customs.custom_icon import MyFluentIcon
from ui.pages.view_font import FontView  # 導入字體頁面
from ui.pages.view_gallery import GalleryView
from ui.pages.view_logo import LogoView  # 導入 Logo 頁面
# 導入所有頁面
from ui.pages.view_settings import SettingsView
from ui.pages.view_about import AboutView


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()

        # --- 1. 核心元件初始化 ---
        self.settings = SettingsManager()
        self.translator = Translator()
        self.asset_manager = AssetManager()  # 實例化資源管理器
        self.themeListener = SystemThemeListener(self)

        # --- 2. 啟動介面邏輯 ---
        self.splashScreen = SplashScreen(QIcon('assets/icons/logo.png'), self)
        self.splashScreen.setIconSize(QSize(300, 300))
        # ‼️ 注意：這裡的 self.show() 應該在 init_window 之後調用，以確保窗口位置正確
        # self.show() # <--- 暫時註解或移動這行

        # --- 3. 載入初始設定 ---
        self._load_initial_settings()

        # --- 4. 初始化主視窗和導覽 ---
        self.init_window()
        # 注意：FluentWindow 會自動建立 self.navigationInterface
        self.init_navigation()

        # --- 將 self.show() 移動到這裡 ---
        self.show()  # 在所有設定完成後再顯示視窗

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

    def _center_on_screen(self):
        """將視窗移動到主螢幕的中央。"""
        center_point = QScreen.availableGeometry(self.screen()).center()
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

    def init_window(self):
        """設定主視窗屬性，並恢復上次的狀態或使其居中。"""
        self.setWindowIcon(QIcon("assets/icons/logo.png"))
        self.setWindowTitle("Stellar NEO")

        # 讀取上次儲存的視窗幾何資訊和狀態
        geometry_b64 = self.settings.get("window_geometry")
        window_state = self.settings.get("window_state")

        # 步驟 1: 優先恢復視窗大小。
        # 如果有儲存的幾何資訊，則恢復它。這會設定好視窗的大小。
        if geometry_b64:
            self.restoreGeometry(QByteArray.fromBase64(geometry_b64.encode('utf-8')))
        else:
            # 如果是首次啟動，沒有任何幾何資訊，則設定一個預設大小。
            self.resize(1500, 800)

        # 步驟 2: 接著，根據儲存的狀態決定是最大化、全螢幕，還是居中。
        if window_state == "maximized":
            self.showMaximized()
        elif window_state == "fullscreen":
            self.showFullScreen()
        else:
            # 如果狀態是 "normal" 或未設定，則將視窗居中。
            # 這會覆蓋掉 restoreGeometry 設定的位置，但保留其設定的大小。
            self._center_on_screen()

    def init_navigation(self):
        tr = self.translator.get
        """建立並新增所有子頁面到導覽列"""
        # 實例化子頁面，並傳入需要的管理器
        self.gallery_view = GalleryView(self.asset_manager, self.translator, self)
        self.logo_view = LogoView(self.asset_manager, self.translator, self)
        self.font_view = FontView(self.asset_manager, self.translator, self)
        self.about_view = AboutView(self.translator, self)
        self.settings_view = SettingsView(self.translator, self.settings, self.themeListener, self)

        # 新增主要頁面
        self.addSubInterface(self.gallery_view, FluentIcon.PHOTO, tr("gallery", "Workshop"))
        self.addSubInterface(self.logo_view, FluentIcon.BRUSH, tr("logo_management", "LOGO Management"))
        self.addSubInterface(self.font_view, FluentIcon.FONT, tr("font_management", "Font Management"))

        self.navigationInterface.addSeparator()

        self.addSubInterface(
            self.about_view,
            MyFluentIcon.INFO,
            tr("about", "About"),
            position=NavigationItemPosition.BOTTOM
        )
        # 新增底部的設定頁面
        self.addSubInterface(
            self.settings_view,
            FluentIcon.SETTING,
            tr("settings", "Settings"),
            position=NavigationItemPosition.BOTTOM
        )

    def createSubInterface(self):
        """模擬耗時的初始化操作"""
        loop = QEventLoop(self)
        QTimer.singleShot(1000, loop.quit)
        loop.exec()


    def closeEvent(self, e):
        """關閉應用程式時，儲存視窗狀態並確保監聽器執行緒被終止"""
        # 儲存視窗大小與位置
        geometry = self.saveGeometry()
        self.settings.set("window_geometry", geometry.toBase64().data().decode('utf-8'))

        # 手動判斷並儲存視窗狀態
        state = "normal"
        if self.isMaximized():
            state = "maximized"
        elif self.isFullScreen():
            state = "fullscreen"
        self.settings.set("window_state", state)

        # 處理現有的 themeListener 邏輯
        if self.themeListener.isRunning():
            self.themeListener.quit()
            self.themeListener.wait()

        super().closeEvent(e)

