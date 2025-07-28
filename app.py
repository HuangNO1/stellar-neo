import os
import sys

# 匯入 uic 模組
from PyQt6 import uic
from PyQt6.QtCore import QTimer, QSize, QEventLoop
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import setTheme, FluentWindow, isDarkTheme, SystemThemeListener, SplashScreen

# 匯入設定檔，這部分和之前一樣
from core.config import LANGUAGES, THEMES
from core.settings_manager import SettingsManager
from core.translator import Translator


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()

        self.splashScreen = SplashScreen(QIcon('assets/logos/canon.png'), self)
        self.splashScreen.setIconSize(QSize(102, 102))


        # 使用 uic.loadUi 載入 UI 檔案，並將其元件附加到 self
        uic.loadUi("ui/components/test.ui", self)

        self.settings = SettingsManager()
        self.translator = Translator()

        # 反向對應字典，方便從設定值找到顯示名稱
        self.reverse_lang_map = {v: k for k, v in LANGUAGES.items()}

        self.themeListener = SystemThemeListener(self)

        self._init_ui()
        self._connect_signals()

        # 2. 在创建其他子页面前先显示主界面
        self.show()

        # 3. 创建子界面
        self.createSubInterface()

        # 4. 隐藏启动页面
        self.splashScreen.close()

    def _init_ui(self):
        """初始化 UI 狀態，包括載入設定和填充元件"""
        # 1. 動態填充下拉框 (注意：現在直接用 self.languageComboBox)
        self.languageComboBox.addItems(LANGUAGES.keys())
        self.themeComboBox.addItems(THEMES.keys())

        # 2. 載入並套用語言設定
        lang_code = self.settings.get("language", "en")
        lang_name = self.reverse_lang_map.get(lang_code, "English")
        self.languageComboBox.setCurrentText(lang_name)
        # 初始載入一次翻譯
        self.translator.load(lang_code, os.path.abspath("i18n"))
        self._update_ui_texts()  # 使用載入的翻譯更新介面

        # 3. 載入並套用主題設定
        theme_name = self.settings.get("theme", "System")
        self.themeComboBox.setCurrentText(theme_name)
        setTheme(THEMES.get(theme_name, THEMES["System"]))

    def _connect_signals(self):
        """連接所有元件的訊號與槽"""
        self.languageComboBox.currentTextChanged.connect(self._on_language_changed)
        self.themeComboBox.currentTextChanged.connect(self._on_theme_changed)
        # self.applyButton.clicked.connect(self._on_apply_clicked)

    def _on_language_changed(self, lang_name: str):
        """當語言下拉框變化時，即時載入新語言並更新 UI 文字"""
        lang_code = LANGUAGES.get(lang_name, "en")
        self.translator.load(lang_code, os.path.abspath("i18n"))
        self._update_ui_texts()
        # **自動儲存語言設定**
        self.settings.set("language", lang_code)
        print(f"Language setting automatically saved: {lang_code}")

    def _on_theme_changed(self, theme_name: str):
        """當主題下拉框變化時，即時套用新主題"""
        theme = THEMES.get(theme_name, THEMES["System"])
        setTheme(theme)
        if theme == "System":
            # 创建主题监听器
            self.themeListener.start()
        else:
            self.themeListener.terminate()

        # **自動儲存主題設定**
        self.settings.set("theme", theme_name)
        print(f"Theme setting automatically saved: {theme_name}")

    # def _on_apply_clicked(self):
    #     """當點擊套用按鈕時，儲存目前選擇的設定"""
    #     lang_name = self.languageComboBox.currentText()
    #     theme_name = self.themeComboBox.currentText()
    #
    #     self.settings.set("language", LANGUAGES.get(lang_name, "en"))
    #     self.settings.set("theme", theme_name)
    #
    #     print("Settings saved!")

    def _update_ui_texts(self):
        """使用目前載入的翻譯器更新介面所有文字"""
        tr = self.translator.get
        # 更新視窗標題
        self.setWindowTitle(tr("title", "Settings Example"))

        # 更新標籤文字
        self.languageLabel.setText(tr("language", "Language"))
        self.themeLabel.setText(tr("theme", "Theme"))

        # 更新按鈕文字
        self.applyButton.setText(tr("apply", "Apply"))

        # 更新主題下拉框中的選項文字
        self.themeComboBox.blockSignals(True)
        current_text = self.themeComboBox.currentText()
        self.themeComboBox.clear()

        # 建立一個暫存的對應，用於找到更新後的選項
        translated_map = {}
        for key in THEMES.keys():
            translated_text = tr(key.lower(), key)
            self.themeComboBox.addItem(translated_text)
            translated_map[key] = translated_text

        # 嘗試恢復之前的選項
        # 我們需要從原始的英文 key (如 "Light") 找到翻譯後的文字 (如 "淺色")
        current_key = next((k for k, v in THEMES.items() if v == THEMES.get(current_text)), None)
        if not current_key:  # 如果找不到，就用設定檔中的
            current_key = self.settings.get("theme", "System")

        self.themeComboBox.setCurrentText(translated_map.get(current_key, translated_map["System"]))

        self.themeComboBox.blockSignals(False)

    def closeEvent(self, e):
        # 停止监听器线程
        self.themeListener.terminate()
        self.themeListener.deleteLater()
        super().closeEvent(e)

    def _onThemeChangedFinished(self):
        super()._onThemeChangedFinished()

        # 云母特效启用时需要增加重试机制
        if self.isMicaEffectEnabled():
            QTimer.singleShot(100, lambda: self.windowEffect.setMicaEffect(self.winId(), isDarkTheme()))

    def createSubInterface(self):
        loop = QEventLoop(self)
        QTimer.singleShot(1000, loop.quit)
        loop.exec()
