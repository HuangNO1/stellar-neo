# ui/pages/view_gallery.py (功能完整版)
import os
from PyQt6 import uic
from PyQt6.QtCore import Qt, QSize, QRect, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt6.QtWidgets import QWidget, QFileDialog, QListWidgetItem
from qfluentwidgets import InfoBarPosition, InfoBar

# 修正 import，使用新的 exif_reader
from core.exif_reader import get_exif_data
from core.settings_manager import SettingsManager


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

        # --- 關鍵修正 ---
        # 1. 關閉 QLabel 的自動縮放，防止圖片被拉伸變形。
        self.image_preview_label.setScaledContents(False)
        # 2. 確保 .ui 檔案中的置中設定生效，讓手動縮放的圖片能居中顯示。
        self.image_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._connect_signals()
        self._load_settings()

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
            self.original_pixmap = QPixmap(path) # 移除用於測試的 "+ 111"

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
        修正版：以父層容器(middle_panel)為基準進行等比例縮放。
        這樣可以確保圖片在保持長寬比的前提下，最大化地顯示在可用區域中。
        """
        if not self.original_pixmap or self.original_pixmap.isNull():
            self.image_preview_label.clear()
            self.image_preview_label.setText("請選擇或拖入圖片")
            return

        # --- 關鍵修正：使用 middle_panel 的大小作為縮放目標 ---
        # 這能準確反映 QSplitter 分割後，中間佈局的實際可用大小 [cite: 2, 6]。
        container_size = self.middle_panel.size()

        # 避免在視窗尚未顯示時 (size為0) 進行無效計算
        if container_size.width() <= 1 or container_size.height() <= 1:
            return

        # 1. 根據容器大小，保持長寬比來縮放原始圖片
        scaled_pixmap = self.original_pixmap.scaled(
            container_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        settings = self._get_current_settings()
        frame_enabled = settings.get('frame_enabled', False)

        # 2. 根據縮放後的圖片大小，計算相框寬度
        # 相框寬度基於滑塊的值(1-100) [cite: 18] 和圖片的短邊計算，視覺效果更一致
        base_size = min(scaled_pixmap.width(), scaled_pixmap.height())
        # 將滑塊值 (e.g., 1-100) 轉換為一個合理的比例
        frame_ratio = settings.get('frame_width', 10) / 250.0
        frame_width = int(base_size * frame_ratio) if frame_enabled else 0

        # 3. 建立最終畫布，大小為 "縮放後的圖片" + "相框"
        canvas_size = scaled_pixmap.size() + QSize(frame_width * 2, frame_width * 2)
        final_pixmap = QPixmap(canvas_size)
        final_pixmap.fill(Qt.GlobalColor.transparent)

        # 4. 使用 QPainter 開始繪製
        painter = QPainter(final_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 5. 如果啟用相框，先繪製白色背景
        if frame_enabled and frame_width > 0:
            painter.setBrush(QColor("white"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(final_pixmap.rect())

        # 6. 將保持了正確比例的 scaled_pixmap 繪製到畫布中心
        image_rect = QRect(QPoint(frame_width, frame_width), scaled_pixmap.size())
        painter.drawPixmap(image_rect, scaled_pixmap)

        # 7. 如果啟用浮水印，在圖片上繪製文字
        if settings.get('watermark_enabled', False):
            text = settings.get('watermark_text', 'Sample Watermark')
            # 字體大小也基於縮放後的圖片尺寸，確保視覺上大小合適
            font_size = max(10, int(scaled_pixmap.height() / 30))
            font = QFont("Arial", font_size)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255, 128))

            padding = int(base_size * 0.02)
            watermark_rect = image_rect.adjusted(0, 0, -padding, -padding)
            painter.drawText(watermark_rect, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight, text)

        painter.end()

        # 8. 將最終繪製好的、尺寸正確的 Pixmap 設置給 QLabel
        # 因為 setScaledContents 已被設為 False，圖片將以原始尺寸居中顯示，不會再被拉伸
        self.image_preview_label.setPixmap(final_pixmap)

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

