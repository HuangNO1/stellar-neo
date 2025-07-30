from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QStackedWidget, QVBoxLayout
from qfluentwidgets import TabBar
from qfluentwidgets.components.widgets.tab_view import TabCloseButtonDisplayMode

from core.settings_manager import SettingsManager
from core.translator import Translator  # 導入您的 Translator


class GalleryTabs(QWidget):
    settingsChanged = pyqtSignal()

    # 定義設定值與翻譯鍵的精確對應關係
    COMBO_MAPS = {
        "logo_source": {"auto_detect": "logo_source_auto", "custom_text": "logo_source_text"},
        "text_source": {"exif": "text_source_exif", "custom": "text_source_custom"},
        "layout": {"logo_top_text_bottom": "layout_logo_top", "logo_bottom_text_top": "layout_logo_bottom",
                   "logo_left_text_right": "layout_logo_left"},
        "area": {"in_frame": "position_in_frame", "in_photo": "position_in_photo"},
        "align": {"top_left": "align_top_left", "top_center": "align_top_center", "top_right": "align_top_right",
                  "bottom_left": "align_bottom_left", "bottom_center": "align_bottom_center",
                  "bottom_right": "align_bottom_right"},
        "style": {"solid_color": "style_solid_color", "blur_extend": "style_blur_extend"}
    }

    # 接收 translator
    def __init__(self, translator: Translator, parent=None):
        super().__init__(parent)
        self.settings_manager = SettingsManager()
        self.translator = translator

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.tabBar = TabBar(self)
        self.tabBar.setAddButtonVisible(False)
        self.stackedWidget = QStackedWidget(self)

        main_layout.addWidget(self.tabBar)
        main_layout.addWidget(self.stackedWidget)

        self.watermarkInterface = uic.loadUi("ui/components/watermark_tab.ui")
        self.frameInterface = uic.loadUi("ui/components/frame_tab.ui")

        # 使用 translator 更新 Tab 標題
        self.addSubInterface(self.watermarkInterface, 'watermarkInterface',
                             self.translator.get('gallery_tab_watermark', 'Watermark'))
        self.addSubInterface(self.frameInterface, 'frameInterface', self.translator.get('gallery_tab_frame', 'Frame'))

        self.stackedWidget.currentChanged.connect(self.onCurrentIndexChanged)

        # 執行初始化
        self._translate_ui_text()  # 新增：翻譯所有靜態文字
        self._init_ui_options()
        self._load_settings()
        self._connect_signals()

    def addSubInterface(self, widget: QWidget, objectName: str, text: str):
        widget.setObjectName(objectName)
        self.stackedWidget.addWidget(widget)
        tab_item = self.tabBar.addTab(
            routeKey=objectName, text=text, onClick=lambda: self.stackedWidget.setCurrentWidget(widget)
        )
        tab_item.setCloseButtonDisplayMode(TabCloseButtonDisplayMode.NEVER)
        tab_item.setMaximumWidth(120)

    def onCurrentIndexChanged(self, index):
        widget = self.stackedWidget.widget(index)
        self.tabBar.setCurrentTab(widget.objectName())

    def _translate_ui_text(self):
        """ 翻譯所有從 .ui 檔案載入的靜態 UI 元件文字 """
        # --- 浮水印 Tab ---
        w = self.watermarkInterface
        w.title_label_1.setText(self.translator.get("logo_settings_title", "Logo Settings"))
        w.logo_enabled_switch.setText(self.translator.get("show_logo", "Show Logo"))
        w.logo_text_input.setPlaceholderText(self.translator.get("logo_text_placeholder", "Enter Logo Text"))
        w.logo_size_label.setText(self.translator.get("logo_size", "Logo Size"))
        w.title_label_2.setText(self.translator.get("watermark_text_settings_title", "Watermark Text Settings"))
        w.text_enabled_switch.setText(self.translator.get("show_text", "Show Text"))
        w.text_custom_input.setPlaceholderText(self.translator.get("custom_text_placeholder", "Enter Custom Text"))
        w.exif_options_label.setText(self.translator.get("exif_options_title", "Parameters to show:"))
        w.exif_model_check.setText(self.translator.get("exif_model", "Model"))
        w.exif_iso_check.setText(self.translator.get("exif_iso", "ISO"))
        w.exif_aperture_check.setText(self.translator.get("exif_aperture", "Aperture"))
        w.exif_shutter_check.setText(self.translator.get("exif_shutter", "Shutter"))
        w.title_label_3.setText(self.translator.get("common_style_title", "Common Styles"))
        w.font_size_label.setText(self.translator.get("font_size", "Font Size"))
        w.title_label_4.setText(self.translator.get("layout_title", "Overall Layout"))

        # 相框
        f = self.frameInterface
        f.frame_enabled_switch.setText(self.translator.get("enable_frame", "Enable Frame"))
        f.photo_shadow_switch.setText(self.translator.get("photo_shadow", "Photo Shadow"))
        f.frame_radius_label.setText(self.translator.get("frame_radius", "Frame Radius"))
        f.photo_radius_label.setText(self.translator.get("photo_radius", "Photo Radius"))
        f.padding_top_label.setText(self.translator.get("padding_top", "Top Padding"))
        f.padding_sides_label.setText(self.translator.get("padding_sides", "Sides Padding"))
        f.padding_bottom_label.setText(self.translator.get("padding_bottom", "Bottom Padding"))
        f.frame_style_label.setText(self.translator.get("frame_style", "Frame Style"))
        f.frame_blur_label.setText(self.translator.get("frame_blur", "Frame Blur"))
        f.frame_color_label.setText(self.translator.get("frame_color", "Frame Color"))

    def _populate_combo(self, combo, key_prefix: str, options: list):
        """ 使用 key-value 填充 ComboBox """
        for option_key in options:
            display_text = self.translator.get(f"{key_prefix}_{option_key}", option_key.replace("_", " ").title())
            combo.addItem(display_text, userData=option_key)

    def _init_ui_options(self):
        """ 初始化 ComboBox 的選項 """
        self._populate_combo(self.watermarkInterface.logo_source_combo, "w_logo_source", ["auto_detect", "custom_text"])
        self._populate_combo(self.watermarkInterface.text_source_combo, "w_text_source", ["exif", "custom"])
        self._populate_combo(self.watermarkInterface.layout_combo, "w_layout",
                             ["logo_top_text_bottom", "logo_bottom_text_top", "logo_left_text_right"])
        self._populate_combo(self.watermarkInterface.position_area_combo, "w_area", ["in_frame", "in_photo"])
        self._populate_combo(self.watermarkInterface.position_align_combo, "w_align",
                             ["top_left", "top_center", "top_right", "bottom_left", "bottom_center", "bottom_right"])
        self._populate_combo(self.frameInterface.frame_style_combo, "f_style", ["solid_color", "blur_extend"])

    # _connect_signals, _get_current_settings, _on_settings_changed, _load_settings
    # 這些函數的內部邏輯與上一版相似，主要是確保它們使用 userData 來讀寫設定鍵，這裡不再重複貼出以節省篇幅。
    # 唯一的修改是確保 _load_settings 使用 `combo.findData(key)` 來正確恢復選項。
    def _connect_signals(self):
        """連接所有 UI 控制項的信號到 _on_settings_changed 槽函數"""
        controls = {
            # 浮水印 Tab
            self.watermarkInterface.logo_enabled_switch: 'checkedChanged',
            self.watermarkInterface.logo_source_combo: 'currentIndexChanged',
            self.watermarkInterface.logo_text_input: 'textChanged',
            self.watermarkInterface.logo_size_slider: 'valueChanged',
            self.watermarkInterface.text_enabled_switch: 'checkedChanged',
            self.watermarkInterface.text_source_combo: 'currentIndexChanged',
            self.watermarkInterface.text_custom_input: 'textChanged',
            self.watermarkInterface.exif_model_check: 'stateChanged',
            self.watermarkInterface.exif_iso_check: 'stateChanged',
            self.watermarkInterface.exif_aperture_check: 'stateChanged',
            self.watermarkInterface.exif_shutter_check: 'stateChanged',
            self.watermarkInterface.font_combo: 'currentIndexChanged',
            self.watermarkInterface.font_color_button: 'colorChanged',
            self.watermarkInterface.font_size_slider: 'valueChanged',
            self.watermarkInterface.layout_combo: 'currentIndexChanged',
            self.watermarkInterface.position_area_combo: 'currentIndexChanged',
            self.watermarkInterface.position_align_combo: 'currentIndexChanged',

            # 相框 Tab
            self.frameInterface.frame_enabled_switch: 'checkedChanged',
            self.frameInterface.photo_shadow_switch: 'checkedChanged',
            self.frameInterface.frame_radius_slider: 'valueChanged',
            self.frameInterface.photo_radius_slider: 'valueChanged',
            self.frameInterface.padding_top_slider: 'valueChanged',
            self.frameInterface.padding_sides_slider: 'valueChanged',
            self.frameInterface.padding_bottom_slider: 'valueChanged',
            self.frameInterface.frame_style_combo: 'currentIndexChanged',
            self.frameInterface.frame_blur_slider: 'valueChanged',
            self.frameInterface.frame_color_button: 'colorChanged',
        }

        for control, signal_name in controls.items():
            getattr(control, signal_name).connect(self._on_settings_changed)

    def _get_current_settings(self) -> dict:
        """收集所有 UI 控制項的當前值並返回一個字典"""
        w = self.watermarkInterface
        f = self.frameInterface

        settings = {
            "watermark": {
                "logo_enabled": w.logo_enabled_switch.isChecked(),
                "logo_source": w.logo_source_combo.currentData(),
                "logo_text": w.logo_text_input.text(),
                "logo_size": w.logo_size_slider.value(),
                "text_enabled": w.text_enabled_switch.isChecked(),
                "text_source": w.text_source_combo.currentData(),
                "text_custom": w.text_custom_input.text(),
                "exif_options": {
                    "model": w.exif_model_check.isChecked(),
                    "iso": w.exif_iso_check.isChecked(),
                    "aperture": w.exif_aperture_check.isChecked(),
                    "shutter": w.exif_shutter_check.isChecked(),
                },
                "font_family": w.font_combo.currentText(),
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

    def _on_settings_changed(self):
        """ 當設定改變時，儲存設定並發出信號 """
        settings = self._get_current_settings()
        self.settings_manager.set("gallery_settings", settings)
        self.settingsChanged.emit()

    def _load_settings(self):
        """從設定檔載入設定並更新 UI"""
        settings = self.settings_manager.get("gallery_settings")
        w_settings = settings.get("watermark", {})
        f_settings = settings.get("frame", {})
        w = self.watermarkInterface
        f = self.frameInterface

        # --- 載入浮水印設定 ---
        w.logo_enabled_switch.setChecked(w_settings.get('logo_enabled', False))
        w.logo_source_combo.setCurrentIndex(w.logo_source_combo.findData(w_settings.get('logo_source', 'auto_detect')))
        w.logo_text_input.setText(w_settings.get('logo_text', ''))
        w.logo_size_slider.setValue(w_settings.get('logo_size', 30))
        w.text_enabled_switch.setChecked(w_settings.get('text_enabled', True))
        w.text_source_combo.setCurrentIndex(w.text_source_combo.findData(w_settings.get('text_source', 'exif')))
        w.text_custom_input.setText(w_settings.get('text_custom', ''))
        exif = w_settings.get('exif_options', {})
        w.exif_model_check.setChecked(exif.get('model', True))
        w.exif_iso_check.setChecked(exif.get('iso', True))
        w.exif_aperture_check.setChecked(exif.get('aperture', True))
        w.exif_shutter_check.setChecked(exif.get('shutter', True))
        # 載入字體
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
        f.frame_style_combo.setCurrentIndex(f.frame_style_combo.findData(f_settings.get('style', 'solid_color')))
        f.frame_blur_slider.setValue(f_settings.get('blur_radius', 20))
        f.frame_color_button.setColor(f_settings.get('color', '#FFFFFFFF'))
