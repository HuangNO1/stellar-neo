# view_font.py (重構後)

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QListWidgetItem, QFileDialog
from qfluentwidgets import MessageBox

from core.asset_manager import AssetManager
from core.translator import Translator
from ui.customs.font_item_widget import FontItemWidget


class FontView(QWidget):
    def __init__(self, asset_manager: AssetManager, translator: Translator, parent=None):
        super().__init__(parent)
        self.translator = translator
        self.tr = self.translator.get
        
        uic.loadUi("ui/components/font_manager.ui", self)

        self.asset_manager = asset_manager
        self._is_selecting_all = False

        self._translate_ui()
        self._connect_signals()
        self.load_fonts()

    def _translate_ui(self):
        self.title_label.setText(self.tr("font_management", "Font Management"))
        self.upload_font_button.setText(self.tr("upload_font_button", "Upload Font"))
        self.select_all_checkbox.setText(self.tr("gallery_select_all", "Select All"))
        self.clear_selected_button.setText(self.tr("gallery_clear_selected", "Clear Selected"))
        self.userFontTitle.setText(self.tr("user_uploaded_fonts", "User Uploaded Fonts"))
        self.systemFontTitle.setText(self.tr("system_builtin_fonts", "System-Builtin Fonts"))

    def _connect_signals(self):
        # 管理功能的信號只連接到使用者字體相關的操作
        
        self.upload_font_button.clicked.connect(self.upload_font)  # [cite: 2]
        self.select_all_checkbox.stateChanged.connect(self._on_select_all_changed)
        
        self.clear_selected_button.clicked.connect(self._on_clear_selected_clicked)  # [cite: 3]

    def load_fonts(self):
        """分類載入使用者字體和系統字體到不同的列表中"""
        # 清空列表
        self.user_font_list_widget.clear()
        self.system_font_list_widget.clear()

        # 1. 載入使用者上傳的字體
        user_fonts = self.asset_manager.get_user_fonts()  # 返回 {path: [families]}
        user_families_sorted = sorted(set(family for families in user_fonts.values() for family in families))

        for family in user_families_sorted:
            # 找到這個 family 對應的路徑
            path = next((p for p, fams in user_fonts.items() if family in fams), None)
            if not path: continue

            item_widget = FontItemWidget(family, path, self.translator, self)
            item_widget.selection_changed.connect(self._update_select_all_checkbox_state)

            list_item = QListWidgetItem(self.user_font_list_widget)
            list_item.setData(Qt.ItemDataRole.UserRole, path)  # 存儲字體檔案路徑用於刪除
            list_item.setSizeHint(item_widget.sizeHint())
            self.user_font_list_widget.addItem(list_item)
            self.user_font_list_widget.setItemWidget(list_item, item_widget)

        # 2. 載入系統字體
        system_fonts = self.asset_manager.get_system_fonts()
        for family in system_fonts:
            # 對於系統字體，路徑為 None，且 checkbox 將被禁用
            item_widget = FontItemWidget(family, None, self.translator, self)

            list_item = QListWidgetItem(self.system_font_list_widget)
            list_item.setData(Qt.ItemDataRole.UserRole, None)  # 沒有路徑
            list_item.setSizeHint(item_widget.sizeHint())
            self.system_font_list_widget.addItem(list_item)
            self.system_font_list_widget.setItemWidget(list_item, item_widget)

        # 更新 UI 狀態
        self._update_select_all_checkbox_state()

    def upload_font(self):
        """開啟對話框以上傳字體"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            self.tr("select_font_dialog", "Select Font(s)"),
            "",
            f"{self.tr("font_files", "Font Files")} (*.ttf *.otf *.woff *.woff2)")
        if files:
            for file_path in files:
                self.asset_manager.add_font(file_path)
            self.load_fonts()  # 完成後重新載入

    def _on_select_all_changed(self, state: Qt.CheckState):
        """【邏輯修正】處理'全選'核取方塊的狀態變化"""
        if self._is_selecting_all: return
        self._is_selecting_all = True

        # 核心邏輯修正
        total_deletable = self.user_font_list_widget.count()
        checked_count = sum(
            self.user_font_list_widget.itemWidget(self.user_font_list_widget.item(i)).is_checked()
            for i in range(total_deletable)
        )
        should_check = not (checked_count == total_deletable and total_deletable > 0)

        for i in range(self.user_font_list_widget.count()):
            widget = self.user_font_list_widget.itemWidget(self.user_font_list_widget.item(i))
            if widget:
                widget.set_checked(should_check)

        self._is_selecting_all = False
        self._update_select_all_checkbox_state()

    def _update_select_all_checkbox_state(self):
        """根據使用者字體列表的勾選情況，更新'全選'框的狀態"""
        if self._is_selecting_all: return

        total_deletable = self.user_font_list_widget.count()
        if total_deletable == 0:
            self.select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
            self.select_all_checkbox.setEnabled(False)
            return

        self.select_all_checkbox.setEnabled(True)
        checked_count = sum(
            self.user_font_list_widget.itemWidget(self.user_font_list_widget.item(i)).is_checked()
            for i in range(total_deletable)
        )

        self.select_all_checkbox.blockSignals(True)
        if checked_count == 0:
            self.select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
        elif checked_count == total_deletable:
            self.select_all_checkbox.setCheckState(Qt.CheckState.Checked)
        else:
            self.select_all_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
        self.select_all_checkbox.blockSignals(False)

    def _on_clear_selected_clicked(self):
        """刪除所有選中的使用者字體"""
        items_to_delete = []
        for i in range(self.user_font_list_widget.count()):
            list_item = self.user_font_list_widget.item(i)
            item_widget = self.user_font_list_widget.itemWidget(list_item)
            if item_widget and item_widget.is_checked():
                items_to_delete.append(list_item)

        if not items_to_delete:
            return

        title = self.tr("confirm_delete_title", "Confirm Deletion")
        body = self.tr("confirm_clear_selected_body_font",
                       "Delete {count} selected font(s)?\n(May require app restart to take full effect)").format(
            count=len(items_to_delete))
        self.msg_box = MessageBox(title, body, self.window())
        self.msg_box.yesButton.setText(self.tr("ok", "OK"))
        self.msg_box.cancelButton.setText(self.tr("cancel", "Cancel"))

        if self.msg_box.exec():
            for list_item in items_to_delete:
                font_path = list_item.data(Qt.ItemDataRole.UserRole)
                if font_path:  # 再次確認是使用者字體
                    self.asset_manager.delete_font(font_path)
            self.load_fonts()