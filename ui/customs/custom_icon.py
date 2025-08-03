from enum import Enum

from qfluentwidgets import getIconColor, Theme, FluentIconBase

#    請確保您的 import 路徑是正確的
from core.utils import resource_path_str


class MyFluentIcon(FluentIconBase, Enum):
    """ Custom icons """

    WARNING = "warning"
    INFO = "info"

    def path(self, theme=Theme.AUTO):
        # 2. 構造相對路徑字串
        relative_icon_path = f'assets/icons/base/{self.value}_{getIconColor(theme)}.svg'

        # 3. 使用 resource_path() 將其轉換為絕對路徑
        return resource_path_str(relative_icon_path)
