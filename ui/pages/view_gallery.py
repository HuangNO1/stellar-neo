from PyQt6 import uic
from PyQt6.QtWidgets import QWidget


class GalleryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 載入 UI 檔案
        uic.loadUi("ui/components/gallery.ui", self)

        # 現在您可以使用 self.import_button, self.image_list 等來存取元件
        self.import_button.clicked.connect(self.on_import_images)

    def on_import_images(self):
        print("「批量導入圖片」按鈕被點擊了！")
        # 在這裡加入您選擇檔案的邏輯