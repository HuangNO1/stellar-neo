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
from ui.pages.view_settings import SettingsView
from ui.pages.view_gallery import GalleryView  # 確保您已建立此佔位檔案


# 像範例中一樣，建立一個簡單的佔位符 Widget 用於子頁面
class SimpleWidget(QFrame):
    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.setObjectName(text.replace(' ', '-'))
        self.label = SubtitleLabel(text, self)
        self.hBoxLayout = QHBoxLayout(self)
        setFont(self.label, 24)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hBoxLayout.addWidget(self.label, 1, Qt.AlignmentFlag.AlignCenter)


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()

        # --- 1. 核心元件初始化 ---
        self.settings = SettingsManager()
        self.translator = Translator()
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
        self.setWindowTitle("My Application")

    def init_navigation(self):
        tr = self.translator.get
        """建立並新增所有子頁面到導覽列"""
        # 實例化子頁面
        self.gallery_view = GalleryView(self)
        # self.sub_gallery_view = SimpleWidget("Sub Gallery Page", self)
        self.settings_view = SettingsView(self.translator, self.settings, self.themeListener, self)

        # 使用 self.addSubInterface 直接新增導覽項
        self.addSubInterface(
            self.gallery_view,
            FluentIcon.PHOTO,
            tr("gallery", "Gallery")
        )
        # 新增巢狀子項目到 "Gallery" 頁面下
        # self.addSubInterface(
        #     self.sub_gallery_view,
        #     FluentIcon.FOLDER,
        #     self.translator.get("gallery", "Gallery"),
        #     parent=self.gallery_view,
        # )

        # if self.init_nav_times <= 1:
        self.navigationInterface.addSeparator()

        # 使用 NavigationItemPosition 枚舉來設定位置
        self.addSubInterface(
            self.settings_view,
            FluentIcon.SETTING,
            tr("settings", "Settings"),
            position=NavigationItemPosition.BOTTOM
        )

        # 連接設定頁面發出的信號，以便更新全域UI
        self.settings_view.languageChanged.connect(self._show_restart_dialog)

    def _show_restart_dialog(self):
        """顯示一個提示框，告知使用者需要重啟"""
        tr = self.translator.get
        title = tr("language_changed_title", "Language Changed")
        content = tr("language_changed_body",
                     "The language setting has been saved. Please restart the application for the changes to take "
                     "full effect.")

        # 創建一個模態對話方塊
        w = MessageBox(title, content, self)

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
