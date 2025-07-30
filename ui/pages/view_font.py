from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QWidget, QListWidgetItem, QFileDialog
from qfluentwidgets import MessageBox

from core.asset_manager import AssetManager
from core.translator import Translator


class FontView(QWidget):
    def __init__(self, asset_manager: AssetManager, translator: Translator, parent=None):
        super().__init__(parent)
        self.translator = translator
        uic.loadUi("ui/components/font_manager.ui", self)

        self.asset_manager = asset_manager

        self.upload_font_button.clicked.connect(self.upload_font)
        self.font_list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)

        self.load_fonts()

    def load_fonts(self):
        self.font_list_widget.clear()
        font_families = self.asset_manager.get_fonts()
        for family in font_families:
            item = QListWidgetItem(family)
            item.setFont(QFont(family, 14))
            # 這裡可以存儲字體家族名或檔案路徑，取決於刪除邏輯
            # item.setData(Qt.ItemDataRole.UserRole, family)
            self.font_list_widget.addItem(item)

    def upload_font(self):
        files, _ = QFileDialog.getOpenFileNames(self, "選擇字體檔案", "", "字體檔案 (*.ttf *.otf)")
        if files:
            for file_path in files:
                self.asset_manager.add_font(file_path)
            self.load_fonts()

    def on_item_double_clicked(self, item: QListWidgetItem):
        font_family = item.text()
        logo_path = item.data(Qt.ItemDataRole.UserRole)
        # 刪除字體的邏輯比較複雜，這裡先做一個提示
        title = self.translator.get("delete_logo_title", "Confirm Deletion")
        content = self.translator.get("delete_logo_body", 'Are you sure you want to delete Logo "{name}"?').format(
            name=Path(logo_path).name)
        msg_box = MessageBox(title, content, self.window())
        msg_box.exec()
