import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout
from qfluentwidgets import CheckBox, ToolButton, FluentIcon, IconWidget

from core.translator import Translator
from ui.customs.ElidedLabel import ElidedLabel
from ui.customs.custom_icon import MyFluentIcon


class GalleryItemWidget(QWidget):
    delete_requested = pyqtSignal(str)
    selection_changed = pyqtSignal(bool)

    # 接收 translator 作為參數
    def __init__(self, path: str, has_exif: bool, translator: Translator, parent=None):
        super().__init__(parent)
        self.path = path
        self.translator = translator
        self.tr = self.translator.get

        self.checkbox = CheckBox(self)
        self.filename_label = ElidedLabel(os.path.basename(path), self)
        self.filename_label.setMinimumWidth(100)
        self.warning_icon_widget = IconWidget(MyFluentIcon.WARNING, parent=self)
        self.warning_icon_widget.setFixedSize(16, 16)

        if not has_exif:
            tooltip_text = self.tr("exif_warning_tooltip", "Cannot read EXIF")
            self.warning_icon_widget.setToolTip(tooltip_text)
            self.warning_icon_widget.setVisible(True)
        else:
            self.warning_icon_widget.setVisible(False)

        self.delete_button = ToolButton(self)
        self.delete_button.setIcon(FluentIcon.DELETE)
        self.delete_button.setFixedSize(28, 28)
        # 使用 translator 更新 ToolTip
        delete_tooltip = self.tr("delete_image_tooltip", "Delete this image")
        self.delete_button.setToolTip(delete_tooltip)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        layout.addWidget(self.checkbox)
        layout.addWidget(self.filename_label, 1)
        layout.addWidget(self.warning_icon_widget)
        layout.addWidget(self.delete_button)

        self.delete_button.clicked.connect(self._on_delete_clicked)
        self.checkbox.stateChanged.connect(self._on_checkbox_changed)

    def _on_delete_clicked(self):
        self.delete_requested.emit(self.path)

    def _on_checkbox_changed(self, state):
        self.selection_changed.emit(state == Qt.CheckState.Checked.value)

    def set_checked(self, is_checked: bool):
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(is_checked)
        self.checkbox.blockSignals(False)

    def is_checked(self) -> bool:
        return self.checkbox.isChecked()
