from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QPainter, QImage
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import SingleDirectionScrollArea

def load_svg_as_pixmap(path: str, size: QSize) -> QPixmap:
    """高分辨率渲染 SVG，再縮小為指定大小的高品質 QPixmap"""
    renderer = QSvgRenderer(path)

    # 放大倍率（越高越清晰，但也越耗效能）
    scale_factor = 10
    upscale_size = QSize(size.width() * scale_factor, size.height() * scale_factor)

    # 高解析渲染到 QImage
    image = QImage(upscale_size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter)
    painter.end()

    # 縮小回目標大小並使用平滑轉換
    return QPixmap.fromImage(image).scaled(
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )


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