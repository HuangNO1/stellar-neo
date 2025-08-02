from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QPainter, QImage
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import SingleDirectionScrollArea

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
    # 必須給內部的視圖也加上透明背景樣式
    widget.setStyleSheet("QWidget{background: transparent}")
    scroll.setWidget(widget)
    return scroll, widget