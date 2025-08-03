from PyQt6.QtWidgets import QWidget
from PyQt6 import uic

from core.translator import Translator
from core.utils import resource_path


class AboutView(QWidget):
    def __init__(self, translator: Translator, parent=None):
        super().__init__(parent)
        uic.loadUi(resource_path("ui/components/about.ui"), self)
        self.tr = translator.get
        # 設定滾動區域
        self.ScrollArea.setStyleSheet("QScrollArea{background: transparent; border: none}")
        # 必須給內部的視圖也加上透明背景樣式
        self.scrollWidget.setStyleSheet("QWidget{background: transparent}")

        self.init_all_ui()

    def init_all_ui(self):
        # logo
        self.logoLabel.setImage(resource_path("assets/icons/logo.png"))
        self.logoLabel.scaledToHeight(64)
        self.githubButton.setUrl("https://github.com/HuangNO1/stellar-neo")
        self.blogButton.setUrl("https://huangno1.github.io/")
        self.logoArtButton.setUrl("https://www.pixiv.net/artworks/117867484")
        self.logoArtistButton.setUrl("https://www.pixiv.net/users/16252763")
        # text
        self.aboutAppTitle.setText(self.tr("about_app_title", "About the App"))
        self.aboutAppBody.setText(self.tr("about_app_body", "Given the lack of satisfactory watermark applications on the market, especially with deficiencies in reading EXIF information from images exported by LRC or Luminar Neo, Stellar Neo was born. This application is dedicated to providing truly out-of-the-box, detail-optimized photo frame and watermark tools, hoping to become everyone's top choice."))
        self.aboutAuthorTitle.setText(self.tr("about_author_title", "About the Author"))
        self.creditsTitle.setText(self.tr("about_credits_title", "Acknowledgments and Disclaimer"))
        self.logoCreditPrefixLabel.setText(self.tr("about_credits_prefix", "App Logo source"))
        self.disclaimerLabel.setText(self.tr("about_credits_disclaimer", "The brand logos involved in this application are for learning and reference only. Please do not use them for any commercial purposes."))