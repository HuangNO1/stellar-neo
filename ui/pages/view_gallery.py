import os
from pathlib import Path

from PIL import Image, ImageFilter
from PIL.ImageQt import ImageQt
from PyQt6 import uic
from PyQt6.QtCore import Qt, QSize, QRectF, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QPainterPath, QBrush, QFontMetrics, QPen
from PyQt6.QtWidgets import QWidget, QFileDialog, QListWidgetItem, QGraphicsDropShadowEffect, QGraphicsScene, \
    QGraphicsView, QGraphicsPathItem, QGraphicsPixmapItem, QGraphicsSimpleTextItem, QApplication
from qfluentwidgets import MessageBox, Flyout

from core.asset_manager import AssetManager
from core.exif_reader import get_exif_data
from core.logo_mapping import get_logo_path
from core.settings_manager import SettingsManager
from core.translator import Translator
from ui.customs.custom_icon import MyFluentIcon
from ui.customs.export_message import ExportMessageBox
from ui.customs.gallery_item_widget import GalleryItemWidget
from ui.customs.gallery_tabs import GalleryTabs


class GalleryView(QWidget):
    FULL_REDRAW_KEYS = {
        'frame': [
            'enabled', 'padding_top', 'padding_sides', 'padding_bottom',
            'style', 'frame_radius', 'photo_radius', 'blur_radius'
        ],
        'watermark': [
            'layout', 'area', 'align', 'font_size'
        ]
    }

    # TODO 如果文件名過長 需要考慮
    def __init__(self, asset_manager: AssetManager, translator: Translator, parent=None):
        super().__init__(parent)
        uic.loadUi("ui/components/gallery.ui", self)

        self.settings_manager = SettingsManager()
        self.asset_manager = asset_manager
        # --- 國際化核心 ---
        self.translator = translator
        self.tr = self.translator.get

        self.image_items = {}
        self.original_pil_img = None  # 新增此屬性
        self.current_image_path = None
        self.original_pixmap = None
        self._is_selecting_all = False

        # 新增一個用於防抖的計時器
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.setInterval(100)  # 100毫秒延遲，可根據體驗調整
        self.resize_timer.timeout.connect(self._update_display)

        # --- 新增：用於快取的屬性 ---
        self.blur_cache = {}
        # 用於快取上次計算的佈局矩形，避免在局部更新時重新計算
        self.last_frame_rect = None
        self.last_photo_rect = None

        # --- QGraphicsView 核心設定 ---
        self.scene = QGraphicsScene(self)
        self.image_preview_label.setScene(self.scene)  # 在 .ui 中，這現在是 QGraphicsView
        # 設定 View 的渲染提示和行為，以獲得最佳品質和體驗
        self.image_preview_label.setRenderHints(
            QPainter.RenderHint.Antialiasing |
            QPainter.RenderHint.TextAntialiasing |
            QPainter.RenderHint.SmoothPixmapTransform
        )
        self.image_preview_label.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.image_preview_label.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.image_preview_label.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.image_preview_label.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.image_preview_label.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        # 設定透明背景，讓 frame_shadow 生效
        self.image_preview_label.setStyleSheet("background: transparent; border: none;")

        # --- 新增：場景中的圖形物件 (Graphics Items) ---
        # 我們將創建一次，然後只更新它們的屬性
        self.frame_item = QGraphicsPathItem()
        self.photo_item = QGraphicsPathItem()
        self.logo_item = QGraphicsPixmapItem()
        self.logo_text_item = QGraphicsSimpleTextItem()
        self.watermark_text_item = QGraphicsSimpleTextItem()
        self.prompt_item = QGraphicsSimpleTextItem()  # 用於顯示提示文字

        # 使用 ZValue 控制圖層順序 (數字越大，越在上層)
        self.frame_item.setZValue(0)
        self.photo_item.setZValue(10)
        self.logo_item.setZValue(20)
        self.logo_text_item.setZValue(20)
        self.watermark_text_item.setZValue(20)
        self.prompt_item.setZValue(30)

        # 將物件添加到場景中
        self.scene.addItem(self.frame_item)
        self.scene.addItem(self.photo_item)
        self.scene.addItem(self.logo_item)
        self.scene.addItem(self.logo_text_item)
        self.scene.addItem(self.watermark_text_item)
        self.scene.addItem(self.prompt_item)

        # 照片陰影效果 (直接作用於照片物件)
        self.photo_shadow_effect = QGraphicsDropShadowEffect(self)
        self.photo_shadow_effect.setColor(QColor(0, 0, 0, 100))
        self.photo_shadow_effect.setBlurRadius(40)
        self.photo_shadow_effect.setOffset(5, 5)
        self.photo_item.setGraphicsEffect(self.photo_shadow_effect)

        # 相框外部陰影 (作用於整個 QGraphicsView 元件)
        self.frame_shadow_effect = QGraphicsDropShadowEffect(self)
        self.frame_shadow_effect.setBlurRadius(30)
        self.frame_shadow_effect.setColor(QColor(0, 0, 0, 80))
        self.frame_shadow_effect.setOffset(0, 0)
        self.image_preview_label.setGraphicsEffect(self.frame_shadow_effect)

        # 設定拖拽事件
        self.setAcceptDrops(True)  # <--- 在主元件上啟用拖放

        # 加入右側的設定 Tabs
        # 將 translator 傳遞給子元件
        self.tabs = GalleryTabs(self.asset_manager, self.translator, self)
        self.right_layout.addWidget(self.tabs)

        self._translate_ui()
        self._connect_signals()
        self._clear_preview()

    def _translate_ui(self):
        self.import_button.setText(self.tr("gallery_import_button", "Import"))
        self.select_all_checkbox.setText(self.tr("gallery_select_all", "Select All"))
        self.clear_selected_button.setText(self.tr("gallery_clear_selected", "Clear Selected"))
        self.export_button.setText(self.tr("gallery_export_button", "Export Selected Images"))
        # TODO 加上導出功能
        self._clear_preview()  # 清除時會設定預設文字
        self._update_select_all_checkbox_state()  # 更新 UI 狀態

    def resizeEvent(self, event):
        """
        重寫 resizeEvent。
        每當視窗或 splitter 大小改變時，此函數會被呼叫。
        """
        super().resizeEvent(event)
        self.resize_timer.start()  # 啟動或重置計時器

    def _connect_signals(self):
        """連接所有元件的信號與槽函數。"""
        self.import_button.clicked.connect(self._open_image_dialog)
        self.image_list.currentItemChanged.connect(self._on_list_item_selected)
        # 將 splitterMoved 連接到計時器，而不是直接更新
        self.main_splitter.splitterMoved.connect(self.resize_timer.start)

        # 連接到優化後的信號和槽
        self.tabs.settingsChanged.connect(self._handle_settings_change)

        # 連接新的控制按鈕信號
        self.select_all_checkbox.stateChanged.connect(self._on_select_all_changed)
        self.clear_selected_button.clicked.connect(self._on_clear_selected_clicked)

        # 連接 匯出按鈕 匯出圖片
        self.export_button.clicked.connect(self._on_export_button_clicked)

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
                    self._update_display()  # 更新顯示以顯示提示文字

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
                    self._update_display()

            self._update_select_all_checkbox_state()

    def _on_export_button_clicked(self):
        """
        批量導出選中的圖片。
        此方法會獲取當前設定，應用到所有選中的圖片上，並將它們保存到用戶指定的目錄中。
        """
        # 1. 獲取所有選中的圖片路徑
        selected_paths = []
        for i in range(self.image_list.count()):
            item_widget = self.image_list.itemWidget(self.image_list.item(i))
            if item_widget and item_widget.is_checked():
                path = self.image_list.item(i).data(Qt.ItemDataRole.UserRole)
                selected_paths.append(path)

        # 2. 檢查是否有選中的圖片，若無則提示
        if not selected_paths:
            Flyout.create(
                icon=MyFluentIcon.WARNING,
                title=self.tr('export_no_selection_title', 'No Images Selected'),
                content=self.tr('export_no_selection_content', 'Please select images to export.'),
                target=self.export_button,
                parent=self.window(),
                isClosable=True
            )
            return

        # 3. 獲取導出目錄
        last_dir = self.settings_manager.get('last_export_dir', os.path.expanduser("~"))
        output_dir = QFileDialog.getExistingDirectory(
            self,
            self.tr("gallery_export_dialog_title", "Select Export Directory"),
            last_dir
        )

        if not output_dir:
            return  # 用戶取消操作

        self.settings_manager.set('last_export_dir', output_dir)

        # 4. 準備進度條對話框
        total_count = len(selected_paths)
        export_dialog = ExportMessageBox(self.translator, self.window(), total=total_count)

        self.is_export_cancelled = False

        def on_cancel():
            self.is_export_cancelled = True

        export_dialog.cancelExport.connect(on_cancel)
        export_dialog.show()

        # 5. 獲取當前所有設定
        all_settings = self.tabs._get_current_settings()

        # 6. 循環處理並導出每張圖片
        for i, path in enumerate(selected_paths):
            QApplication.processEvents()  # 處理UI事件，讓UI保持響應，特別是“取消”按鈕
            if self.is_export_cancelled:
                break

            # 更新進度條顯示的文字
            export_dialog.setCurrentProgress(i, f"{i} / {total_count} - {os.path.basename(path)}")

            try:
                # 核心：使用離屏渲染方法生成最終圖片
                final_pixmap = self._render_image_for_export(path, all_settings)

                if final_pixmap:
                    base_name = os.path.basename(path)
                    name, ext = os.path.splitext(base_name)
                    # 您未來可以在此處提供更多導出選項 (格式、品質、命名規則等)
                    output_filename = f"{name}_framed{ext}"
                    output_path = os.path.join(output_dir, output_filename)

                    # 保存 QPixmap 到文件，可以指定品質 (JPEG)
                    if not final_pixmap.save(output_path, quality=95):
                        raise IOError(f"Failed to save {output_path}")
                else:
                    print(f"Warning: Rendering failed for {path}, skipping.")

            except Exception as e:
                print(f"Error exporting {path}: {e}")
                export_dialog.setExportError(str(e))
                QTimer.singleShot(4000, export_dialog.close)  # 顯示錯誤4秒後關閉
                return  # 出錯後終止導出

        # 7. 導出結束
        if not self.is_export_cancelled:
            export_dialog.setExportCompleted()
            QTimer.singleShot(1500, export_dialog.close)  # 顯示完成1.5秒後關閉
        else:
            export_dialog.close()

    def _render_image_for_export(self, image_path: str, all_settings: dict) -> QPixmap:
        """
        為導出功能，離屏渲染單張圖片。
        此方法創建一個臨時的 QGraphicsScene，並將所有效果繪製上去，
        最後將 Scene 內容渲染成一個 QPixmap。
        所有計算都基於原始圖片尺寸，以保證輸出品質。
        """
        # --- 1. 載入原始圖片和數據 ---
        try:
            with Image.open(image_path) as img:
                pil_img = img.copy()
        except Exception as e:
            print(f"無法使用 Pillow 載入圖片 {image_path}: {e}")
            return None

        original_pixmap = QPixmap(image_path)
        if original_pixmap.isNull():
            return None

        exif_data = self.image_items.get(image_path, {}).get('exif', {})
        f_settings = all_settings.get('frame', {})
        w_settings = all_settings.get('watermark', {})

        # --- 2. 基於原始圖片尺寸計算佈局 ---
        img_w, img_h = original_pixmap.width(), original_pixmap.height()
        base_padding = min(img_w, img_h) * 0.1
        padding_top = int(base_padding * f_settings.get('padding_top', 10) / 100)
        padding_sides = int(base_padding * f_settings.get('padding_sides', 10) / 100)
        padding_bottom = int(base_padding * f_settings.get('padding_bottom', 10) / 100)

        if not f_settings.get('enabled', True):
            padding_top = padding_sides = padding_bottom = 0

        frame_w = img_w + padding_sides * 2
        frame_h = img_h + padding_top + padding_bottom
        frame_rect = QRectF(0, 0, frame_w, frame_h)
        photo_rect = QRectF(padding_sides, padding_top, img_w, img_h)

        # --- 3. 創建臨時的 Scene 和圖形物件 ---
        temp_scene = QGraphicsScene()
        temp_scene.setSceneRect(frame_rect)

        # 為了不影響 UI 上的物件，我們創建全新的臨時物件
        frame_item = QGraphicsPathItem()
        photo_item = QGraphicsPathItem()
        logo_item = QGraphicsPixmapItem()
        logo_text_item = QGraphicsSimpleTextItem()
        watermark_text_item = QGraphicsSimpleTextItem()

        # 設置 Z-Value (圖層順序)
        frame_item.setZValue(0)
        photo_item.setZValue(10)
        logo_item.setZValue(20)
        logo_text_item.setZValue(20)
        watermark_text_item.setZValue(20)

        temp_scene.addItem(frame_item)
        temp_scene.addItem(photo_item)
        temp_scene.addItem(logo_item)
        temp_scene.addItem(logo_text_item)
        temp_scene.addItem(watermark_text_item)

        # --- 4. 配置和繪製每個圖形物件 ---

        # (A) 繪製相框
        if f_settings.get('enabled', True):
            frame_radius = f_settings.get('frame_radius', 5) / 100.0 * min(frame_w, frame_h) / 2
            path = QPainterPath()
            path.addRoundedRect(frame_rect, frame_radius, frame_radius)
            frame_item.setPath(path)
            frame_item.setPen(QPen(Qt.PenStyle.NoPen))  # 無論何種樣式，都先取消邊框

            frame_style = f_settings.get('style', 'solid_color')

            # vvvvvvvvvvvvvv 重構後的畫刷設定邏輯 vvvvvvvvvvvvvv
            if frame_style == 'solid_color':
                frame_item.setBrush(QBrush(QColor(f_settings.get('color', '#FFFFFFFF'))))

            elif frame_style == 'blur_extend' and pil_img:
                # 1. 獲取使用者在UI上設定的基礎模糊半徑
                base_blur_radius = f_settings.get('blur_radius', 20)

                # 2. 獲取原始圖片尺寸
                pil_w, pil_h = pil_img.size

                # 3. 計算縮放比例並應用
                export_blur_radius = base_blur_radius
                if hasattr(self, 'last_preview_photo_size') and self.last_preview_photo_size.width() > 0:
                    preview_w = self.last_preview_photo_size.width()
                    scale_factor = pil_w / preview_w
                    export_blur_radius = base_blur_radius * scale_factor
                    print(f"[DEBUG] Preview Width: {preview_w}, Original Width: {pil_w}, Scale: {scale_factor:.2f}")
                    print(f"[DEBUG] Base Radius: {base_blur_radius}, Scaled Export Radius: {export_blur_radius:.2f}")

                # 後續計算
                target_w, target_h = int(frame_w), int(frame_h)
                scale = max(target_w / pil_w, target_h / pil_h)
                resized = pil_img.resize((int(pil_w * scale), int(pil_h * scale)), Image.Resampling.LANCZOS)
                left, top = (resized.width - target_w) / 2, (resized.height - target_h) / 2
                cropped = resized.crop((left, top, left + target_w, top + target_h))

                if cropped.mode != 'RGB':
                    cropped = cropped.convert('RGB')

                blurred = None
                # 4. 使用計算後、適用於高解析度圖片的模糊半徑
                if export_blur_radius > 0:
                    blurred = cropped.filter(ImageFilter.GaussianBlur(radius=export_blur_radius))
                else:
                    blurred = cropped

                # 關鍵：將 PIL Image 轉換為 QPixmap，並保留對 QImage 的引用以防被回收
                blurred_qimage = ImageQt(blurred)
                blurred_pixmap = QPixmap.fromImage(blurred_qimage)

                # 增加建議的保險措施
                if blurred_pixmap.isNull():
                    print("警告：模糊相框未能正確轉換為 QPixmap，將使用灰色作為備用。")
                    frame_item.setBrush(QBrush(QColor("#CCCCCC")))
                else:
                    # 1. 創建一個空的畫刷
                    image_brush = QBrush()

                    # 2. 使用 .setTexture() 將 QPixmap 明確設置為畫刷的紋理
                    image_brush.setTexture(blurred_pixmap)

                    # 3. 將配置好的畫刷應用到 item
                    frame_item.setBrush(image_brush)

            # (B) 繪製照片 (帶圓角和陰影)
            photo_radius = f_settings.get('photo_radius', 3) / 100.0 * min(photo_rect.width(),
                                                                           photo_rect.height()) / 2
            # 將物件移動到照片應在的位置
            photo_item.setPos(photo_rect.topLeft())

            # 在物件的本地座標系中定義路徑 (從0,0開始)
            photo_path = QPainterPath()
            photo_path.addRoundedRect(0, 0, photo_rect.width(), photo_rect.height(), photo_radius, photo_radius)
            photo_item.setPath(photo_path)

            # 直接使用原始圖片作為畫刷，無需複雜的座標變換
            photo_item.setBrush(QBrush(original_pixmap))
            photo_item.setPen(QPen(Qt.PenStyle.NoPen))

            if f_settings.get('enabled', True) and f_settings.get('photo_shadow', True):
                shadow = QGraphicsDropShadowEffect()
                shadow.setColor(QColor(0, 0, 0, 100))
                shadow.setBlurRadius(60)
                shadow.setOffset(10, 10)
                photo_item.setGraphicsEffect(shadow)

        # (C) 繪製浮水印 (此處為 _update_watermark 方法的邏輯複現)
        # 為了在不大規模重構 _update_watermark 的情況下完成功能，我們在此處重新實現其核心邏輯
        # 並將所有 self.xxx_item 的操作改為對應的臨時 item (例如 logo_item)
        logo_enabled = w_settings.get('logo_enabled', False)
        text_enabled = w_settings.get('text_enabled', True)
        if logo_enabled or text_enabled:
            # --- Start of watermark logic replication ---
            logo_pixmap = None
            logo_text = ""
            if logo_enabled:
                logo_source = w_settings.get('logo_source', 'auto_detect')
                if logo_source == 'auto_detect':
                    make = exif_data.get('Make', '')
                    logo_path = get_logo_path(make, str(self.asset_manager.default_logos_dir))
                    if logo_path: logo_pixmap = QPixmap(logo_path)
                elif logo_source == 'select_from_library':
                    logo_key = w_settings.get('logo_source_app', '')
                    logo_path = next((p for p in self.asset_manager.get_default_logos() if Path(p).stem == logo_key),
                                     None)
                    if logo_path: logo_pixmap = QPixmap(logo_path)
                elif logo_source == 'my_custom_logo':
                    logo_key = w_settings.get('logo_source_my_custom', '')
                    logo_path = next((p for p in self.asset_manager.get_user_logos() if Path(p).stem == logo_key), None)
                    if logo_path: logo_pixmap = QPixmap(logo_path)
                elif w_settings.get('logo_source') == 'custom_text':
                    logo_text = w_settings.get('logo_text_custom', 'Logo')

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

            # 1. 直接使用導出畫布上的照片尺寸 (photo_rect) 來計算，這是最準確的方式。
            #    photo_rect 此時代表的是原始圖片的尺寸。
            export_photo_w = photo_rect.width()
            export_photo_h = photo_rect.height()

            # 2. 應用與 `_update_watermark` 中完全相同的公式，確保比例一致。
            #    基礎大小現在是相對於全尺寸圖片，而非預覽圖。
            base_font_size = max(8, int(min(export_photo_w, export_photo_h) * 0.04))

            # 3. 根據使用者設定的滑桿百分比，計算最終的字體大小。
            font_size_ratio = w_settings.get('font_size', 20) / 100.0
            font_size = int(base_font_size * font_size_ratio)

            # 後續所有尺寸相關的計算（如 gap, padding, logo_h_scaled）都將基於這個
            # 正確縮放後的 font_size，從而保證整體比例一致。
            font_color = QColor(w_settings.get('font_color', '#FFFFFFFF'))

            font_family_name = "Arial"
            font_source = w_settings.get('font_family', 'system')
            if font_source == 'system':
                font_family_name = w_settings.get('font_system', 'Arial')
            elif font_source == 'my_custom':
                font_key = w_settings.get('font_my_custom', '')
                user_fonts = self.asset_manager.get_user_fonts()
                for path, families in user_fonts.items():
                    if self.asset_manager._create_key_from_name(Path(path).stem) == font_key:
                        font_family_name = families[0] if families else "Arial"
                        break

            watermark_font = QFont(font_family_name, font_size)
            logo_font = QFont(font_family_name, int(font_size * 1.2))

            fm = QFontMetrics(watermark_font)
            text_rect = fm.boundingRect(watermark_text)
            logo_fm = QFontMetrics(logo_font)
            logo_text_rect = logo_fm.boundingRect(logo_text)

            if logo_pixmap and not logo_pixmap.isNull():
                logo_h_scaled = int(logo_font.pointSizeF() * 1.2 * (w_settings.get('logo_size', 30) / 50.0))
                logo_pixmap = logo_pixmap.scaledToHeight(logo_h_scaled, Qt.TransformationMode.SmoothTransformation)

            gap = int(font_size * 0.3)
            logo_w = logo_pixmap.width() if logo_pixmap and not logo_pixmap.isNull() else logo_text_rect.width()
            logo_h = logo_pixmap.height() if logo_pixmap and not logo_pixmap.isNull() else logo_text_rect.height()
            text_w = text_rect.width()
            text_h = text_rect.height()

            layout = w_settings.get('layout', 'logo_left')
            total_w, total_h = 0, 0
            if layout in ['logo_top', 'logo_bottom']:
                total_w = max(logo_w, text_w)
                total_h = (logo_h + text_h + gap) if (
                        logo_enabled and text_enabled and logo_w > 0 and text_w > 0) else (
                        logo_h or text_h)
            else:  # logo_left or logo_right
                total_w = (logo_w + text_w + gap) if (
                        logo_enabled and text_enabled and logo_w > 0 and text_w > 0) else (
                        logo_w or text_w)
                total_h = max(logo_h, text_h)

            # 5. 決定浮水印的錨點 (左上角)
            area = w_settings.get('area', 'in_photo')
            align = w_settings.get('align', 'bottom_right')
            # 如果相框被禁用，則強制將區域設為 'in_photo'
            f_settings = self.tabs._get_current_settings().get('frame', {})
            if not f_settings.get('enabled', True):
                area = 'in_photo'

            target_rect = photo_rect if area == 'in_photo' else frame_rect
            padding = int(font_size * 0.5)

            x, y = 0, 0
            # --- 水平定位 (X) ---
            if 'left' in align:
                x = target_rect.left() + padding
            elif 'center' in align:
                x = target_rect.center().x() - total_w / 2
            elif 'right' in align:
                x = target_rect.right() - total_w - padding

            # --- 垂直定位 (Y) ---
            if area == 'in_photo':
                if 'top' in align:
                    y = target_rect.top() + padding
                elif 'middle' in align:  # QGraphicsScene 中沒有 middle，這裡假設是 center
                    y = target_rect.center().y() - total_h / 2
                elif 'bottom' in align:
                    y = target_rect.bottom() - total_h - padding
            elif area == 'in_frame':
                if 'top' in align:
                    # 垂直置中於上邊框的空白區域
                    top_padding_space = photo_rect.top()
                    y = (top_padding_space - total_h) / 2
                elif 'bottom' in align:
                    # 垂直置中於下邊框的空白區域
                    bottom_padding_space = frame_rect.bottom() - photo_rect.bottom()
                    y = photo_rect.bottom() + (bottom_padding_space - total_h) / 2
                else:  # 對於 in_frame 模式，middle/center/left/right 的 Y 軸與 in_photo 相同
                    y = target_rect.center().y() - total_h / 2

            # 6. 計算內部相對位置並更新物件
            logo_x_rel, logo_y_rel, text_x_rel, text_y_rel = 0, 0, 0, 0
            if layout == 'logo_top':
                # [修正] 移除水平居中，改為左對齊以保持一致性
                logo_x_rel = 0
                text_x_rel = 0
                logo_y_rel = 0
                text_y_rel = logo_h + gap
            elif layout == 'logo_bottom':
                # [修正] 移除水平居中，改為左對齊以保持一致性
                logo_x_rel = 0
                text_x_rel = 0
                text_y_rel = 0
                logo_y_rel = text_h + gap
            else:  # logo_left or logo_right
                logo_y_rel = (total_h - logo_h) / 2
                text_y_rel = (total_h - text_h) / 2
                if layout == 'logo_right':
                    text_x_rel = 0
                    logo_x_rel = text_w + gap
                else:  # logo_left
                    logo_x_rel = 0
                    text_x_rel = logo_w + gap

            if logo_enabled:
                if logo_pixmap and not logo_pixmap.isNull():
                    logo_item.setPixmap(logo_pixmap)
                    logo_item.setPos(x + logo_x_rel, y + logo_y_rel)
                elif logo_text:
                    logo_text_item.setText(logo_text)
                    logo_text_item.setFont(logo_font)
                    logo_text_item.setBrush(font_color)
                    logo_text_item.setPos(x + logo_x_rel, y + logo_y_rel)

            if text_enabled and watermark_text:
                watermark_text_item.setText(watermark_text)
                watermark_text_item.setFont(watermark_font)
                watermark_text_item.setBrush(font_color)
                watermark_text_item.setPos(x + text_x_rel, y + text_y_rel)
            # --- End of watermark logic replication ---

        # --- 5. 將 Scene 渲染到 QPixmap ---
        output_pixmap = QPixmap(int(frame_w), int(frame_h))
        output_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(output_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        temp_scene.render(painter)
        painter.end()

        return output_pixmap

    def _clear_preview(self):
        """清空預覽，隱藏所有物件並顯示提示文字"""
        self.current_image_path = None
        self.original_pixmap = None
        # 隱藏所有主要物件
        self.frame_item.hide()
        self.photo_item.hide()
        self.logo_item.hide()
        self.logo_text_item.hide()
        self.watermark_text_item.hide()
        # 設定並顯示提示文字
        prompt_text = self.tr("gallery_drop_prompt", "Drop image here")
        self.prompt_item.setText(prompt_text)
        self.prompt_item.setFont(QFont("Arial", 16))
        self.prompt_item.setBrush(QColor("#aaa"))
        self.prompt_item.show()

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
            self._update_display()  # 更新顯示以顯示提示文字
            return

        path = current_item.data(Qt.ItemDataRole.UserRole)
        if path != self.current_image_path:
            self.current_image_path = path
            self.original_pixmap = QPixmap(path)

            # 處理圖片載入失敗的情況
            if self.original_pixmap.isNull():
                # 這裡可以加入一個錯誤提示的對話框
                self._on_delete_item_requested(path)  # 假設壞圖就直接刪除
                return

                # 新增：預先載入 PIL Image 並處理潛在錯誤
            try:
                # 使用 with 陳述式確保檔案被正確關閉
                with Image.open(path) as img:
                    self.original_pil_img = img
                    # 強制載入圖像資料，將其讀入記憶體
                    self.original_pil_img.load()
            except Exception as e:
                print(f"無法使用 Pillow 載入圖片 {path}: {e}")
                self.original_pil_img = None
                # 可以選擇彈出錯誤訊息或直接移除該項目
                self._on_delete_item_requested(path)
                return

            self.blur_cache.clear()  # 換了新圖，清除模糊快取
            self._update_display()

    # vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
    # --- 核心繪圖與更新 ---
    # vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def _update_frame_shadow(self, enabled: bool):
        """僅更新相框陰影的啟用狀態"""
        self.frame_shadow_effect.setEnabled(enabled)

    def _update_photo_shadow(self, enabled: bool):
        """僅更新照片陰影的啟用狀態"""
        f_settings = self.tabs._get_current_settings().get('frame', {})
        # 照片陰影也依賴於相框是否啟用
        self.photo_shadow_effect.setEnabled(enabled and f_settings.get('enabled', True))

    def _update_frame_color(self, color_hex: str):
        """僅更新相框顏色（僅在純色模式下有效）"""
        f_settings = self.tabs._get_current_settings().get('frame', {})
        if f_settings.get('style') == 'solid_color':
            self.frame_item.setBrush(QBrush(QColor(color_hex)))

    def _redraw_watermark(self):
        """
        僅重繪浮水印，而不重新計算整個場景佈局。
        它會使用快取的 `last_frame_rect` 和 `last_photo_rect`。
        """
        if not self.last_frame_rect or not self.last_photo_rect or not self.current_image_path:
            # 如果沒有快取數據，執行一次完整更新來生成它
            self._update_display()
            return

        all_settings = self.tabs._get_current_settings()
        w_settings = all_settings.get('watermark', {})
        exif_data = self.image_items.get(self.current_image_path, {}).get('exif', {})
        self._update_watermark(self.last_frame_rect, self.last_photo_rect, w_settings, exif_data)

    def _handle_settings_change(self, changes: dict):
        """
        處理設定變更的智慧型插槽。
        - 優先檢查是否需要完整重繪。
        - 若否，則根據變更內容執行對應的局部更新函式。
        """
        if not self.current_image_path:
            return

        frame_changes = changes.get('frame', {})
        watermark_changes = changes.get('watermark', {})

        # 1. 檢查是否觸發了任何需要完整重繪的設定
        if any(key in frame_changes for key in self.FULL_REDRAW_KEYS['frame']) or \
                any(key in watermark_changes for key in self.FULL_REDRAW_KEYS['watermark']):
            self._update_display()
            return  # 執行完完整重繪後，直接返回

        # 2. 若未觸發完整重繪，則處理局部、輕量的更新
        needs_watermark_redraw = False

        # --- 處理相框的局部變更 ---
        if 'frame_shadow' in frame_changes:
            self._update_frame_shadow(frame_changes['frame_shadow'])

        if 'photo_shadow' in frame_changes:
            self._update_photo_shadow(frame_changes['photo_shadow'])

        if 'color' in frame_changes:
            self._update_frame_color(frame_changes['color'])

        # --- 處理浮水印的局部變更 ---
        # 任何未觸發完整重繪的浮水印變更，都只需要重繪浮水印本身
        if watermark_changes:
            needs_watermark_redraw = True

        if needs_watermark_redraw:
            self._redraw_watermark()

    def _update_display(self):
        """
        核心更新函數。它計算佈局，然後調用各自的輔助函數來更新圖形物件。
        """
        if not self.current_image_path or not self.original_pixmap or self.original_pixmap.isNull():
            # 如果沒有圖片，確保場景是空的但提示文字可見
            self._clear_preview()

            # 1. 將 viewport 的矩形映射到 scene 的座標系統，得到當前可見的場景區域
            visible_scene_rect = self.image_preview_label.mapToScene(
                self.image_preview_label.viewport().rect()).boundingRect()

            # 2. 將場景的邊界設定為剛好等於可見區域，這會重設任何縮放或平移
            self.scene.setSceneRect(visible_scene_rect)

            # 3. 獲取提示文字的邊界
            prompt_rect = self.prompt_item.boundingRect()

            # 4. 在場景座標系統中計算居中的位置
            center_x = visible_scene_rect.x() + (visible_scene_rect.width() - prompt_rect.width()) / 2
            center_y = visible_scene_rect.y() + (visible_scene_rect.height() - prompt_rect.height()) / 2

            # 5. 設定提示文字的位置並顯示
            self.prompt_item.setPos(center_x, center_y)
            self.prompt_item.show()
            return

        # 有圖片，隱藏提示文字
        self.prompt_item.hide()

        all_settings = self.tabs._get_current_settings()
        f_settings = all_settings.get('frame', {})
        w_settings = all_settings.get('watermark', {})
        exif_data = self.image_items.get(self.current_image_path, {}).get('exif', {})

        # 1. 計算佈局尺寸
        view_size = self.image_preview_label.viewport().size()
        if view_size.width() <= 20 or view_size.height() <= 20:
            return

        # 步驟 A: 獲取原始圖片尺寸，並計算其在 view_size 中按比例縮放後的大小
        img_size = self.original_pixmap.size()
        image_fitted_in_view = img_size.scaled(view_size, Qt.AspectRatioMode.KeepAspectRatio)

        # 步驟 B: 以圖片實際佔據的區域大小為基準來計算 base_padding，確保比例正確
        base_padding = min(image_fitted_in_view.width(), image_fitted_in_view.height()) * 0.1

        padding_top = int(base_padding * f_settings.get('padding_top', 10) / 100)
        padding_sides = int(base_padding * f_settings.get('padding_sides', 10) / 100)
        padding_bottom = int(base_padding * f_settings.get('padding_bottom', 10) / 100)

        if not f_settings.get('enabled', True):
            padding_top = padding_sides = padding_bottom = 0

        image_area_w = view_size.width() - (padding_sides * 2)
        image_area_h = view_size.height() - padding_top - padding_bottom
        if image_area_w <= 0 or image_area_h <= 0:
            return

        scaled_photo = self.original_pixmap.scaled(
            QSize(int(image_area_w), int(image_area_h)),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # 記錄下當前預覽照片的尺寸，以便導出時計算縮放比例
        self.last_preview_photo_size = scaled_photo.size()

        frame_w = scaled_photo.width() + padding_sides * 2
        frame_h = scaled_photo.height() + padding_top + padding_bottom

        frame_rect = QRectF(0, 0, frame_w, frame_h)
        photo_rect = QRectF(padding_sides, padding_top, scaled_photo.width(), scaled_photo.height())

        self.last_frame_rect = frame_rect
        self.last_photo_rect = photo_rect

        # 2. 更新各個圖形物件
        self._update_frame(frame_rect, photo_rect, f_settings)
        self._update_photo(photo_rect, scaled_photo, f_settings)
        self._update_watermark(frame_rect, photo_rect, w_settings, exif_data)

        # 3. 更新場景並讓 View 適應內容
        self.scene.setSceneRect(frame_rect)
        self.image_preview_label.fitInView(frame_rect, Qt.AspectRatioMode.KeepAspectRatio)

    def _update_frame(self, frame_rect: QRectF, photo_rect: QRectF, f_settings: dict):
        """更新相框物件"""
        self.frame_shadow_effect.setEnabled(f_settings.get('frame_shadow', False))

        if not f_settings.get('enabled', True):
            self.frame_item.hide()
            return

        self.frame_item.show()
        frame_style = f_settings.get('style', 'solid_color')
        frame_radius = f_settings.get('frame_radius', 5) / 100.0 * min(frame_rect.width(), frame_rect.height()) / 2

        path = QPainterPath()
        path.addRoundedRect(frame_rect, frame_radius, frame_radius)
        self.frame_item.setPath(path)

        if frame_style == 'solid_color':
            color = QColor(f_settings.get('color', '#FFFFFFFF'))
            self.frame_item.setBrush(QBrush(color))
            # self.frame_item.setPen(Qt.PenStyle.NoPen)
            self.frame_item.setPen(QPen(Qt.PenStyle.NoPen))
        elif frame_style == 'blur_extend':
            blur_radius = f_settings.get('blur_radius', 20)
            # 使用我們在 _on_list_item_selected 中預載入的 PIL Image
            if not self.original_pil_img:
                self.frame_item.setBrush(QBrush(QColor("transparent")))  # 如果圖像載入失敗則設為透明
                return
            cache_key = (self.current_image_path, blur_radius, int(frame_rect.width()), int(frame_rect.height()))

            if cache_key in self.blur_cache:
                blurred_pixmap = self.blur_cache[cache_key]
            else:
                # --- 開始修正邏輯 ---
                pil_img = self.original_pil_img
                target_w, target_h = int(frame_rect.width()), int(frame_rect.height())
                img_w, img_h = pil_img.size

                if target_w == 0 or target_h == 0 or img_w == 0 or img_h == 0:
                    return  # 避免除以零錯誤

                # 1. 計算統一的縮放比例，以「覆蓋」目標區域
                scale = max(target_w / img_w, target_h / img_h)

                # 2. 等比例縮放
                new_w, new_h = int(img_w * scale), int(img_h * scale)
                resized_pil = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                # 3. 從中心裁切到目標尺寸
                left = (new_w - target_w) / 2
                top = (new_h - target_h) / 2
                right = (new_w + target_w) / 2
                bottom = (new_h + target_h) / 2
                cropped_pil = resized_pil.crop((left, top, right, bottom))

                # 4. 僅在 blur_radius > 0 時應用模糊
                if blur_radius > 0:
                    blurred_pil = cropped_pil.filter(ImageFilter.GaussianBlur(radius=blur_radius))
                else:
                    blurred_pil = cropped_pil  # 半徑為0時，使用清晰的裁切後圖像
                # --- 結束修正邏輯 ---

                blurred_qimage = ImageQt(blurred_pil)
                blurred_pixmap = QPixmap.fromImage(blurred_qimage)
                # 將 pixmap 存入快取，但也要將 qimage 物件一起存入，防止其被回收
                self.blur_cache[cache_key] = (blurred_pixmap, blurred_qimage)

                # 從快取中獲取 pixmap
                pixmap_to_use, _ = self.blur_cache[cache_key]
                self.frame_item.setBrush(QBrush(pixmap_to_use))
                self.frame_item.setPen(QPen(Qt.PenStyle.NoPen))

    def _update_photo(self, photo_rect: QRectF, scaled_photo: QPixmap, f_settings: dict):
        """
        更新照片物件和其陰影。
        使用 QGraphicsPathItem 並用圖片畫刷填充，以實現圓角效果。
        """
        self.photo_item.show()
        # 將 Path Item 移動到正確的位置
        self.photo_item.setPos(photo_rect.topLeft())

        # 1. 在物件的本地座標系中，定義圓角矩形路徑
        photo_radius = f_settings.get('photo_radius', 3) / 100.0 * min(photo_rect.width(), photo_rect.height()) / 2
        photo_path = QPainterPath()
        photo_path.addRoundedRect(0, 0, photo_rect.width(), photo_rect.height(), photo_radius, photo_radius)
        self.photo_item.setPath(photo_path)

        # 2. 建立一個基於圖片的畫刷，並將其應用於路徑物件
        photo_brush = QBrush(scaled_photo)
        self.photo_item.setBrush(photo_brush)

        # 3. 確保沒有邊框被繪製
        self.photo_item.setPen(QPen(Qt.PenStyle.NoPen))

        # 4. 啟用或禁用陰影效果
        self.photo_shadow_effect.setEnabled(f_settings.get('photo_shadow', True) and f_settings.get('enabled', True))

    def _update_watermark(self, frame_rect: QRectF, photo_rect: QRectF, w_settings: dict, exif_data: dict):
        """完整實現：更新浮水印文字和 Logo 物件"""
        # 預先隱藏所有浮水印相關物件
        self.logo_item.hide()
        self.logo_text_item.hide()
        self.watermark_text_item.hide()

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
                if logo_path: logo_pixmap = QPixmap(logo_path)
            elif logo_source == 'select_from_library':
                logo_key = w_settings.get('logo_source_app', '')
                logo_path = next((p for p in self.asset_manager.get_default_logos() if Path(p).stem == logo_key), None)
                if logo_path: logo_pixmap = QPixmap(logo_path)
            elif logo_source == 'my_custom_logo':
                logo_key = w_settings.get('logo_source_my_custom', '')
                logo_path = next((p for p in self.asset_manager.get_user_logos() if Path(p).stem == logo_key), None)
                if logo_path: logo_pixmap = QPixmap(logo_path)
            elif w_settings.get('logo_source') == 'custom_text':
                logo_text = w_settings.get('logo_text_custom', 'Logo')

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
                if exif_options.get('aperture') and exif_data.get('FNumber'): parts.append(f"f/{exif_data['FNumber']}")
                if exif_options.get('shutter') and exif_data.get('ExposureTime'): parts.append(
                    f"{exif_data['ExposureTime']}s")
                if exif_options.get('iso') and exif_data.get('ISO'): parts.append(f"ISO {exif_data['ISO']}")
                watermark_text = "  ".join(parts)
            elif text_source == 'custom':
                watermark_text = w_settings.get('text_custom', '')

        # 3. 設定字體和顏色
        font_size_ratio = w_settings.get('font_size', 20) / 100.0
        base_font_size = max(8, int(min(photo_rect.width(), photo_rect.height()) * 0.04))
        font_size = int(base_font_size * font_size_ratio)
        font_color = QColor(w_settings.get('font_color', '#FFFFFFFF'))

        font_family_name = "Arial"
        font_source = w_settings.get('font_family', 'system')
        if font_source == 'system':
            font_family_name = w_settings.get('font_system', 'Arial')
        elif font_source == 'my_custom':
            font_key = w_settings.get('font_my_custom', '')
            user_fonts = self.asset_manager.get_user_fonts()
            for path, families in user_fonts.items():
                if self.asset_manager._create_key_from_name(Path(path).stem) == font_key:
                    font_family_name = families[0] if families else "Arial"
                    break

        watermark_font = QFont(font_family_name, font_size)
        logo_font = QFont(font_family_name, int(font_size * 1.2))

        # 4. 計算尺寸和位置
        fm = QFontMetrics(watermark_font)
        text_rect = fm.boundingRect(watermark_text)
        logo_fm = QFontMetrics(logo_font)
        logo_text_rect = logo_fm.boundingRect(logo_text)

        if logo_pixmap and not logo_pixmap.isNull():
            logo_h_scaled = int(logo_font.pointSizeF() * 1.2 * (w_settings.get('logo_size', 30) / 50.0))
            logo_pixmap = logo_pixmap.scaledToHeight(logo_h_scaled, Qt.TransformationMode.SmoothTransformation)

        gap = int(font_size * 0.3)
        logo_w = logo_pixmap.width() if logo_pixmap and not logo_pixmap.isNull() else logo_text_rect.width()
        logo_h = logo_pixmap.height() if logo_pixmap and not logo_pixmap.isNull() else logo_text_rect.height()
        text_w = text_rect.width()
        text_h = text_rect.height()

        layout = w_settings.get('layout', 'logo_left')
        total_w, total_h = 0, 0
        if layout in ['logo_top', 'logo_bottom']:
            total_w = max(logo_w, text_w)
            total_h = (logo_h + text_h + gap) if (logo_enabled and text_enabled and logo_w > 0 and text_w > 0) else (
                    logo_h or text_h)
        else:  # logo_left or logo_right
            total_w = (logo_w + text_w + gap) if (logo_enabled and text_enabled and logo_w > 0 and text_w > 0) else (
                    logo_w or text_w)
            total_h = max(logo_h, text_h)

        # 5. 決定浮水印的錨點 (左上角)
        area = w_settings.get('area', 'in_photo')
        align = w_settings.get('align', 'bottom_right')
        # 如果相框被禁用，則強制將區域設為 'in_photo'
        f_settings = self.tabs._get_current_settings().get('frame', {})
        if not f_settings.get('enabled', True):
            area = 'in_photo'

        target_rect = photo_rect if area == 'in_photo' else frame_rect
        padding = int(font_size * 0.5)

        x, y = 0, 0
        # --- 水平定位 (X) ---
        if 'left' in align:
            x = target_rect.left() + padding
        elif 'center' in align:
            x = target_rect.center().x() - total_w / 2
        elif 'right' in align:
            x = target_rect.right() - total_w - padding

        # --- 垂直定位 (Y) ---
        if area == 'in_photo':
            if 'top' in align:
                y = target_rect.top() + padding
            elif 'middle' in align:  # QGraphicsScene 中沒有 middle，這裡假設是 center
                y = target_rect.center().y() - total_h / 2
            elif 'bottom' in align:
                y = target_rect.bottom() - total_h - padding
        elif area == 'in_frame':
            if 'top' in align:
                # 垂直置中於上邊框的空白區域
                top_padding_space = photo_rect.top()
                y = (top_padding_space - total_h) / 2
            elif 'bottom' in align:
                # 垂直置中於下邊框的空白區域
                bottom_padding_space = frame_rect.bottom() - photo_rect.bottom()
                y = photo_rect.bottom() + (bottom_padding_space - total_h) / 2
            else:  # 對於 in_frame 模式，middle/center/left/right 的 Y 軸與 in_photo 相同
                y = target_rect.center().y() - total_h / 2

        # 6. 計算內部相對位置並更新物件
        logo_x_rel, logo_y_rel, text_x_rel, text_y_rel = 0, 0, 0, 0
        if layout == 'logo_top':
            # [修正] 移除水平居中，改為左對齊以保持一致性
            logo_x_rel = 0
            text_x_rel = 0
            logo_y_rel = 0
            text_y_rel = logo_h + gap
        elif layout == 'logo_bottom':
            # [修正] 移除水平居中，改為左對齊以保持一致性
            logo_x_rel = 0
            text_x_rel = 0
            text_y_rel = 0
            logo_y_rel = text_h + gap
        else:  # logo_left or logo_right
            logo_y_rel = (total_h - logo_h) / 2
            text_y_rel = (total_h - text_h) / 2
            if layout == 'logo_right':
                text_x_rel = 0
                logo_x_rel = text_w + gap
            else:  # logo_left
                logo_x_rel = 0
                text_x_rel = logo_w + gap

        if logo_enabled:
            if logo_pixmap and not logo_pixmap.isNull():
                self.logo_item.setPixmap(logo_pixmap)
                self.logo_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
                self.logo_item.setPos(x + logo_x_rel, y + logo_y_rel)
                self.logo_item.show()
            elif logo_text:
                self.logo_text_item.setText(logo_text)
                self.logo_text_item.setFont(logo_font)
                self.logo_text_item.setBrush(font_color)
                self.logo_text_item.setPos(x + logo_x_rel, y + logo_y_rel)
                self.logo_text_item.show()

        if text_enabled and watermark_text:
            self.watermark_text_item.setText(watermark_text)
            self.watermark_text_item.setFont(watermark_font)
            self.watermark_text_item.setBrush(font_color)
            self.watermark_text_item.setPos(x + text_x_rel, y + text_y_rel)
            self.watermark_text_item.show()
