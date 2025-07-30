from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QWidget, QHBoxLayout
from qfluentwidgets import CheckBox, BodyLabel

from core.translator import Translator


class FontItemWidget(QWidget):
    # TODO 如果文件名過長 需要考慮
    """用於顯示在字體列表中的自訂項目"""
    selection_changed = pyqtSignal(bool)

    def __init__(self, family: str, path: str | None, translator: Translator, parent=None):
        super().__init__(parent)
        self.translator = translator
        self.tr = self.translator.get

        self.path = path  # path is None for system fonts
        self.family = family
        self.is_deletable = path is not None

        self.checkbox = CheckBox(self)
        self.checkbox.setEnabled(self.is_deletable)  # 系統字體不給勾選

        display_text = family
        if self.is_deletable:
            display_text += f" ( {self.tr("user_upload", "User Upload")} ) "

        self.font_label = BodyLabel(display_text, self)
        self.font_label.setFont(QFont(family, 12))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        # 直接隱藏
        if not self.is_deletable:
            self.checkbox.setVisible(False)
        layout.addWidget(self.checkbox)
        layout.addWidget(self.font_label, 1)

        self.checkbox.stateChanged.connect(
            lambda state: self.selection_changed.emit(state == Qt.CheckState.Checked.value)
        )

    def is_checked(self) -> bool:
        return self.checkbox.isChecked()

    def set_checked(self, is_checked: bool):
        if not self.is_deletable:
            return
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(is_checked)
        self.checkbox.blockSignals(False)
