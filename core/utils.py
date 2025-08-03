import os
import sys

from PyQt6.QtWidgets import QWidget
from qfluentwidgets import SingleDirectionScrollArea

def resource_path(relative_path):
    """ 取得資源檔案的絕對路徑 (打包前後皆可使用) """
    try:
        # PyInstaller 建立的暫存資料夾，並將路徑存在 _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # 在開發模式下，使用正常的相對路徑
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


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
