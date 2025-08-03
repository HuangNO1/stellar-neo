# ui/pages/view_settings.py
from PyQt6 import uic
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import setTheme, SystemThemeListener, MessageBox

# 匯入設定檔
from core.config import LANGUAGES, THEMES
from core.settings_manager import SettingsManager
from core.translator import Translator
from core.utils import resource_path_str


class SettingsView(QWidget):

    def __init__(self, translator: Translator, settings: SettingsManager, theme_listener: SystemThemeListener,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsView")

        self.translator = translator
        self.settings = settings
        self.themeListener = theme_listener
        uic.loadUi(resource_path_str("ui/components/settings.ui"), self)

        self.reverse_lang_map = {v: k for k, v in LANGUAGES.items()}
        # --- 新增 ---
        # 建立一個空的字典，用於儲存翻譯後的主題名稱與原始英文鍵的對應關係
        self.reverse_theme_map = {}

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """初始化此頁面的 UI 狀態"""
        self.languageComboBox.addItems(LANGUAGES.keys())

        lang_code = self.settings.get("language", "en")
        lang_name = self.reverse_lang_map.get(lang_code, "English")
        self.languageComboBox.setCurrentText(lang_name)

        # 這裡僅設定初始值，下拉框的內容會在 _update_ui_texts 中填充
        theme_name = self.settings.get("theme", "System")
        self.themeComboBox.setCurrentText(theme_name)

        self._update_ui_texts()

    def _connect_signals(self):
        self.languageComboBox.currentTextChanged.connect(self._on_language_changed)
        self.themeComboBox.currentTextChanged.connect(self._on_theme_changed)

    def _on_language_changed(self, lang_name: str):
        """語言改變時，僅儲存設定並發射信號"""
        lang_code = LANGUAGES.get(lang_name, "en")

        if self.settings.get("language") == lang_code:
            return

        self.settings.set("language", lang_code)
        print(f"Language setting saved: {lang_code}. Restart required.")
        self._show_restart_dialog()

    def _on_theme_changed(self, theme_display_name: str):
        """主題改變時，套用主題、儲存設定並管理監聽器"""
        # --- 核心修正 ---
        # 1. 使用反向對應字典，從顯示名稱(如"淺色")找到原始英文鍵(如"Light")
        original_theme_key = self.reverse_theme_map.get(theme_display_name, "System")

        # 2. 使用原始英文鍵從 THEMES 字典中獲取正確的主題物件
        theme = THEMES.get(original_theme_key, THEMES["System"])
        setTheme(theme)

        if original_theme_key == "System":
            self.themeListener.start()
        else:
            if self.themeListener.isRunning():
                self.themeListener.quit()

        # 3. 儲存設定時，也應該儲存原始英文鍵
        self.settings.set("theme", original_theme_key)
        print(f"Theme setting automatically saved: {original_theme_key}")

    def _show_restart_dialog(self):
        """顯示一個提示框，告知使用者需要重啟"""
        tr = self.translator.get
        title = tr("language_changed_title", "Language Changed")
        content = tr("language_changed_body",
                     "The language setting has been saved. Please restart the application for the changes to take full effect.")
        self.w = MessageBox(title, content, self.window())
        self.w.yesButton.setText(tr("ok", "OK"))
        self.w.cancelButton.setText(tr("cancel", "Cancel"))
        # 當對話方塊被接受 (使用者點擊 "OK") 時，關閉應用程式
        if self.w.exec():
            self.window().close()

    def _update_ui_texts(self):
        """更新此頁面內的 UI 文字，並建立主題的反向對應"""
        tr = self.translator.get

        self.titleLabel.setText(tr("settings", "Settings"))
        self.languageLabel.setText(tr("language", "Language"))
        self.themeLabel.setText(tr("theme", "Theme"))

        # --- 邏輯強化 ---
        self.themeComboBox.blockSignals(True)  # 更新UI時，暫時阻擋信號避免觸發 _on_theme_changed

        current_theme_setting = self.settings.get("theme", "System")
        self.themeComboBox.clear()

        # 建立翻譯後的字典，同時更新反向對應字典
        translated_map = {}
        for key in THEMES.keys():
            translated_text = tr(key.lower(), key)
            translated_map[key] = translated_text
            # 建立 "淺色": "Light" 這樣的反向對應
            self.reverse_theme_map[translated_text] = key

        self.themeComboBox.addItems(translated_map.values())

        # 根據設定檔中的原始鍵(如"System")，從翻譯後的地圖中找到對應的顯示文字(如"跟隨系統")
        current_display_text = translated_map.get(current_theme_setting, translated_map["System"])
        self.themeComboBox.setCurrentText(current_display_text)

        self.themeComboBox.blockSignals(False)  # 恢復信號
