import os
from PyQt6 import uic
from PyQt6.QtCore import Qt, QSize, QRect, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt6.QtWidgets import QWidget, QFileDialog, QListWidgetItem
from qfluentwidgets import InfoBarPosition, InfoBar, MessageBox

# 修正 import，使用新的 exif_reader 和自訂元件
from core.exif_reader import get_exif_data
from core.settings_manager import SettingsManager
from core.translator import Translator
from ui.customs.gallery_tabs import GalleryTabs
from ui.customs.gallery_item_widget import GalleryItemWidget


class GalleryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 修正 uic 載入路徑
        uic.loadUi("ui/components/gallery.ui", self)

        self.settings_manager = SettingsManager()
        # --- 國際化核心 ---
        self.translator = Translator()
        # 假設您的語言檔都放在 i18n/ 資料夾下
        # 且 settings.json 中的 "language" 鍵為 "en", "zh_TW" 等
        language = self.settings_manager.get("language", "en")
        self.translator.load(language, "./i18n")



        self.image_items = {}  # 用於存儲圖片路徑和對應的 list_item
        self.current_image_path = None
        self.original_pixmap = None
        self._is_selecting_all = False  # 用於防止 '全選' 時信號循環觸發的標誌

        # 設定拖拽事件
        self.image_preview_label.setAcceptDrops(True)
        self.image_preview_label.dragEnterEvent = self.dragEnterEvent
        self.image_preview_label.dropEvent = self.dropEvent

        # 加入右側的設定 Tabs
        # 將 translator 傳遞給子元件
        self.tabs = GalleryTabs(self.translator, self)
        self.right_layout.addWidget(self.tabs)

        # --- 關鍵修正 ---
        # 1. 關閉 QLabel 的自動縮放，防止圖片被拉伸變形。由我們手動控制縮放。
        self.image_preview_label.setScaledContents(False)
        # 2. 確保 .ui 檔案中的置中設定生效，讓手動縮放的圖片能居中顯示。
        self.image_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._translate_ui()  # 翻譯此視圖的 UI
        self._connect_signals()

    def _translate_ui(self):
        """ 翻譯 gallery.ui 中的靜態文字 """
        self.import_button.setText(self.translator.get("gallery_import_button", "Import"))
        self.select_all_checkbox.setText(self.translator.get("gallery_select_all", "Select All"))
        self.clear_selected_button.setText(self.translator.get("gallery_clear_selected", "Clear Selected"))
        self._clear_preview()  # 清除時會設定預設文字

    def resizeEvent(self, event):
        """
        重寫 resizeEvent。
        每當視窗或 splitter 大小改變時，此函數會被呼叫。
        """
        super().resizeEvent(event)
        # 重新計算並更新預覽圖，以適應新的標籤大小
        self._update_preview()

    def _connect_signals(self):
        """連接所有元件的信號與槽函數。"""
        self.import_button.clicked.connect(self._open_image_dialog)
        self.image_list.currentItemChanged.connect(self._on_list_item_selected)
        self.main_splitter.splitterMoved.connect(self._update_preview)
        self.tabs.settingsChanged.connect(self._update_preview)

        # 連接新的控制按鈕信號
        self.select_all_checkbox.stateChanged.connect(self._on_select_all_changed)
        # self.clear_all_button.clicked.connect(self._on_clear_all_clicked)
        self.clear_selected_button.clicked.connect(self._on_clear_selected_clicked)

    # --- 核心功能方法 ---

    def _add_images(self, paths: list):
        """
        將圖片路徑列表添加到 UI 列表和內部資料結構中。
        對於每個圖片，都會創建一個自訂的 GalleryItemWidget。
        """
        new_images_added = False
        for path in paths:
            # 避免重複添加
            if path not in self.image_items and os.path.exists(path):
                exif = get_exif_data(path)
                # 簡單判斷是否有關鍵的 EXIF 資訊，例如相機型號
                has_exif = bool(exif.get('Model'))
                # 創建自訂元件實例
                # 創建自訂元件實例時傳入 translator
                item_widget = GalleryItemWidget(path, has_exif, self.translator, self)
                # 連接自訂元件發出的信號
                item_widget.selection_changed.connect(self._update_select_all_checkbox_state)
                item_widget.delete_requested.connect(self._on_delete_item_requested)

                # 創建 QListWidgetItem 並將自訂元件放入其中
                list_item = QListWidgetItem(self.image_list)
                list_item.setData(Qt.ItemDataRole.UserRole, path)  # 將圖片路徑存儲在 item 中
                list_item.setSizeHint(item_widget.sizeHint())  # 關鍵：設定 item 的建議大小
                self.image_list.addItem(list_item)
                self.image_list.setItemWidget(list_item, item_widget)  # 將 widget 設置為 item 的內容

                # 將圖片資訊和對應的 list_item 存儲起來，方便後續操作
                self.image_items[path] = {'exif': exif, 'list_item': list_item}
                new_images_added = True

        if new_images_added:
            self._update_select_all_checkbox_state()
            # 如果是首次添加，預設選中第一張圖片
            if self.image_list.count() > 0 and not self.current_image_path:
                self.image_list.setCurrentRow(0)

    def _on_delete_item_requested(self, path: str):
        """響應從 GalleryItemWidget 發出的刪除請求。"""
        if path not in self.image_items:
            return

        # 彈出確認對話框，增加用戶體驗
        title = self.translator.get("confirm_delete_title", "Confirm Deletion")
        body = self.translator.get("confirm_delete_item_body", "Delete {filename}?").format(
            filename=os.path.basename(path))
        msg_box = MessageBox(title, body, self.window())

        if msg_box.exec():
            list_item = self.image_items[path]['list_item']
            row = self.image_list.row(list_item)

            # 從 QListWidget 中安全移除
            self.image_list.takeItem(row)
            # 從內部資料結構中移除
            del self.image_items[path]

            # 如果被刪除的是當前正在預覽的圖片，需要更新預覽
            if path == self.current_image_path:
                if self.image_list.count() > 0:
                    # 選中下一個項目或最後一個項目
                    new_row = min(row, self.image_list.count() - 1)
                    self.image_list.setCurrentRow(new_row)
                else:
                    # 列表已空，清空預覽
                    self._clear_preview()

            self._update_select_all_checkbox_state()

    def _on_select_all_changed(self, state):
        """處理'全選'勾選框的狀態改變事件。"""
        # 使用標誌位防止在遍歷設置時，子項的信號反過來觸發此函數，造成無限循環
        if self._is_selecting_all:
            return

        self._is_selecting_all = True

        # 關鍵邏輯修正：
        # 只要點擊後不是「未選中」狀態，就一律視為「全選」操作。
        is_checked = (state != Qt.CheckState.Unchecked.value)

        for i in range(self.image_list.count()):
            list_item = self.image_list.item(i)
            item_widget = self.image_list.itemWidget(list_item)
            if item_widget:
                # 呼叫自訂元件的方法來設定勾選狀態
                item_widget.set_checked(is_checked)

        self._is_selecting_all = False

        # 關鍵補充：
        # 在操作完所有子項後，手動呼叫一次狀態更新函數。
        # 這能確保主勾選框的狀態被正確地更新為 Checked 或 Unchecked，
        # 而不是停留在 PartiallyChecked。
        self._update_select_all_checkbox_state()

        self._is_selecting_all = True
        is_checked = (state == Qt.CheckState.Checked.value)
        for i in range(self.image_list.count()):
            list_item = self.image_list.item(i)
            item_widget = self.image_list.itemWidget(list_item)
            if item_widget:
                # 呼叫自訂元件的方法來設定勾選狀態
                item_widget.set_checked(is_checked)
        self._is_selecting_all = False

    def _update_select_all_checkbox_state(self):
        """根據所有子項的勾選狀態，更新'全選'勾選框的狀態（未選/全選/部分選中）。"""
        if self._is_selecting_all or self.image_list.count() == 0:
            # 如果列表為空，確保勾選框是未選中狀態
            if self.image_list.count() == 0:
                self.select_all_checkbox.blockSignals(True)
                self.select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
                self.select_all_checkbox.blockSignals(False)
            return

        checked_count = 0
        for i in range(self.image_list.count()):
            list_item = self.image_list.item(i)
            item_widget = self.image_list.itemWidget(list_item)
            if item_widget and item_widget.is_checked():
                checked_count += 1

        # 暫時阻斷信號，防止設定狀態時再次觸發 _on_select_all_changed
        self.select_all_checkbox.blockSignals(True)
        if checked_count == 0:
            self.select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
        elif checked_count == self.image_list.count():
            self.select_all_checkbox.setCheckState(Qt.CheckState.Checked)
        else:
            # 部分選中狀態
            self.select_all_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
        self.select_all_checkbox.blockSignals(False)  # 恢復信號

    def _on_clear_selected_clicked(self):
        """處理'清除選取'按鈕的點擊事件。"""
        # 1. 找出所有被選中的項目
        items_to_delete = []
        for i in range(self.image_list.count()):
            list_item = self.image_list.item(i)
            item_widget = self.image_list.itemWidget(list_item)
            if item_widget and item_widget.is_checked():
                items_to_delete.append(list_item)

        # 2. 如果沒有選中的項目，直接返回
        if not items_to_delete:
            return

        # 3. 彈出確認對話框
        title = self.translator.get("confirm_delete_title", "Confirm Deletion")
        body = self.translator.get("confirm_clear_selected_body", "Clear {count} items?").format(
            count=len(items_to_delete))
        msg_box = MessageBox(title, body, self.window())

        if msg_box.exec():
            # 標記當前預覽是否需要更新
            preview_needs_update = False

            # 4. 遍歷並刪除所有選中的項目
            for list_item in items_to_delete:
                row = self.image_list.row(list_item)
                path = list_item.data(Qt.ItemDataRole.UserRole)

                # 如果被刪除的是當前預覽的圖片，做個標記
                if path == self.current_image_path:
                    preview_needs_update = True

                # 從 QListWidget 中移除
                self.image_list.takeItem(row)
                # 從內部資料結構中移除
                if path in self.image_items:
                    del self.image_items[path]

            # 5. 統一更新預覽和UI狀態
            if preview_needs_update:
                # 如果列表已空，清空預覽，否則選中第一項
                if self.image_list.count() > 0:
                    self.image_list.setCurrentRow(0)
                else:
                    self._clear_preview()

            self._update_select_all_checkbox_state()

    def _clear_preview(self):
        """清空預覽區域並重設相關狀態變數。"""
        self.current_image_path = None
        self.original_pixmap = None
        self.image_preview_label.clear()
        # 使用 translator 設定提示文字
        prompt = self.translator.get("gallery_drop_prompt", "Drop image here")
        self.image_preview_label.setText(prompt)

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
        """當列表中的選中項改變時，更新圖片預覽。"""
        if not current_item:
            # 如果沒有選中項 (例如列表被清空)，則清除預覽
            self._clear_preview()
            return

        path = current_item.data(Qt.ItemDataRole.UserRole)
        if path != self.current_image_path:
            self.current_image_path = path
            self.original_pixmap = QPixmap(path)

            # 處理圖片載入失敗的情況
            if self.original_pixmap.isNull():
                print(f"無法載入圖片: {path}")
                # 直接調用刪除邏輯來處理損壞或不存在的圖片
                self._on_delete_item_requested(path)
                return

            self._update_preview()

    # --- 繪圖與更新 ---

    def _update_preview(self):
        """
        核心繪圖函數。
        根據當前圖片、相框和浮水印設定，重新計算並繪製預覽圖。
        """
        if not self.original_pixmap or self.original_pixmap.isNull():
            self._clear_preview()
            return

        # 1. 獲取佈局的總可用空間
        container_size = self.middle_panel.size()
        if container_size.width() <= 1 or container_size.height() <= 1:
            return

        settings = self.tabs._get_current_settings()
        frame_enabled = settings.get('frame_enabled', False)

        # 2. 計算相框的像素寬度
        frame_width = 0
        if frame_enabled:
            # 將滑塊的值(1-100)映射為一個基於容器短邊的比例，讓邊框視覺上更穩定
            base_size = min(container_size.width(), container_size.height())
            frame_ratio = settings.get('frame_width', 10) / 250.0
            frame_width = int(base_size * frame_ratio)

        # 3. 計算真正留給圖片的空間
        image_area_width = container_size.width() - (frame_width * 2)
        image_area_height = container_size.height() - (frame_width * 2)

        if image_area_width <= 0 or image_area_height <= 0:
            self.image_preview_label.clear()
            return

        # 4. 將原始圖片，等比例縮放到這個預留好的小空間內
        image_area_size = QSize(image_area_width, image_area_height)
        scaled_pixmap = self.original_pixmap.scaled(
            image_area_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # 5. 建立最終畫布，其大小剛好等於 "縮放後的圖片 + 相框"
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
