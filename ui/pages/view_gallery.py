# ui/pages/view_gallery.py (純 PyQt6 版本)
import os
from PyQt6 import uic
from PyQt6.QtCore import Qt, QSize, QRect, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt6.QtWidgets import QWidget, QFileDialog, QListWidgetItem

# 匯入我們新建立的、純 PyQt6 的 EXIF 讀取器
from core.exif_reader import get_exif_data
from core.settings_manager import SettingsManager


class GalleryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        uic.loadUi("ui/components/gallery.ui", self)

        self.settings_manager = SettingsManager()
        self.image_items = {}
        self.current_image_path = None
        self.original_pixmap = None  # 儲存未經處理的原始 QPixmap

        # 啟用拖拽功能
        self.image_preview_label.setAcceptDrops(True)
        self.image_preview_label.dragEnterEvent = self.dragEnterEvent
        self.image_preview_label.dropEvent = self.dropEvent

        self._connect_signals()
        self._load_settings()

    def _connect_signals(self):
        self.import_button.clicked.connect(self._open_image_dialog)
        self.image_list.currentItemChanged.connect(self._on_list_item_selected)

        # 連接右側控制項
        self.watermark_enabled_checkbox.stateChanged.connect(self._on_settings_changed)
        self.watermark_text_input.textChanged.connect(self._on_settings_changed)
        self.frame_enabled_checkbox.stateChanged.connect(self._on_settings_changed)
        self.frame_width_slider.valueChanged.connect(self._on_settings_changed)

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
        if current_item:
            path = current_item.data(Qt.ItemDataRole.UserRole)
            if path != self.current_image_path:
                self.current_image_path = path
                # 直接使用 QPixmap 載入圖片
                self.original_pixmap = QPixmap(path)
                if self.original_pixmap.isNull():
                    print(f"無法載入圖片: {path}")
                    self.current_image_path = None
                    self.original_pixmap = None
                    self.image_preview_label.setText(f"無法載入:\n{os.path.basename(path)}")
                    return
                self._update_preview()

    def _on_settings_changed(self):
        settings = self._get_current_settings()
        self.settings_manager.set("gallery_settings", settings)
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
        使用 QPainter 即時繪製預覽圖，完全取代 Pillow 和 image_processor。
        """
        if not self.original_pixmap:
            self.image_preview_label.setText("請選擇或拖入圖片")
            return

        settings = self._get_current_settings()
        frame_enabled = settings.get('frame_enabled', False)
        frame_width = settings.get('frame_width', 10) if frame_enabled else 0

        # 1. 計算畫布大小（圖片 + 邊框）
        canvas_size = self.original_pixmap.size() + QSize(frame_width * 2, frame_width * 2)

        # 2. 建立一個新的 QPixmap 作為畫布
        final_pixmap = QPixmap(canvas_size)
        final_pixmap.fill(Qt.GlobalColor.transparent)  # 設定透明背景

        # 3. 建立 QPainter 在畫布上繪圖
        painter = QPainter(final_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 4. 繪製相框背景 (如果啟用)
        if frame_enabled:
            painter.setBrush(QColor("white"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(final_pixmap.rect())

        # 5. 將原始圖片繪製到相框中間
        image_rect = QRect(QPoint(frame_width, frame_width), self.original_pixmap.size())
        painter.drawPixmap(image_rect, self.original_pixmap)

        # 6. 繪製浮水印 (如果啟用)
        if settings.get('watermark_enabled', False):
            text = settings.get('watermark_text', 'Sample Watermark')
            # 根據圖片大小動態設定字體大小
            font_size = max(12, int(self.original_pixmap.height() / 40))
            font = QFont("Arial", font_size)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255, 128))  # 半透明白色

            # 將浮水印繪製在圖片右下角
            watermark_rect = QRect(image_rect)
            watermark_rect.adjust(0, 0, -10, -10)  # 增加一些邊距
            painter.drawText(watermark_rect, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight, text)

        # 7. 結束繪圖
        painter.end()

        # 8. 將最終繪製好的 Pixmap 縮放並顯示在 QLabel 中
        self.image_preview_label.setPixmap(final_pixmap.scaled(
            self.image_preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))

    def _get_current_settings(self) -> dict:
        return {
            'watermark_enabled': self.watermark_enabled_checkbox.isChecked(),
            'watermark_text': self.watermark_text_input.text(),
            'frame_enabled': self.frame_enabled_checkbox.isChecked(),
            'frame_width': self.frame_width_slider.value(),
        }

    def _load_settings(self):
        settings = self.settings_manager.get("gallery_settings", {})
        self.watermark_enabled_checkbox.setChecked(settings.get('watermark_enabled', False))
        self.watermark_text_input.setText(settings.get('watermark_text', ''))
        self.frame_enabled_checkbox.setChecked(settings.get('frame_enabled', False))
        self.frame_width_slider.setValue(settings.get('frame_width', 10))

