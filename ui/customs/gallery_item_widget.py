import os

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QCheckBox, QGraphicsColorizeEffect
from qfluentwidgets import PushButton, FluentIcon, ToolButton, BodyLabel, IconWidget, CheckBox
from core.utils import load_svg_as_pixmap


class GalleryItemWidget(QWidget):
    """
    用於圖片列表的自訂列表項元件。
    包含：勾選框、檔名、警告圖示、刪除按鈕。
    """
    # 定義信號，用於通知外部 (GalleryView)
    delete_requested = pyqtSignal(str)  # 請求刪除此項目，傳遞其路徑
    selection_changed = pyqtSignal(bool)  # 勾選狀態改變時發出信號

    def __init__(self, path: str, has_exif: bool, parent=None):
        super().__init__(parent)
        self.path = path

        # --- 建立元件 ---
        self.checkbox = CheckBox(self)

        self.filename_label = BodyLabel(os.path.basename(path), self)
        self.filename_label.setMinimumWidth(100)  # 給檔名一個最小寬度

        self.warning_icon_label = QLabel(self)
        self.warning_icon_label.setFixedSize(16, 16)  # 設定固定大小

        # 預設隱藏警告圖示。這是確保無 EXIF 時才顯示的第一步。
        self.warning_icon_label.setVisible(False)

        # 根據是否有 EXIF 資訊來設定警告圖示和提示
        # 這個 if 區塊是唯一會讓警告圖示變得可見的地方。
        if not has_exif:
            # 從本地檔案載入圖示
            # warning_pixmap = QPixmap()
            icon_size = QSize(16, 16)
            warning_pixmap = load_svg_as_pixmap("assets/icons/base/warning.svg", icon_size)

            if not warning_pixmap.isNull():
                # 直接設置圖片，不再進行任何著色處理
                self.warning_icon_label.setPixmap(warning_pixmap)

            # 使用 Qt 原生的 setToolTip
            self.warning_icon_label.setToolTip("無法讀取 EXIF 裝置資訊")
            # 只有在這個條件下，才將圖示設為可見
            self.warning_icon_label.setVisible(True)
        # 建立刪除按鈕
        self.delete_button = ToolButton(self)
        self.delete_button.setIcon(FluentIcon.DELETE)
        self.delete_button.setFixedSize(28, 28)
        self.delete_button.setToolTip("刪除此圖片")

        # --- 設定佈局 ---
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        layout.addWidget(self.checkbox)
        layout.addWidget(self.filename_label, 1)  # 設置 stretch 為 1，使其能自動擴展
        layout.addWidget(self.warning_icon_label)
        layout.addWidget(self.delete_button)

        # --- 連接內部信號 ---
        self.delete_button.clicked.connect(self._on_delete_clicked)
        self.checkbox.stateChanged.connect(self._on_checkbox_changed)

    def _on_delete_clicked(self):
        """當刪除按鈕被點擊時，發射請求刪除的信號。"""
        self.delete_requested.emit(self.path)

    def _on_checkbox_changed(self, state):
        """當勾選框狀態改變時，發射狀態改變的信號。"""
        self.selection_changed.emit(state == Qt.CheckState.Checked.value)

    def set_checked(self, is_checked: bool):
        """提供一個外部方法來設定勾選狀態，同時避免觸發信號循環。"""
        self.checkbox.blockSignals(True)  # 暫時阻斷信號
        self.checkbox.setChecked(is_checked)
        self.checkbox.blockSignals(False)  # 恢復信號

    def is_checked(self) -> bool:
        """提供一個外部方法來獲取勾選狀態。"""
        return self.checkbox.isChecked()

