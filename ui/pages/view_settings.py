# ui/pages/view_settings.py
import os
from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import setTheme, SystemThemeListener

# 匯入設定檔
from core.config import LANGUAGES, THEMES
from core.settings_manager import SettingsManager
from core.translator import Translator


class SettingsView(QWidget):
    # 這個信號現在的意義是: "語言已變更，需要重啟"
    languageChanged = pyqtSignal()

    def __init__(self, translator: Translator, settings: SettingsManager, theme_listener: SystemThemeListener,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsView")

        self.translator = translator
        self.settings = settings
        self.themeListener = theme_listener
        uic.loadUi("ui/components/settings.ui", self)

        self.reverse_lang_map = {v: k for k, v in LANGUAGES.items()}
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """初始化此頁面的 UI 狀態"""
        self.languageComboBox.addItems(LANGUAGES.keys())
        self.themeComboBox.addItems(THEMES.keys())

        lang_code = self.settings.get("language", "en")
        lang_name = self.reverse_lang_map.get(lang_code, "English")
        self.languageComboBox.setCurrentText(lang_name)

        theme_name = self.settings.get("theme", "System")
        self.themeComboBox.setCurrentText(theme_name)

        if hasattr(self, 'applyButton'):
            self.applyButton.setVisible(False)

        self._update_ui_texts()

    def _connect_signals(self):
        self.languageComboBox.currentTextChanged.connect(self._on_language_changed)
        self.themeComboBox.currentTextChanged.connect(self._on_theme_changed)

    def _on_language_changed(self, lang_name: str):
        """語言改變時，僅儲存設定並發射信號"""
        lang_code = LANGUAGES.get(lang_name, "en")

        # 檢查語言是否真的改變了，避免不必要的儲存和提示
        if self.settings.get("language") == lang_code:
            return

        self.settings.set("language", lang_code)
        print(f"Language setting saved: {lang_code}. Restart required.")

        # 發射信號，通知主視窗處理重啟提示
        self.languageChanged.emit()

    def _on_theme_changed(self, theme_name: str):
        """主題改變時，套用主題、儲存設定並管理監聽器"""
        theme = THEMES.get(theme_name, THEMES["System"])
        setTheme(theme)

        if theme_name == "System":
            self.themeListener.start()
        else:
            if self.themeListener.isRunning():
                self.themeListener.quit()

        self.settings.set("theme", theme_name)
        print(f"Theme setting automatically saved: {theme_name}")

    def _update_ui_texts(self):
        """僅更新此頁面內的 UI 文字（在初始載入時呼叫）"""
        tr = self.translator.get
        self.languageLabel.setText(tr("language", "Language"))
        self.themeLabel.setText(tr("theme", "Theme"))

        self.themeComboBox.blockSignals(True)
        current_theme_setting = self.settings.get("theme", "System")
        self.themeComboBox.clear()
        translated_map = {key: tr(key.lower(), key) for key in THEMES.keys()}
        self.themeComboBox.addItems(translated_map.values())
        self.themeComboBox.setCurrentText(translated_map.get(current_theme_setting, translated_map["System"]))
        self.themeComboBox.blockSignals(False)

