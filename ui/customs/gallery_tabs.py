from PyQt6 import uic
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QStackedWidget, QLabel, QVBoxLayout
from qfluentwidgets import TabBar

from core.settings_manager import SettingsManager


class GalleryTabs(QWidget):
    settingsChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_manager = SettingsManager()

        # 1. 建立一個垂直主佈局，並將其應用於 GalleryTabs (self)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)  # 設置邊距為0，使其填滿
        main_layout.setSpacing(0)  # 設置元件間距為0

        self.tabBar = TabBar(self)
        self.stackedWidget = QStackedWidget(self)
        self.counter = 1

        main_layout.addWidget(self.tabBar)
        main_layout.addWidget(self.stackedWidget)

        self.watermarkInterface = uic.loadUi("ui/components/watermark_tab.ui")
        self.frameInterface = uic.loadUi("ui/components/frame_tab.ui")

        # 添加標籤頁
        self.addSubInterface(self.watermarkInterface, 'watermarkInterface', '浮水印')
        self.addSubInterface(self.frameInterface, 'frameInterface', '相框')

        # 连接信号
        self.stackedWidget.currentChanged.connect(self.onCurrentIndexChanged)

        self._connect_signals()
        self.init_Text()

    def init_Text(self):
        """
        初始化一些控鍵的國際化文字
        :return:
        """
        self.frameInterface.frame_enabled_checkbox.setOffText("关闭")
        self.frameInterface.frame_enabled_checkbox.setOnText("开启")

        items = ['shoko', '西宫硝子', '宝多六花', '小鸟游六花']
        self.frameInterface.frame_style_comboBox.addItems(items)

    def addSubInterface(self, widget: QLabel, objectName: str, text: str):
        widget.setObjectName(objectName)
        # widget.setAlignment(Qt.Orientation.AlignCenter)
        self.stackedWidget.addWidget(widget)

        # 使用全局唯一的 objectName 作为路由键
        self.tabBar.addTab(
            routeKey=objectName,
            text=text,
            onClick=lambda: self.stackedWidget.setCurrentWidget(widget)
        )

    def onCurrentIndexChanged(self, index):
        widget = self.stackedWidget.widget(index)
        self.tabBar.setCurrentTab(widget.objectName())

    def onAddNewTab(self):
        w = QLabel(f"Tab {self.counter}")
        self.addSubInterface(w, w.text(), w.text())
        self.counter += 1

    def onCloseTab(self, index: int):
        item = self.tabBar.tabItem(index)
        widget = self.findChild(QLabel, item.routeKey())
        self.stackedWidget.removeWidget(widget)
        self.tabBar.removeTab(index)
        widget.deleteLater()

    def _connect_signals(self):
        # 連接右側控制項
        self.watermarkInterface.watermark_enabled_checkbox.stateChanged.connect(self._on_settings_changed)
        self.watermarkInterface.watermark_text_input.textChanged.connect(self._on_settings_changed)
        self.frameInterface.frame_enabled_checkbox.checkedChanged.connect(self._on_settings_changed)
        self.frameInterface.frame_width_slider.valueChanged.connect(self._on_settings_changed)

    def _get_current_settings(self) -> dict:
        # 測試
        # print(f"frame_width_slider {self.frame_width_slider.value()}, type: {type(self.frame_width_slider.value())}")
        return {
            'watermark_enabled': self.watermarkInterface.watermark_enabled_checkbox.isChecked(),
            'watermark_text': self.watermarkInterface.watermark_text_input.text(),
            'frame_enabled': self.frameInterface.frame_enabled_checkbox.isChecked(),
            'frame_width': self.frameInterface.frame_width_slider.value(),
        }

    def _on_settings_changed(self):
        settings = self._get_current_settings()
        self.settings_manager.set("gallery_settings", settings)
        self.settingsChanged.emit()

    def _load_settings(self):
        settings = self.settings_manager.get("gallery_settings", {})
        self.watermarkInterface.watermark_enabled_checkbox.setChecked(settings.get('watermark_enabled', False))
        self.watermarkInterface.watermark_text_input.setText(settings.get('watermark_text', ''))
        self.frameInterface.frame_enabled_checkbox.setChecked(settings.get('frame_enabled', False))
        self.frameInterface.frame_width_slider.setValue(settings.get('frame_width', 10))
