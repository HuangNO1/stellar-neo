from PyQt6.QtCore import pyqtSignal
from qfluentwidgets import MessageBoxBase, SubtitleLabel, ProgressBar, BodyLabel
from core.translator import Translator

class ExportMessageBox(MessageBoxBase):
    cancelExport = pyqtSignal()
    exportError = pyqtSignal()

    def __init__(self, translator: Translator, parent=None, current: int = 0, total: int = 100):
        super().__init__(parent)
        self.tr = translator.get
        self.current = current
        self.total = total
        self.titleLabel = SubtitleLabel()
        self.titleLabel.setText(self.tr("exporting", "Exporting"))
        self.progressLabel = BodyLabel()
        self.progressLabel.setText(f'{current} / {total}')
        # 设置取值范围
        self.progressBar = ProgressBar()
        self.progressBar.setRange(current, total)

        # 设置当前值
        self.progressBar.setValue(current)

        # 将组件添加到布局中
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.progressLabel)
        self.viewLayout.addWidget(self.progressBar)

        # 设置对话框的最小宽度
        self.widget.setMinimumWidth(400)
        # 隱藏確認按鈕
        self.yesButton.hide()
        self.buttonLayout.insertStretch(0, 1)
        # 取消按鈕
        self.cancelButton.setText(self.tr('cancel', 'Cancel'))
        self.cancelButton.clicked.connect(self._on_cancel_export)

    def setCurrentProgress(self, current):
        self.current = current
        self.progressBar.setValue(current)
        self.progressLabel.setText(f'{current} / {self.total}')

    def setExportError(self, error):
        self.progressBar.error()
        self.titleLabel.setText(f'{self.tr('export_error', 'Export Error')}: {error}')
        self.exportError.emit()

    def _on_cancel_export(self):
        self.progressBar.pause()
        self.titleLabel.setText(self.tr('cancel_export', 'Cancel Export'))
        self.cancelExport.emit()




