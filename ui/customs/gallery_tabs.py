import json

from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget, QStackedWidget, QVBoxLayout
from qfluentwidgets import TabBar
from qfluentwidgets.components.widgets.tab_view import TabCloseButtonDisplayMode

from core.asset_manager import AssetManager
from core.settings_manager import SettingsManager
from core.translator import Translator  # 導入您的 Translator
from core.utils import wrap_scroll



class GalleryTabs(QWidget):
    """
        優化後的 GalleryTabs 類別。
        - 使用 QTimer 延遲更新，避免高頻率觸發信號。
        - 比較設定差異，只在設定實際變更時發出信號。
        - 發出的信號只包含已變更的設定，以供 view_gallery 進行策略性更新。
        """
    settingsChanged = pyqtSignal(dict)  # 信號現在會攜帶一個包含變更的字典

    # 接收 translator
    def __init__(self, asset_manager: AssetManager, translator: Translator, parent=None):
        super().__init__(parent)
        self.settings_manager = SettingsManager()
        self.translator = translator
        self.tr = self.translator.get
        self.asset_manager = asset_manager

        # --- 新增：用於優化的屬性 ---
        self.cached_settings = {}  # 用於快取上一次的設定
        self.update_timer = QTimer(self)  # 用於延遲更新的計時器

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.tabBar = TabBar(self)
        self.tabBar.setAddButtonVisible(False)
        self.stackedWidget = QStackedWidget(self)

        main_layout.addWidget(self.tabBar)
        main_layout.addWidget(self.stackedWidget)

        # 加上滾動區塊
        self.watermarkScrollArea, self.watermarkInterface = wrap_scroll(uic.loadUi("ui/components/watermark_tab.ui"))
        self.frameScrollArea, self.frameInterface = wrap_scroll(uic.loadUi("ui/components/frame_tab.ui"))

        # 使用 translator 更新 Tab 標題
        self.addSubInterface(self.watermarkScrollArea, 'watermarkInterface',
                             self.tr('watermark_tab', 'Watermark'))
        self.addSubInterface(self.frameScrollArea, 'frameInterface', self.tr('frame_tab', 'Frame'))

        self.stackedWidget.currentChanged.connect(self.onCurrentIndexChanged)

        # 執行初始化
        self.init_all_ui()
        self._load_settings()
        self._connect_signals()

        # --- 新增：設定計時器 ---
        self.update_timer.setSingleShot(True)
        self.update_timer.setInterval(150)  # 150毫秒的延遲
        self.update_timer.timeout.connect(self._emit_changes)

        # 首次載入後，快取初始設定
        self.cached_settings = self._get_current_settings()


    def addSubInterface(self, widget: QWidget, objectName: str, text: str):
        widget.setObjectName(objectName)
        self.stackedWidget.addWidget(widget)
        tab_item = self.tabBar.addTab(
            routeKey=objectName, text=text, onClick=lambda: self.stackedWidget.setCurrentWidget(widget)
        )
        tab_item.setCloseButtonDisplayMode(TabCloseButtonDisplayMode.NEVER)
        tab_item.setMaximumWidth(120)

    def init_all_ui(self):
        self._translate_ui_text()  # 新增：翻譯所有靜態文字
        self._populate_all_options()
        self._init_color_pick_btn()

    def onCurrentIndexChanged(self, index):
        widget = self.stackedWidget.widget(index)
        self.tabBar.setCurrentTab(widget.objectName())

    def _translate_ui_text(self):
        """ 翻譯所有從 .ui 檔案載入的靜態 UI 元件文字 """
        # --- 浮水印 Tab ---
        w = self.watermarkInterface
        w.title_label_1.setText(self.tr("logo_settings_title", "Logo Settings"))
        # logo開關
        w.logo_enabled_switch.setOnText(self.tr("show_logo", "Show Logo"))
        w.logo_enabled_switch.setOffText(self.tr("hide_logo", "Hide Logo"))
        w.logo_size_label.setText(self.tr("logo_size", "Logo Size"))
        w.title_label_2.setText(self.tr("watermark_text_settings_title", "Watermark Text Settings"))
        # 文字開關
        w.text_enabled_switch.setOnText(self.tr("show_text", "Show Text"))
        w.text_enabled_switch.setOffText(self.tr("hide_text", "Hide Text"))
        w.text_custom_input.setPlaceholderText(self.tr("custom_text_placeholder", "Enter Custom Text"))
        w.exif_options_label.setText(self.tr("exif_options_title", "Parameters to show:"))
        w.exif_model_check.setText(self.tr("exif_model", "Model"))
        w.exif_focal_length_check.setText(self.tr("exif_focal_length", "Focal Length"))
        w.exif_iso_check.setText(self.tr("exif_iso", "ISO"))
        w.exif_aperture_check.setText(self.tr("exif_aperture", "Aperture"))
        w.exif_shutter_check.setText(self.tr("exif_shutter", "Shutter"))
        w.title_label_3.setText(self.tr("common_style_title", "Common Styles"))
        w.font_size_label.setText(self.tr("font_size", "Font Size"))
        w.title_label_4.setText(self.tr("layout_title", "Overall Layout"))

        # 相框
        f = self.frameInterface
        # 啟用相框開關
        f.frame_enabled_switch.setOnText(self.tr("enable_frame", "Enable Frame"))
        f.frame_enabled_switch.setOffText(self.tr("disable_frame", "Disable Frame"))
        f.photo_shadow_switch.setOnText(self.tr("enable_photo_shadow", "Enable Photo Shadow"))
        f.photo_shadow_switch.setOffText(self.tr("disable_enable_photo_shadow", "Disable Photo Shadow"))
        f.frame_radius_label.setText(self.tr("frame_radius", "Frame Radius"))
        f.photo_radius_label.setText(self.tr("photo_radius", "Photo Radius"))
        f.padding_top_label.setText(self.tr("padding_top", "Top Padding"))
        f.padding_sides_label.setText(self.tr("padding_sides", "Sides Padding"))
        f.padding_bottom_label.setText(self.tr("padding_bottom", "Bottom Padding"))
        f.frame_style_label.setText(self.tr("frame_style", "Frame Style"))
        f.frame_blur_label.setText(self.tr("frame_blur", "Frame Blur"))
        f.frame_color_label.setText(self.tr("frame_color", "Frame Color"))

    def _populate_combo(self, combo, place_holder_text: str, key_prefix: str, options: list):
        # TODO 有一些字體或logo文件名過長
        """ 使用 key-value 填充 ComboBox """
        combo.setPlaceholderText(place_holder_text)
        if len(options) < 1:
            # 如果是空的就還是加上這樣的提示
            display_text = self.tr("empty", "Empty")
            combo.addItem(f"--- {display_text} ---")
            combo.setEnabled(False)
            return
        for option_key in options:
            display_text = self.tr(f"{key_prefix}_{option_key}", option_key.replace("_", " ").title())
            combo.addItem(display_text, userData=option_key)

    def _populate_all_options(self):
        """ 初始化 ComboBox 的選項 """
        # TODO 注意當選擇浮水印在相框上時，怎麼處理，
        #  TODO 顯示LOGO且顯示文字才能有 layout_combo 顯示
        w = self.watermarkInterface
        f = self.frameInterface
        # 1. 獲取字體選項並填充
        user_fonts, system_fonts = self.asset_manager.get_font_options()
        self._populate_combo(w.font_my_custom_combo, self.tr('select_font', 'Select Font'), "font", user_fonts)
        self._populate_combo(w.font_system_combo, self.tr('select_font', 'Select Font'), "font", system_fonts)

        # 2. 獲取 Logo 選項並填充
        user_logos, app_logos = self.asset_manager.get_logo_options()
        self._populate_combo(w.logo_source_my_custom_combo, self.tr('select_logo', 'Select Logo'), "logo", user_logos)
        self._populate_combo(w.logo_source_app_combo, self.tr('select_logo', 'Select Logo'), "logo", app_logos)

        self._populate_combo(w.logo_source_combo, self.tr('logo_source_method', 'Logo Source Method'), "w_logo_source", ["auto_detect","select_from_library", "my_custom_logo"])
        self._populate_combo(w.text_source_combo, self.tr('text_source_method', 'Text Source Method'), "w_text_source", ["exif", "custom"])
        self._populate_combo(w.font_combo, self.tr('select_font_method', 'Select Font Method'), "w_font_source", ["system", "my_custom"])
        self._populate_combo(w.layout_combo, self.tr('layout_watermark', 'Watermark Layout'), "w_layout",
                             ["logo_top", "logo_bottom", "logo_left"])
        self._populate_combo(w.position_area_combo, self.tr('position_area_title', 'Watermark Area'), "w_area", ["in_frame", "in_photo"])
        self._populate_combo(w.position_align_combo, self.tr('position_align_title', 'Alignment'), "w_align",
                             ["top_left", "top_center", "top_right", "bottom_left", "bottom_center", "bottom_right"])
        self._populate_combo(f.frame_style_combo, self.tr('frame_style', 'Frame Style'), "f_style", ["solid_color", "blur_extend"])



    def _init_color_pick_btn(self):
        """初始化 自定義的顏色選取按鈕"""
        w = self.watermarkInterface
        f = self.frameInterface
        # 子組件 顏色組件實現國際化
        w.font_color_button.set_translator(self.translator)
        f.frame_color_button.set_translator(self.translator)

    def _connect_signals(self):
        w = self.watermarkInterface
        f = self.frameInterface
        """連接所有 UI 控制項的信號到 _on_settings_changed 槽函數"""
        controls = {
            # 浮水印 Tab
            w.logo_enabled_switch: 'checkedChanged',
            w.logo_source_combo: 'currentIndexChanged',
            w.logo_source_app_combo: 'currentIndexChanged',
            w.logo_source_my_custom_combo: 'currentIndexChanged',
            w.logo_size_slider: 'valueChanged',
            w.text_enabled_switch: 'checkedChanged',
            w.text_source_combo: 'currentIndexChanged',
            w.text_custom_input: 'textChanged',
            w.exif_model_check: 'stateChanged',
            w.exif_focal_length_check: 'stateChanged',
            w.exif_iso_check: 'stateChanged',
            w.exif_aperture_check: 'stateChanged',
            w.exif_shutter_check: 'stateChanged',
            w.font_combo: 'currentIndexChanged',
            w.font_system_combo: 'currentIndexChanged',
            w.font_my_custom_combo: 'currentIndexChanged',
            w.font_color_button: 'colorChanged',
            w.font_size_slider: 'valueChanged',
            w.layout_combo: 'currentIndexChanged',
            w.position_area_combo: 'currentIndexChanged',
            w.position_align_combo: 'currentIndexChanged',

            # 相框 Tab
            f.frame_enabled_switch: 'checkedChanged',
            f.photo_shadow_switch: 'checkedChanged',
            f.frame_radius_slider: 'valueChanged',
            f.photo_radius_slider: 'valueChanged',
            f.padding_top_slider: 'valueChanged',
            f.padding_sides_slider: 'valueChanged',
            f.padding_bottom_slider: 'valueChanged',
            f.frame_style_combo: 'currentIndexChanged',
            f.frame_blur_slider: 'valueChanged',
            f.frame_color_button: 'colorChanged',
        }

        for control, signal_name in controls.items():
            # 所有控制項的信號都只觸發計時器，而不是直接處理
            getattr(control, signal_name).connect(self._request_update)

    def _request_update(self):
        """當任何設定改變時，這個槽函數會被呼叫，它的唯一作用是啟動或重置計時器。"""
        self.update_timer.start()

    def _emit_changes(self):
        """計時器超時後，此函數被呼叫。它會比較設定並發出包含差異的信號。"""
        current_settings = self._get_current_settings()

        # 使用 JSON 序列化來進行深層比較，簡單有效
        if json.dumps(self.cached_settings) == json.dumps(current_settings):
            return  # 如果設定沒有實際變化，則不執行任何操作

        # 計算差異
        changes = self._compare_settings(self.cached_settings, current_settings)

        if changes:
            self.cached_settings = current_settings  # 更新快取
            self.settings_manager.set("gallery_settings", current_settings)  # 儲存完整設定
            self.settingsChanged.emit(changes)  # 發出包含差異的信號

    def _compare_settings(self, old_settings: dict, new_settings: dict) -> dict:
        """
        遞迴比較兩個字典，返回一個只包含已變更鍵值對的新字典。
        """
        changes = {}
        all_keys = old_settings.keys() | new_settings.keys()

        for key in all_keys:
            old_val = old_settings.get(key)
            new_val = new_settings.get(key)

            if isinstance(new_val, dict) and isinstance(old_val, dict):
                sub_changes = self._compare_settings(old_val, new_val)
                if sub_changes:
                    changes[key] = sub_changes
            elif old_val != new_val:
                changes[key] = new_val
        return changes

    def _get_current_settings(self) -> dict:
        """收集所有 UI 控制項的當前值並返回一個字典"""
        w = self.watermarkInterface
        f = self.frameInterface

        settings = {
            "watermark": {
                "logo_enabled": w.logo_enabled_switch.isChecked(),
                "logo_source": w.logo_source_combo.currentData(),
                "logo_source_app": w.logo_source_app_combo.currentData(),
                "logo_source_my_custom": w.logo_source_my_custom_combo.currentData(),
                "logo_size": w.logo_size_slider.value(),
                "text_enabled": w.text_enabled_switch.isChecked(),
                "text_source": w.text_source_combo.currentData(),
                "text_custom": w.text_custom_input.text(),
                "exif_options": {
                    "model": w.exif_model_check.isChecked(),
                    "focal_length": w.exif_focal_length_check.isChecked(),
                    "iso": w.exif_iso_check.isChecked(),
                    "aperture": w.exif_aperture_check.isChecked(),
                    "shutter": w.exif_shutter_check.isChecked(),
                },
                "font_family": w.font_combo.currentData(),
                "font_system": w.font_system_combo.currentData(),
                "font_my_custom": w.font_my_custom_combo.currentData(),
                "font_color": w.font_color_button.color(),
                "font_size": w.font_size_slider.value(),
                "layout": w.layout_combo.currentData(),
                "area": w.position_area_combo.currentData(),
                "align": w.position_align_combo.currentData(),
            },
            "frame": {
                "enabled": f.frame_enabled_switch.isChecked(),
                "photo_shadow": f.photo_shadow_switch.isChecked(),
                "frame_radius": f.frame_radius_slider.value(),
                "photo_radius": f.photo_radius_slider.value(),
                "padding_top": f.padding_top_slider.value(),
                "padding_sides": f.padding_sides_slider.value(),
                "padding_bottom": f.padding_bottom_slider.value(),
                "style": f.frame_style_combo.currentData(),
                "blur_radius": f.frame_blur_slider.value(),
                "color": f.frame_color_button.color(),
            }
        }
        return settings

    # def _on_settings_changed(self):
    #     """ 當設定改變時，儲存設定並發出信號 """
    #     settings = self._get_current_settings()
    #     self.settings_manager.set("gallery_settings", settings)
    #     self.settingsChanged.emit()

    def _load_settings(self):
        """從設定檔載入設定並更新 UI"""
        settings = self.settings_manager.get("gallery_settings")
        w_settings = settings.get("watermark", {})
        f_settings = settings.get("frame", {})
        w = self.watermarkInterface
        f = self.frameInterface

        # --- 載入浮水印設定 ---
        w.logo_enabled_switch.setChecked(w_settings.get('logo_enabled', False))
        logo_source = w.logo_source_combo.findData(w_settings.get('logo_source', 'w_logo_source_auto_detect'))
        w.logo_source_combo.setCurrentIndex(logo_source if logo_source > -1 else 0)

        logo_source_app = w.logo_source_app_combo.findData(w_settings.get('logo_source_app', ''))
        w.logo_source_app_combo.setCurrentIndex(logo_source_app if logo_source_app > -1 else -1)
        logo_source_my_custom = w.logo_source_my_custom_combo.findData(w_settings.get('logo_source_my_custom', ''))
        w.logo_source_app_combo.setCurrentIndex(logo_source_my_custom if logo_source_my_custom > -1 else -1)

        w.logo_size_slider.setValue(w_settings.get('logo_size', 30))
        w.text_enabled_switch.setChecked(w_settings.get('text_enabled', True))

        text_source = w.text_source_combo.findData(w_settings.get('text_source', 'exif'))
        w.text_source_combo.setCurrentIndex(text_source if text_source > -1 else 0)

        w.text_custom_input.setText(w_settings.get('text_custom', ''))
        # exif
        exif = w_settings.get('exif_options', {})
        w.exif_model_check.setChecked(exif.get('model', True))
        w.exif_focal_length_check.setChecked(exif.get('focal_length', True))
        w.exif_iso_check.setChecked(exif.get('iso', True))
        w.exif_aperture_check.setChecked(exif.get('aperture', True))
        w.exif_shutter_check.setChecked(exif.get('shutter', True))
        # 載入字體
        font_family = w.font_combo.findData(w_settings.get('font_family', ''))
        w.font_combo.setCurrentIndex(font_family if font_family > -1 else 0)

        font_system = w.font_system_combo.findData(w_settings.get('font_system', ''))
        w.font_system_combo.setCurrentIndex(font_system if font_system > -1 else -1)

        font_my_custom = w.font_my_custom_combo.findData(w_settings.get('font_my_custom', ''))
        w.font_my_custom_combo.setCurrentIndex(font_my_custom if font_my_custom > -1 else -1)

        w.font_color_button.setColor(w_settings.get('font_color', '#FFFFFFFF'))
        w.font_size_slider.setValue(w_settings.get('font_size', 20))
        w.layout_combo.setCurrentIndex(w.layout_combo.findData(w_settings.get('layout', 'logo_top_text_bottom')))
        w.position_area_combo.setCurrentIndex(w.position_area_combo.findData(w_settings.get('area', 'in_frame')))
        w.position_align_combo.setCurrentIndex(w.position_align_combo.findData(w_settings.get('align', 'bottom_right')))

        # --- 載入相框設定 ---
        f.frame_enabled_switch.setChecked(f_settings.get('enabled', True))
        f.photo_shadow_switch.setChecked(f_settings.get('photo_shadow', True))
        f.frame_radius_slider.setValue(f_settings.get('frame_radius', 5))
        f.photo_radius_slider.setValue(f_settings.get('photo_radius', 3))
        f.padding_top_slider.setValue(f_settings.get('padding_top', 10))
        f.padding_sides_slider.setValue(f_settings.get('padding_sides', 10))
        f.padding_bottom_slider.setValue(f_settings.get('padding_bottom', 10))

        frame_style = f.frame_style_combo.findData(f_settings.get('style', 'solid_color'))
        f.frame_style_combo.setCurrentIndex(frame_style if frame_style > -1 else 0)

        f.frame_blur_slider.setValue(f_settings.get('blur_radius', 20))
        f.frame_color_button.setColor(f_settings.get('color', '#FFFFFFFF'))

        # 更新快取
        self.cached_settings = self._get_current_settings()


