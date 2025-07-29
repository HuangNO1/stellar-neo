from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer


def load_svg_as_pixmap(path: str, size: QSize) -> QPixmap:
    """將 SVG 檔案以指定大小載入為高品質 QPixmap"""
    renderer = QSvgRenderer(path)
    pixmap = QPixmap(size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap
