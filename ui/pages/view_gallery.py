import os
from pathlib import Path

from PIL.ImageQt import ImageQt
from PIL import Image, ImageFilter
from PyQt6 import uic
from PyQt6.QtCore import Qt, QSize, QRect, QPoint, QRectF
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QPainterPath, QBrush
from PyQt6.QtWidgets import QWidget, QFileDialog, QListWidgetItem, QGraphicsDropShadowEffect
from qfluentwidgets import MessageBox

from core.asset_manager import AssetManager
from core.exif_reader import get_exif_data
from core.logo_mapping import get_logo_path
from core.settings_manager import SettingsManager
from core.translator import Translator
from ui.customs.gallery_item_widget import GalleryItemWidget
from ui.customs.gallery_tabs import GalleryTabs


class GalleryView(QWidget):
    # TODO 如果文件名過長 需要考慮c
    def __init__(self, asset_manager: AssetManager, translator: Translator, parent=None):
        super().__init__(parent)
        # 修正 uic 載入路徑
        uic.loadUi("ui/components/gallery.ui", self)

        self.settings_manager = SettingsManager()
        self.asset_manager = asset_manager
        # --- 國際化核心 ---
        self.translator = translator
        self.tr = self.translator.get

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
        self.tabs = GalleryTabs(self.asset_manager, self.translator, self)
        self.right_layout.addWidget(self.tabs)

        # --- 關鍵修正 ---
        # 1. 關閉 QLabel 的自動縮放，防止圖片被拉伸變形。由我們手動控制縮放。
        self.image_preview_label.setScaledContents(False)
        # 2. 確保 .ui 檔案中的置中設定生效，讓手動縮放的圖片能居中顯示。
        self.image_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # --- 新增：為圖片標籤建立一個陰影效果物件 ---
        # 我們將根據設定來啟用或禁用它
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(30)
        self.shadow.setColor(QColor(0, 0, 0, 80))
        self.shadow.setOffset(0, 0)
        self.image_preview_label.setGraphicsEffect(self.shadow)
        self.shadow.setEnabled(False)  # 預設關閉

        self._translate_ui()  # 翻譯此視圖的 UI
        self._connect_signals()
        self._clear_preview()

    def _translate_ui(self):
        self.import_button.setText(self.tr("gallery_import_button", "Import"))
        self.select_all_checkbox.setText(self.tr("gallery_select_all", "Select All"))
        self.clear_selected_button.setText(self.tr("gallery_clear_selected", "Clear Selected"))
        self._clear_preview()  # 清除時會設定預設文字
        self._update_select_all_checkbox_state()  # 更新 UI 狀態

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
        title = self.tr("confirm_delete_title", "Confirm Deletion")
        body = self.tr("confirm_delete_item_body", "Delete {filename}?").format(
            filename=os.path.basename(path))
        self.msg_box_item = MessageBox(title, body, self.window())
        self.msg_box_item.yesButton.setText(self.tr("ok", "OK"))
        self.msg_box_item.cancelButton.setText(self.tr("cancel", "Cancel"))

        if self.msg_box_item.exec():
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

    def _on_select_all_changed(self, state: Qt.CheckState):
        """處理'全選'核取方塊的狀態變化"""
        if self._is_selecting_all:
            return

        total_count = self.image_list.count()

        self._is_selecting_all = True

        checked_count = sum(
            self.image_list.itemWidget(self.image_list.item(i)).is_checked()
            for i in range(total_count)
        )
        # 核心邏輯：如果不是全選狀態（包括部分選中或未選中），則變為全選；否則全不選。
        should_check = not (checked_count == total_count and total_count > 0)

        for i in range(total_count):
            item_widget = self.image_list.itemWidget(self.image_list.item(i))
            if item_widget:
                # set_checked 會觸發 item_widget.selection_changed 信號
                item_widget.set_checked(should_check)

        self._is_selecting_all = False
        # 操作完成後，呼叫狀態更新函式來同步核取方塊的最終狀態
        self._update_select_all_checkbox_state()

    def _update_select_all_checkbox_state(self):
        """
        根據圖片列表的勾選情況，更新'全選'框的狀態
        """
        if self._is_selecting_all:
            return

        total_count = self.image_list.count()
        # 如果列表為空，禁用並取消勾選核取方塊，然後返回。
        if total_count == 0:
            self.select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
            self.select_all_checkbox.setEnabled(False)
            return

        # 如果列表不為空，確保核取方塊是啟用的
        self.select_all_checkbox.setEnabled(True)

        checked_count = sum(
            self.image_list.itemWidget(self.image_list.item(i)).is_checked()
            for i in range(total_count)
        )

        # 暫時阻斷信號，防止在程式碼中設定狀態時再次觸發 _on_select_all_changed
        self.select_all_checkbox.blockSignals(True)

        if checked_count == 0:
            self.select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
        elif checked_count == total_count:
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
        title = self.tr("confirm_delete_title", "Confirm Deletion")
        body = self.tr("confirm_clear_selected_body", "Clear {count} items?").format(
            count=len(items_to_delete))
        self.msg_box_all = MessageBox(title, body, self.window())
        self.msg_box_all.yesButton.setText(self.tr("ok", "OK"))
        self.msg_box_all.cancelButton.setText(self.tr("cancel", "Cancel"))

        if self.msg_box_all.exec():
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
        prompt = self.tr("gallery_drop_prompt", "Drop image here")
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
        window_title = self.tr("gallery_open_image_dialog")
        file_types = self.tr("gallery_import_image_dialog_file_type", "Image Files")
        image_files, _ = QFileDialog.getOpenFileNames(self, window_title, "",
                                                      f"{file_types} (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)")
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

    # --- 核心繪圖與更新 ---
    # vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
    # --- 以下是完全重寫的 _update_preview 方法和其輔助函式 ---
    # vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def _update_preview(self):
        """
        核心繪圖函數。
        根據當前圖片、相框和浮水印設定，重新計算並繪製預覽圖。
        """
        if not self.current_image_path or not self.original_pixmap or self.original_pixmap.isNull():
            self._clear_preview()
            return

        # 0. 獲取所有設定和當前圖片的 EXIF 資料
        all_settings = self.tabs._get_current_settings()
        f_settings = all_settings.get('frame', {})
        w_settings = all_settings.get('watermark', {})
        exif_data = self.image_items.get(self.current_image_path, {}).get('exif', {})

        # 1. 獲取容器大小
        container_size = self.middle_panel.size()
        if container_size.width() <= 20 or container_size.height() <= 20:
            return

        # 2. 根據設定計算相框邊距 (padding)
        # 將滑塊的百分比值轉換為實際像素
        base_padding = min(container_size.width(), container_size.height()) * 0.15
        padding_top = int(base_padding * f_settings.get('padding_top', 10) / 100)
        padding_sides = int(base_padding * f_settings.get('padding_sides', 10) / 100)
        padding_bottom = int(base_padding * f_settings.get('padding_bottom', 10) / 100)

        # 如果不啟用相框，則所有邊距為零
        if not f_settings.get('enabled', True):
            padding_top = padding_sides = padding_bottom = 0

        # 3. 計算圖片可用的繪製區域
        image_area_w = container_size.width() - (padding_sides * 2)
        image_area_h = container_size.height() - padding_top - padding_bottom
        if image_area_w <= 0 or image_area_h <= 0:
            self.image_preview_label.clear()
            return

        # 4. 等比例縮放原始圖片以適應可用區域
        scaled_photo = self.original_pixmap.scaled(
            QSize(int(image_area_w), int(image_area_h)),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # 5. 計算最終畫布大小（縮放後的圖片 + 邊距）
        final_canvas_w = scaled_photo.width() + padding_sides * 2
        final_canvas_h = scaled_photo.height() + padding_top + padding_bottom
        final_pixmap = QPixmap(QSize(final_canvas_w, final_canvas_h))
        final_pixmap.fill(Qt.GlobalColor.transparent)  # 使用透明背景

        # 6. 開始繪製
        painter = QPainter(final_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 定義相框和相片的矩形區域
        frame_rect = final_pixmap.rect()
        photo_rect = QRect(
            padding_sides,
            padding_top,
            scaled_photo.width(),
            scaled_photo.height()
        )

        # 7. (相框功能) 繪製相框背景
        if f_settings.get('enabled', True):
            self._draw_frame_background(painter, frame_rect, photo_rect, f_settings)

        # 8. (相框功能) 繪製帶有圓角的相片
        self._draw_photo(painter, photo_rect, scaled_photo, f_settings)

        # 9. (浮水印功能) 繪製浮水印
        self._draw_watermark(painter, frame_rect, photo_rect, w_settings, exif_data)

        painter.end()

        # 10. (相框功能) 根據設定啟用或禁用圖片陰影
        self.shadow.setEnabled(f_settings.get('photo_shadow', True))
        self.image_preview_label.setGraphicsEffect(self.shadow)

        # 11. 顯示最終成品
        self.image_preview_label.setPixmap(final_pixmap)

    def _draw_frame_background(self, painter: QPainter, frame_rect: QRect, photo_rect: QRect, f_settings: dict):
        """輔助函式：繪製相框背景（純色或模糊延伸）"""
        frame_style = f_settings.get('style', 'solid_color')
        frame_radius = f_settings.get('frame_radius', 5) / 100.0 * min(frame_rect.width(), frame_rect.height()) / 2

        path = QPainterPath()
        path.addRoundedRect(QRectF(frame_rect), frame_radius, frame_radius)
        painter.save()
        painter.setClipPath(path)

        if frame_style == 'solid_color':
            color = QColor(f_settings.get('color', '#FFFFFFFF'))
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(frame_rect)

        elif frame_style == 'blur_extend':
            # 使用 Pillow 進行模糊處理
            pil_img = Image.open(self.current_image_path)
            blur_radius = f_settings.get('blur_radius', 20)

            # 放大圖片以確保模糊邊緣能填滿相框
            extended_w = int(pil_img.width * (frame_rect.width() / photo_rect.width()))
            extended_h = int(pil_img.height * (frame_rect.height() / photo_rect.height()))
            extended_pil = pil_img.resize((extended_w, extended_h), Image.Resampling.LANCZOS)

            blurred_pil = extended_pil.filter(ImageFilter.GaussianBlur(radius=blur_radius))

            # 將 Pillow 圖片轉回 QPixmap
            blurred_qimage = ImageQt(blurred_pil)
            blurred_pixmap = QPixmap.fromImage(blurred_qimage)

            # 計算繪製位置使其居中
            draw_x = (frame_rect.width() - blurred_pixmap.width()) / 2
            draw_y = (frame_rect.height() - blurred_pixmap.height()) / 2
            painter.drawPixmap(int(draw_x), int(draw_y), blurred_pixmap)

        painter.restore()

    def _draw_photo(self, painter: QPainter, photo_rect: QRect, scaled_photo: QPixmap, f_settings: dict):
        """輔助函式：繪製帶圓角的相片"""
        photo_radius = f_settings.get('photo_radius', 3) / 100.0 * min(photo_rect.width(), photo_rect.height()) / 2

        path = QPainterPath()
        path.addRoundedRect(QRectF(photo_rect), photo_radius, photo_radius)

        painter.save()
        painter.setClipPath(path)
        painter.drawPixmap(photo_rect, scaled_photo)
        painter.restore()

    def _draw_watermark(self, painter: QPainter, frame_rect: QRect, photo_rect: QRect, w_settings: dict,
                        exif_data: dict):
        """輔助函式：處理所有浮水印相關的繪製"""
        logo_enabled = w_settings.get('logo_enabled', False)
        text_enabled = w_settings.get('text_enabled', True)

        if not logo_enabled and not text_enabled:
            return

        # 1. 準備 Logo
        logo_pixmap = None
        logo_text = ""
        if logo_enabled:
            logo_source = w_settings.get('logo_source', 'auto_detect')
            if logo_source == 'auto_detect':
                make = exif_data.get('Make', '')
                logo_path = get_logo_path(make, str(self.asset_manager.default_logos_dir))
                if logo_path:
                    logo_pixmap = QPixmap(logo_path)
            elif logo_source == 'select_from_library':
                logo_key = w_settings.get('logo_source_app', '')
                logo_path = next((p for p in self.asset_manager.get_default_logos() if Path(p).stem == logo_key),
                                 None)
                if logo_path:
                    logo_pixmap = QPixmap(logo_path)
            elif logo_source == 'my_custom_logo':
                logo_key = w_settings.get('logo_source_my_custom', '')
                logo_path = next((p for p in self.asset_manager.get_user_logos() if Path(p).stem == logo_key), None)
                if logo_path:
                    logo_pixmap = QPixmap(logo_path)
            # 'custom_text' 類型由後面的文字部分處理

        # 2. 準備文字
        watermark_text = ""
        if text_enabled:
            text_source = w_settings.get('text_source', 'exif')
            if text_source == 'exif':
                parts = []
                exif_options = w_settings.get('exif_options', {})
                if exif_options.get('model') and exif_data.get('Model'): parts.append(exif_data['Model'])
                if exif_options.get('focal_length') and exif_data.get('FocalLength'): parts.append(
                    f"{exif_data['FocalLength']}mm")
                if exif_options.get('aperture') and exif_data.get('FNumber'): parts.append(
                    f"f/{exif_data['FNumber']}")
                if exif_options.get('shutter') and exif_data.get('ExposureTime'): parts.append(
                    f"{exif_data['ExposureTime']}s")
                if exif_options.get('iso') and exif_data.get('ISO'): parts.append(f"ISO {exif_data['ISO']}")
                watermark_text = "  ".join(parts)
            elif text_source == 'custom':
                watermark_text = w_settings.get('text_custom', '')

        # 如果 Logo 來源是自訂文字，將其作為 logo_text
        if logo_enabled and w_settings.get('logo_source') == 'custom_text':
            logo_text = w_settings.get('logo_text_custom', 'Logo')  # 假設 UI 有 'logo_text_custom'

        # 3. 設定字體和顏色
        font_size_ratio = w_settings.get('font_size', 20) / 100.0
        base_font_size = max(8, int(min(photo_rect.width(), photo_rect.height()) * 0.04))
        font_size = int(base_font_size * font_size_ratio)

        font_family_name = "Arial"  # 預設字體
        font_source = w_settings.get('font_family', 'system')
        if font_source == 'system':
            font_family_name = w_settings.get('font_system', 'Arial')
        elif font_source == 'my_custom':
            # 這裡需要從 asset_manager 獲取真實的字體家族名稱
            font_key = w_settings.get('font_my_custom', '')
            user_fonts = self.asset_manager.get_user_fonts()
            for path, families in user_fonts.items():
                if self.asset_manager._create_key_from_name(Path(path).stem) == font_key:
                    font_family_name = families[0] if families else "Arial"
                    break

        font = QFont(font_family_name, font_size)
        painter.setFont(font)
        painter.setPen(QColor(w_settings.get('font_color', '#FFFFFFFF')))

        # 4. 計算尺寸和位置
        fm = painter.fontMetrics()
        text_rect = fm.boundingRect(watermark_text)
        logo_text_rect = fm.boundingRect(logo_text)

        # 根據 Logo 大小設定調整 Logo 尺寸
        logo_h = int(font_size * 1.2)
        if logo_pixmap:
            logo_pixmap = logo_pixmap.scaledToHeight(int(logo_h * (w_settings.get('logo_size', 30) / 50.0)),
                                                     Qt.TransformationMode.SmoothTransformation)

        # 決定浮水印區塊的總寬高
        layout = w_settings.get('layout', 'logo_left')
        gap = int(font_size * 0.3)  # Logo 和文字的間距
        total_w, total_h = 0, 0

        logo_w = logo_pixmap.width() if logo_pixmap else logo_text_rect.width()
        logo_h = logo_pixmap.height() if logo_pixmap else logo_text_rect.height()
        text_w = text_rect.width()
        text_h = text_rect.height()

        if layout in ['logo_top', 'logo_bottom']:  # 垂直排列
            total_w = max(logo_w, text_w)
            total_h = logo_h + text_h + gap if logo_enabled and text_enabled else logo_h or text_h
        else:  # 水平排列 (logo_left)
            total_w = logo_w + text_w + gap if logo_enabled and text_enabled else logo_w or text_w
            total_h = max(logo_h, text_h)

        # 5. 決定浮水印的錨點 (左上角)
        area = w_settings.get('area', 'in_photo')
        align = w_settings.get('align', 'bottom_right')
        target_rect = photo_rect if area == 'in_photo' else frame_rect
        padding = int(font_size * 0.5)  # 浮水印到邊界的距離

        x, y = 0, 0
        if 'left' in align: x = target_rect.left() + padding
        if 'center' in align: x = target_rect.center().x() - total_w / 2
        if 'right' in align: x = target_rect.right() - total_w - padding
        if 'top' in align: y = target_rect.top() + padding
        if 'middle' in align: y = target_rect.center().y() - total_h / 2
        if 'bottom' in align: y = target_rect.bottom() - total_h - padding

        # 如果在相框內，但相片上方，需要特別處理
        if area == 'in_frame' and 'top' in align:
            y = padding
        if area == 'in_frame' and 'bottom' in align:
            y = photo_rect.bottom() + padding

        # 6. 繪製 Logo 和文字
        painter.save()
        painter.translate(x, y)  # 移動畫布原點到錨點

        logo_x, logo_y, text_x, text_y = 0, 0, 0, 0

        # 根據佈局計算內部相對位置
        if layout == 'logo_top':
            logo_x = (total_w - logo_w) / 2
            text_x = (total_w - text_w) / 2
            text_y = logo_h + gap
        elif layout == 'logo_bottom':
            logo_x = (total_w - logo_w) / 2
            logo_y = text_h + gap
            text_x = (total_w - text_w) / 2
        else:  # logo_left
            text_x = logo_w + gap
            logo_y = (total_h - logo_h) / 2
            text_y = (total_h - text_h) / 2 + fm.ascent()  # 對齊文字基線

        # 繪製
        if logo_enabled:
            if logo_pixmap:
                painter.drawPixmap(int(logo_x), int(logo_y), logo_pixmap)
            elif logo_text:
                painter.drawText(QPoint(int(logo_x), int(logo_y) + fm.ascent()), logo_text)

        if text_enabled:
            painter.drawText(QPoint(int(text_x), int(text_y)), watermark_text)

        painter.restore()
