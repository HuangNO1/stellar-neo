from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget, QListWidgetItem, QFileDialog
from qfluentwidgets import MessageBox

from core.asset_manager import AssetManager
from core.translator import Translator


class LogoView(QWidget):
    def __init__(self, asset_manager: AssetManager,translator: Translator, parent=None):
        super().__init__(parent)
        self.translator = translator
        uic.loadUi("ui/components/logo_manager.ui", self)

        self.asset_manager = asset_manager

        self.logo_list_widget.setIconSize(QSize(64, 64))

        self.upload_logo_button.clicked.connect(self.upload_logo)
        self.logo_list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)

        self.load_logos()

    def load_logos(self):
        self.logo_list_widget.clear()
        logos = self.asset_manager.get_logos()
        for logo_path in logos:
            item = QListWidgetItem(QIcon(logo_path), Path(logo_path).name)
            item.setData(Qt.ItemDataRole.UserRole, logo_path)
            self.logo_list_widget.addItem(item)

    def upload_logo(self):
        files, _ = QFileDialog.getOpenFileNames(self, "選擇 Logo 圖片", "", "圖片檔案 (*.png *.jpg *.jpeg *.svg)")
        if files:
            for file_path in files:
                success, _ = self.asset_manager.add_logo(file_path)
            self.load_logos()

    def on_item_double_clicked(self, item: QListWidgetItem):
        logo_path = item.data(Qt.ItemDataRole.UserRole)
        title = self.translator.get("delete_logo_title", "Confirm Deletion")
        content = self.translator.get("delete_logo_body", 'Are you sure you want to delete Logo "{name}"?').format(
            name=Path(logo_path).name)
        msg_box = MessageBox(title, content, self.window())

        if msg_box.exec():
            if self.asset_manager.delete_logo(logo_path):
                self.load_logos()
