# core/settings_manager.py
import json
import shutil  # 導入 shutil 模組以進行檔案複製
from pathlib import Path

class SettingsManager:
    """
    管理應用程式的設定。
    如果使用者設定檔不存在，會從專案範本目錄複製一份預設設定。
    """
    def __init__(self):
        # 定義使用者專屬的根目錄 (與 AssetManager 保持一致)
        base_dir = Path.home() / ".stellar-neo"
        base_dir.mkdir(parents=True, exist_ok=True)

        # 定義使用者的設定檔路徑
        self.user_settings_path = base_dir / "settings.json"

        # 定義專案內的範本設定檔路徑
        self.template_settings_path = Path("template/settings.json")

        # 初始化時載入設定檔
        self._data = {}
        self._load()

    def _load(self):
        """
        載入設定檔。
        - 如果找到使用者設定檔，直接載入。
        - 如果找不到，則從範本檔案初始化。
        - 如果使用者設定檔已損壞，則載入一個空設定以防止崩潰。
        """
        try:
            # 嘗試讀取使用者的設定檔
            with open(self.user_settings_path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        except FileNotFoundError:
            # 如果使用者的設定檔不存在，從範本檔案進行初始化
            print(f"使用者設定檔不存在，正在從範本 {self.template_settings_path} 進行初始化...")
            self._init_from_template()
            # 初始化後，再次嘗試載入，這次應該會成功 (除非範本也遺失)
            self._load()
        except json.JSONDecodeError:
            # 如果檔案存在但格式錯誤 (例如空檔案或損壞的 JSON)
            # 為了安全起見，載入一個空字典，避免覆蓋掉使用者可能想手動修復的檔案
            print(f"警告：無法解析設定檔 {self.user_settings_path}。將使用空設定啟動。")
            self._data = {}

    def _init_from_template(self):
        """
        從範本檔案複製一份設定到使用者目錄。
        如果連範本檔案都不存在，則建立一個空的設定檔作為最後的保障。
        """
        try:
            # 檢查範本檔案是否存在
            if self.template_settings_path.exists():
                # 將範本檔案複製到使用者的設定路徑
                shutil.copy(self.template_settings_path, self.user_settings_path)
                print(f"成功將範本複製到 {self.user_settings_path}")
            else:
                # 如果範本檔案不存在，則建立一個空的設定檔
                print(f"警告：範本設定檔 {self.template_settings_path} 未找到。將建立一個空的設定檔。")
                self.set_all({}) # 使用 set_all 來建立一個空的 json 檔案
        except Exception as e:
            # 處理複製過程中可能發生的其他錯誤
            print(f"從範本初始化設定時發生錯誤: {e}")
            self.set_all({}) # 同樣建立一個空的檔案作為降級方案

    def get(self, key, default=None):
        """
        根據鍵 (key) 獲取設定值。
        """
        return self._data.get(key, default)

    def set(self, key, value):
        """
        設定一個鍵值對，並立即將其寫入檔案以持久化。
        """
        self._data[key] = value
        self.set_all(self._data) # 呼叫 set_all 來統一寫入邏輯

    def set_all(self, data: dict):
        """
        【新】將整個字典寫入設定檔，用於初始化和統一的儲存操作。
        """
        self._data = data
        try:
            with open(self.user_settings_path, "w", encoding="utf-8") as f:
                # 使用 ensure_ascii=False 和 indent=2 來儲存為人類可讀的格式
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"寫入設定檔 {self.user_settings_path} 時發生錯誤: {e}")