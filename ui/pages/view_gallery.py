# ui/pages/view_gallery.py (功能完整版)
import os
from PyQt6 import uic
from PyQt6.QtCore import Qt, QSize, QRect, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt6.QtWidgets import QWidget, QFileDialog, QListWidgetItem, QVBoxLayout
from qfluentwidgets import InfoBarPosition, InfoBar

# 修正 import，使用新的 exif_reader
from core.exif_reader import get_exif_data
from core.settings_manager import SettingsManager
from ui.customs.gallery_tabs import GalleryTabs


class GalleryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 修正 uic 載入路徑
        uic.loadUi("ui/components/gallery.ui", self)

        self.settings_manager = SettingsManager()
        self.image_items = {}
        self.current_image_path = None
        self.original_pixmap = None

        self.image_preview_label.setAcceptDrops(True)
        self.image_preview_label.dragEnterEvent = self.dragEnterEvent
        self.image_preview_label.dropEvent = self.dropEvent

        # 加入 tabs
        self.tabs = GalleryTabs(self)
        self.right_layout.addWidget(self.tabs)

        # --- 關鍵修正 ---
        # 1. 關閉 QLabel 的自動縮放，防止圖片被拉伸變形。
        self.image_preview_label.setScaledContents(False)
        # 2. 確保 .ui 檔案中的置中設定生效，讓手動縮放的圖片能居中顯示。
        self.image_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # self.init_Text()
        self._connect_signals()

    def init_Text(self):
        """
        初始化一些控鍵的國際化文字
        :return:
        """
        self.frame_enabled_checkbox.setOffText("关闭")
        self.frame_enabled_checkbox.setOnText("开启")

        items = ['shoko', '西宫硝子', '宝多六花', '小鸟游六花']
        self.frame_style_comboBox.addItems(items)

    def resizeEvent(self, event):
        """
        關鍵修復：重寫 resizeEvent。
        每當視窗或 splitter 大小改變時，此函數會被呼叫。
        """
        super().resizeEvent(event)
        # 重新計算並更新預覽圖，以適應新的標籤大小
        self._update_preview()

    def _connect_signals(self):
        self.import_button.clicked.connect(self._open_image_dialog)
        self.image_list.currentItemChanged.connect(self._on_list_item_selected)

        # --- 關鍵修正：連接 QSplitter 的移動信號 ---
        # 當使用者拖動分隔條時，觸發 _update_preview 重新繪製圖片
        self.main_splitter.splitterMoved.connect(self._update_preview)

        # 連接右側控制項
        self.tabs.settingsChanged.connect(self._update_preview)

    # --- 事件處理 ---

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and all(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        self._add_images(paths)
        event.acceptProposedAction()

    # --- 槽函數 (Slots) ---

    def _open_image_dialog(self):
        image_files, _ = QFileDialog.getOpenFileNames(self, "選擇圖片", "",
                                                      "圖片檔案 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)")
        if image_files:
            self._add_images(image_files)

    def _on_list_item_selected(self, current_item: QListWidgetItem, previous_item: QListWidgetItem):
        if not current_item:
            # 如果沒有選中項 (例如列表被清空)，則清除預覽
            self.current_image_path = None
            self.original_pixmap = None
            self.image_preview_label.clear()
            self.image_preview_label.setText("請選擇或拖入圖片")
            return

        path = current_item.data(Qt.ItemDataRole.UserRole)
        if path != self.current_image_path:
            self.current_image_path = path
            self.original_pixmap = QPixmap(path)

            if self.original_pixmap.isNull():
                print(f"無法載入圖片: {path}")

                # 暫時阻斷信號，防止移除 item 時觸發不必要的重繪
                self.image_list.currentItemChanged.disconnect(self._on_list_item_selected)

                # 從 UI 列表和內部資料結構中移除
                row = self.image_list.row(current_item)
                self.image_list.takeItem(row)
                if path in self.image_items:
                    del self.image_items[path]

                # 重新連接信號
                self.image_list.currentItemChanged.connect(self._on_list_item_selected)

                # 顯示錯誤訊息
                InfoBar.error(
                    title='載入錯誤',
                    content=f"無法載入圖片: {os.path.basename(path)}",
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self.window()
                )

                # 如果列表為空，則重設狀態
                if self.image_list.count() == 0:
                    self.current_image_path = None
                    self.original_pixmap = None
                    self.image_preview_label.clear()
                    self.image_preview_label.setText("請選擇或拖入圖片")
                # 否則，可以選擇選中下一個項目
                elif row < self.image_list.count():
                    self.image_list.setCurrentRow(row)
                else:
                    self.image_list.setCurrentRow(self.image_list.count() - 1)
                return

            self._update_preview()

    # --- 輔助方法 ---

    def _add_images(self, paths: list):
        new_images_added = False
        for path in paths:
            if path not in self.image_items and os.path.exists(path):
                # 使用新的基於 PyQt6 的 EXIF 讀取器
                exif = get_exif_data(path)
                print(f"導入圖片: {os.path.basename(path)}, EXIF: {exif}")

                self.image_items[path] = {'exif': exif}

                item = QListWidgetItem(os.path.basename(path))
                item.setData(Qt.ItemDataRole.UserRole, path)
                self.image_list.addItem(item)
                new_images_added = True

        if new_images_added and self.image_list.count() > 0 and not self.current_image_path:
            self.image_list.setCurrentRow(0)


    def _update_preview(self):
        """
        在縮放前預先計算相框空間，確保相框和圖片都能完整顯示。
        """
        if not self.original_pixmap or self.original_pixmap.isNull():
            self.image_preview_label.clear()
            self.image_preview_label.setText("請選擇或拖入圖片")
            return

        # 1. 獲取佈局的總可用空間
        container_size = self.middle_panel.size()
        if container_size.width() <= 1 or container_size.height() <= 1:
            return

        settings = self.tabs._get_current_settings()
        # print("新的settings: ", settings)
        frame_enabled = settings.get('frame_enabled', False)

        # 2. **核心修正：先計算相框的像素寬度**
        frame_width = 0
        if frame_enabled:
            # 將滑塊的值(1-100)映射為一個基於容器短邊的比例，讓邊框視覺上更穩定
            base_size = min(container_size.width(), container_size.height())
            frame_ratio = settings.get('frame_width', 10) / 250.0  # e.g., max 4% of short side
            frame_width = int(base_size * frame_ratio)

        # 3. **計算真正留給圖片的空間**
        # 從總可用空間中，減去上下左右的相框寬度
        image_area_width = container_size.width() - (frame_width * 2)
        image_area_height = container_size.height() - (frame_width * 2)

        # 如果相框設定過大，可能導致計算出的圖片空間為負，需保護
        if image_area_width <= 0 or image_area_height <= 0:
            # 這種情況下，不顯示圖片，或者可以選擇只顯示圖片而不顯示相框
            self.image_preview_label.clear()
            return

        image_area_size = QSize(image_area_width, image_area_height)

        # 4. **將原始圖片，等比例縮放到這個預留好的小空間內**
        scaled_pixmap = self.original_pixmap.scaled(
            image_area_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # 5. 建立最終畫布，其大小剛好等於 "縮放後的圖片 + 相框"
        # 因為 scaled_pixmap 是在預留空間裡縮放的，所以這個總大小不會超過 container_size
        final_canvas_size = scaled_pixmap.size() + QSize(frame_width * 2, frame_width * 2)
        final_pixmap = QPixmap(final_canvas_size)
        final_pixmap.fill(Qt.GlobalColor.transparent)

        # 6. 開始繪製
        painter = QPainter(final_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 繪製相框背景
        if frame_enabled and frame_width > 0:
            painter.setBrush(QColor("white"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(final_pixmap.rect())

        # 將縮放好的圖片繪製到相框中間
        image_rect = QRect(QPoint(frame_width, frame_width), scaled_pixmap.size())
        painter.drawPixmap(image_rect, scaled_pixmap)

        # 繪製浮水印 (邏輯不變)
        if settings.get('watermark_enabled', False):
            text = settings.get('watermark_text', 'Sample Watermark')
            font_size = max(10, int(scaled_pixmap.height() / 30))
            font = QFont("Arial", font_size)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255, 128))
            padding = int(min(scaled_pixmap.width(), scaled_pixmap.height()) * 0.02)
            watermark_rect = image_rect.adjusted(0, 0, -padding, -padding)
            painter.drawText(watermark_rect, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight, text)

        painter.end()

        # 7. 顯示最終成品
        self.image_preview_label.setPixmap(final_pixmap)
