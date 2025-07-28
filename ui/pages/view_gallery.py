# ui/pages/view_gallery.py
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel


class GalleryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GalleryView")

        self.layout = QVBoxLayout(self)
        self.label = QLabel("這裡是「圖片編輯列表」頁面")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.layout.addWidget(self.label)