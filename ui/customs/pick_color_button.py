# ColorButton.py
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor
from qfluentwidgets import ColorDialog, PushButton


class ColorButton(PushButton):
    colorChanged = pyqtSignal(str)

    def __init__(self, *args, color=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.colorDialog = None
        self._color = None
        self._default = color if color is not None else '#FFFFFF'
        self.setText('')
        self.clicked.connect(self.openColorPicker)
        self.setColor(self._default)

    def setColor(self, color: str):
        # 傳入的 color 是字串，例如 '#ffffff'
        if color != self._color:
            self._color = color
            # 建議：發射信號時，將新的顏色值傳出去
            self.colorChanged.emit(self._color)

        # 根據顏色設定樣式，如果顏色為 None 或空字串，則清除樣式
        if self._color:
            self.setStyleSheet(f"background-color: {self._color};")
        else:
            self.setStyleSheet("")

    def color(self):
        return self._color

    def openColorPicker(self):
        # 使用按鈕當前的顏色作為顏色選擇器的初始顏色
        initial_color = QColor(self._color) if self._color else QColor(255, 255, 255)

        # 建立顏色對話框
        self.colorDialog = ColorDialog(
            initial_color,
            "選擇顏色",
            self.window(),
            enableAlpha=False
        )

        # 關鍵修正：
        # 將 colorChanged 信號連接到一個 lambda 函數，
        # 這個函數會呼叫 self.setColor 來更新按鈕顏色。
        # QColor.name() 會返回 '#rrggb' 格式的字串。
        self.colorDialog.colorChanged.connect(lambda c: self.setColor(c.name()))

        # 執行對話框
        self.colorDialog.exec()
