# view_logo.py (重構後)

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget, QListWidgetItem, QFileDialog
from qfluentwidgets import MessageBox

from core.asset_manager import AssetManager
from core.translator import Translator
from ui.customs.logo_item_widget import LogoItemWidget


class LogoView(QWidget):
    # TODO 如果文件名過長 需要考慮
    def __init__(self, asset_manager: AssetManager, translator: Translator, parent=None):
        super().__init__(parent)
        self.translator = translator
        self.tr = self.translator.get

        uic.loadUi("ui/components/logo_manager.ui", self)

        self.asset_manager = asset_manager
        self._is_selecting_all = False  # 防止信號循環的標誌

        # 設定列表間距
        self.user_logo_list_widget.setSpacing(2)
        self.default_logo_list_widget.setSpacing(2)

        self._translate_ui()
        self._connect_signals()
        self.load_logos()

    def _translate_ui(self):
        # 翻譯標題和按鈕文字
        self.title_label.setText(self.tr("logo_management", "Logo Management"))
        self.upload_logo_button.setText(self.tr("upload_logo_button", "Upload Logo"))
        self.select_all_checkbox.setText(self.tr("gallery_select_all", "Select All"))

        self.clear_selected_button.setText(self.tr("gallery_clear_selected", "Clear Selected"))
        self.userLogoTitle.setText(self.tr("user_uploaded_logos", "User Uploaded Logos"))
        self.defaultLogoTitle.setText(self.tr("default_app_logos", "App Defaults"))

    def _connect_signals(self):
        # 連接「上傳」、「全選」、「清除」按鈕的信號，這些操作只針對使用者列表

        self.upload_logo_button.clicked.connect(self.upload_logo)
        self.select_all_checkbox.stateChanged.connect(self._on_select_all_changed)

        self.clear_selected_button.clicked.connect(self._on_clear_selected_clicked)

    def load_logos(self):
        """讀取並分類載入使用者 Logo 和預設 Logo"""
        # 清空兩個列表
        self.user_logo_list_widget.clear()
        self.default_logo_list_widget.clear()

        # 1. 載入使用者上傳的 Logo (可管理)
        user_logos = self.asset_manager.get_user_logos()
        for logo_path in user_logos:
            icon = QIcon(logo_path)
            # 使用可勾選的 LogoItemWidget
            item_widget = LogoItemWidget(logo_path, icon, self)
            # 連接勾選狀態變更信號，以便更新「全選」框的狀態
            item_widget.selection_changed.connect(self._update_select_all_checkbox_state)

            list_item = QListWidgetItem(self.user_logo_list_widget)
            list_item.setData(Qt.ItemDataRole.UserRole, logo_path)
            list_item.setSizeHint(item_widget.sizeHint())
            self.user_logo_list_widget.addItem(list_item)
            self.user_logo_list_widget.setItemWidget(list_item, item_widget)

        # 2. 載入應用程式預設的 Logo (唯讀)
        default_logos = self.asset_manager.get_default_logos()
        for logo_path in default_logos:
            icon = QIcon(logo_path)
            # 使用不可勾選的 LogoItemWidget (透過修改其建構函數或屬性)
            # 為了簡單起見，我們仍然使用 LogoItemWidget，但我們不連接它的信號，
            # 並且在 widget 內部可以把 checkbox 禁用
            item_widget = LogoItemWidget(logo_path, icon, self)
            item_widget.checkbox.setEnabled(False)  # 禁用勾選框
            item_widget.checkbox.setVisible(False)

            list_item = QListWidgetItem(self.default_logo_list_widget)
            list_item.setData(Qt.ItemDataRole.UserRole, logo_path)
            list_item.setSizeHint(item_widget.sizeHint())
            self.default_logo_list_widget.addItem(list_item)
            self.default_logo_list_widget.setItemWidget(list_item, item_widget)

        # 根據使用者列表的狀態更新 UI
        self._update_select_all_checkbox_state()

    def upload_logo(self):
        """開啟檔案對話框以上傳新的 Logo"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            self.tr("select_logo_dialog", "Select Logo(s)"),
            "",
            f"{self.tr("image_files", "Image Files")} (*.png *.jpg *.jpeg *.svg)")
        if files:
            for file_path in files:
                self.asset_manager.add_logo(file_path)
            # 上傳後重新載入所有 Logo
            self.load_logos()

    def _on_select_all_changed(self, state: Qt.CheckState):
        """【邏輯修正】處理'全選'核取方塊的狀態變化"""
        if self._is_selecting_all:
            return

        self._is_selecting_all = True

        # 核心修正：判斷當前是否已經是全選狀態
        # 如果不是，則點擊後應該全選；如果是，則點擊後應該全不選。
        total_count = self.user_logo_list_widget.count()
        checked_count = sum(
            self.user_logo_list_widget.itemWidget(self.user_logo_list_widget.item(i)).is_checked()
            for i in range(total_count)
        )
        should_check = not (checked_count == total_count and total_count > 0)

        # 遍歷使用者列表，設定每個項目的勾選狀態
        for i in range(total_count):
            item = self.user_logo_list_widget.item(i)
            widget = self.user_logo_list_widget.itemWidget(item)
            if widget:
                widget.set_checked(should_check)

        self._is_selecting_all = False
        # 手動更新一次checkbox狀態，確保與列表項同步
        self._update_select_all_checkbox_state()

    def _update_select_all_checkbox_state(self):
        """根據使用者列表的勾選狀態，更新'全選'核取方塊的狀態 (未選/部分選/全選)"""
        if self._is_selecting_all:
            return

        total_count = self.user_logo_list_widget.count()
        if total_count == 0:
            self.select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
            self.select_all_checkbox.setEnabled(False)  # 沒有項目時禁用
            return

        self.select_all_checkbox.setEnabled(True)
        checked_count = 0
        for i in range(total_count):
            item = self.user_logo_list_widget.item(i)
            widget = self.user_logo_list_widget.itemWidget(item)
            if widget and widget.is_checked():
                checked_count += 1

        # 阻斷信號以防止循環觸發 _on_select_all_changed
        self.select_all_checkbox.blockSignals(True)
        if checked_count == 0:
            self.select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
        elif checked_count == total_count:
            self.select_all_checkbox.setCheckState(Qt.CheckState.Checked)
        else:
            self.select_all_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
        self.select_all_checkbox.blockSignals(False)

    def _on_clear_selected_clicked(self):
        """處理'清除選取'按鈕的點擊事件"""
        # 找出所有被選中的項目
        items_to_delete = []
        for i in range(self.user_logo_list_widget.count()):
            list_item = self.user_logo_list_widget.item(i)
            item_widget = self.user_logo_list_widget.itemWidget(list_item)
            if item_widget and item_widget.is_checked():
                items_to_delete.append(list_item)

        if not items_to_delete:
            return

        # 彈出確認對話框
        title = self.tr("confirm_delete_title", "Confirm Deletion")
        body = self.tr("confirm_clear_selected_body_logo", "Delete {count} selected logo(s)?").format(
            count=len(items_to_delete))
        self.msg_box = MessageBox(title, body, self.window())
        self.msg_box.yesButton.setText(self.tr("ok", "OK"))
        self.msg_box.cancelButton.setText(self.tr("cancel", "Cancel"))

        if self.msg_box.exec():
            # 遍歷並刪除所有選中的項目
            for list_item in items_to_delete:
                logo_path = list_item.data(Qt.ItemDataRole.UserRole)
                self.asset_manager.delete_logo(logo_path)
            # 操作完成後，重新載入列表以確保同步
            self.load_logos()
