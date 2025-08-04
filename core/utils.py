import os
import platform
import sys

from PyQt6.QtWidgets import QWidget
from qfluentwidgets import SingleDirectionScrollArea
from pathlib import Path

def get_project_root() -> Path:
    """
    以遞迴方式向上查找，直到找到專案根目錄的標記檔案為止。
    
    一個可靠的標記是 'requirements.txt', 'main.py' 或 '.git' 目錄。
    您可以根據您的專案結構修改這個標記。
    
    :return: 專案根目錄的 Path 物件。
    """
    # 從目前檔案 (__file__) 的目錄開始向上尋找
    current_path = Path(__file__).parent
    while True:
        # 檢查當前路徑下是否存在任何一個標記檔案/目錄
        if (current_path / "requirements.txt").exists() or \
           (current_path / "main.py").exists() or \
           (current_path / ".git").exists() or \
           (current_path / "StellarNeo.spec").exists():
            return current_path
        
        # 如果沒找到，就往上一層目錄
        parent_path = current_path.parent
        
        # 如果已經到達了檔案系統的根目錄（例如 C:\ 或 /），就停止並報錯
        if parent_path == current_path:
            raise FileNotFoundError(
                "無法找到專案根目錄。請確保您的專案根目錄下有 "
                "'requirements.txt', 'main.py', 'StellarNeo.spec' 或 '.git' 等標記檔案/目錄。"
            )
            
        current_path = parent_path

def resource_path_str(relative_path: str) -> str:
    """
    獲取資源的絕對路徑，無論是從開發環境還是從 PyInstaller 打包後的環境。
    此版本會動態尋找專案根目錄，解決了公用函式在子目錄中的路徑問題。
    
    :param relative_path: 資源相對於「專案根目錄」的相對路徑字串。
    :return: 資源的絕對路徑 str。
    """
    try:
        # PyInstaller 執行時，會建立一個暫存目錄，並將路徑存放在 sys._MEIPASS
        # 此時的 base_path 就是打包後的根目錄
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        # 在正常的開發環境中，我們呼叫 get_project_root() 來動態尋找根目錄
        base_path = get_project_root()

    # 將專案根目錄與資源的相對路徑拼接起來
    return str(base_path / relative_path)

def resource_path(relative_path: str) -> Path:
    """
    獲取資源的絕對路徑，無論是從開發環境還是從 PyInstaller 打包後的環境。
    此版本會動態尋找專案根目錄，解決了公用函式在子目錄中的路徑問題。
    
    :param relative_path: 資源相對於「專案根目錄」的相對路徑字串。
    :return: 資源的絕對路徑 Path 物件。
    """
    try:
        # PyInstaller 執行時，會建立一個暫存目錄，並將路徑存放在 sys._MEIPASS
        # 此時的 base_path 就是打包後的根目錄
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        # 在正常的開發環境中，我們呼叫 get_project_root() 來動態尋找根目錄
        base_path = get_project_root()

    # 將專案根目錄與資源的相對路徑拼接起來
    return base_path / relative_path


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

def get_os_type():
    """
    判斷當前運行的作業系統。
    返回 'windows', 'linux', 'darwin' (macOS), 或 'unknown'。
    """
    system = platform.system().lower()
    if 'windows' in system:
        return 'windows'
    elif 'linux' in system:
        return 'linux'
    elif 'darwin' in system:
        return 'darwin'
    return 'unknown'
