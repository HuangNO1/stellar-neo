import os

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from qfluentwidgets import CheckBox

from ui.customs.ElidedLabel import ElidedLabel


# --- 新增：自訂 Logo 項目元件 ---
class LogoItemWidget(QWidget):
    """用於顯示在 Logo 列表中的自訂項目"""
    selection_changed = pyqtSignal(bool)

    def __init__(self, path: str, icon: QIcon, parent=None):
        super().__init__(parent)
        self.path = path

        self.checkbox = CheckBox(self)
        self.icon_label = QLabel(self)
        self.icon_label.setPixmap(icon.pixmap(QSize(32, 32)))
        self.filename_label = ElidedLabel(os.path.basename(path), self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        layout.addWidget(self.checkbox)
        layout.addWidget(self.icon_label)
        layout.addWidget(self.filename_label, 1)

        self.checkbox.stateChanged.connect(
            lambda state: self.selection_changed.emit(state == Qt.CheckState.Checked.value)
        )

    def is_checked(self) -> bool:
        return self.checkbox.isChecked()

    def set_checked(self, is_checked: bool):
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(is_checked)
        self.checkbox.blockSignals(False)
