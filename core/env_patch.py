import os


def patch_qt_platform():
    """
    如果在 kde 的 wayland 下因為無法設置窗口透明度，
    所以運行的時候FluentWindow的側邊導覽icon用滑鼠懸浮會報錯
    This plugin does not support setting window opacity，這裡需要添加檢測
    可以强制使用 X11 而非 Wayland：使用export QT_QPA_PLATFORM=xcb
    """
    is_wayland = os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
    is_kde = (
            os.environ.get("KDE_FULL_SESSION") == "true" or
            "plasma" in os.environ.get("DESKTOP_SESSION", "").lower()
    )

    if is_wayland and is_kde:
        print("[INFO] KDE + Wayland detected, forcing QT_QPA_PLATFORM=xcb")
        os.environ["QT_QPA_PLATFORM"] = "xcb"
