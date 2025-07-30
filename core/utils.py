from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import SingleDirectionScrollArea

def load_svg_as_pixmap(path: str, size: QSize) -> QPixmap:
    """將 SVG 檔案以指定大小載入為高品質 QPixmap"""
    renderer = QSvgRenderer(path)
    pixmap = QPixmap(size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


def valid_setting_str(setting: any) -> bool:
    if isinstance(setting, str) and len(setting) > 0:
        return True
    return False


def wrap_scroll(widget: QWidget) -> tuple[SingleDirectionScrollArea, QWidget]:
    """
    在組件上包上一層滾動區塊，讓像是垂直的布局能夠滾動
    Args:
        widget: 被包住的組件

    Returns: tuple[SingleDirectionScrollArea, QWidget]

    """
    scroll = SingleDirectionScrollArea()
    scroll.setWidgetResizable(True)
    scroll.enableTransparentBackground()
    scroll.setStyleSheet("QScrollArea{background: transparent; border: none}")
    # 必须给内部的视图也加上透明背景样式
    widget.setStyleSheet("QWidget{background: transparent}")
    scroll.setWidget(widget)
    return scroll, widget