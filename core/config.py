from qfluentwidgets import Theme

# 語言選項：{顯示名稱: 語言代碼}
# 顯示名稱將直接用於下拉框，語言代碼用於載入翻譯檔和儲存設定
LANGUAGES = {
    "English": "en",
    "简体中文": "zh_CN",
    "繁體中文": "zh_TW"
}

# 主題選項：{顯示名稱: Theme列舉}
# 顯示名稱用於下拉框和儲存設定
THEMES = {
    "Light": Theme.LIGHT,
    "Dark": Theme.DARK,
    "System": Theme.AUTO
}

NAVIGATIONS = {
    "photo": "photo"
}