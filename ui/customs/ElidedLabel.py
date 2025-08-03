# In: ui/customs/elided_label.py (建議路徑)

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics
from qfluentwidgets import BodyLabel


class ElidedLabel(BodyLabel):
    """
    一個自訂的 QLabel，當文字過長時會自動在右側顯示省略號 (...)，
    並且在滑鼠懸浮時透過 ToolTip 顯示完整的文字。
    """

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self._full_text = text
        # 初始就設定 ToolTip，確保任何情況下都能看到完整文字
        self.setToolTip(self._full_text)

    def setText(self, text: str):
        """重寫 setText 以更新完整文字。"""
        self._full_text = text
        self.setToolTip(self._full_text)
        # 立即更新一次顯示的文字
        self._update_elided_text()
        super().setText(self.text())  # 更新 QLabel 內部文字

    def resizeEvent(self, event):
        """在 Widget 大小改變時觸發，重新計算並設定省略後的文字。"""
        super().resizeEvent(event)
        self._update_elided_text()

    def _update_elided_text(self):
        """根據目前的寬度計算並設定省略文字。"""
        fm = QFontMetrics(self.font())
        # 使用 elidedText 進行文字截斷，ElideRight 表示在右側加入...
        elided_text = fm.elidedText(self._full_text, Qt.TextElideMode.ElideRight, self.width())
        # 使用 setText() 方法來更新標籤的顯示文字，避免遞迴呼叫
        super().setText(elided_text)