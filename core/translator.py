# core/translator.py
import json
import os


class Translator:
    def __init__(self):
        self.translations = {}

    def load(self, language_code: str, base_path: str):
        file_path = os.path.join(base_path, f"{language_code}.json")
        if not os.path.exists(file_path):
            print(f"Translation file not found: {file_path}")
            self.translations = {}
            return
        with open(file_path, "r", encoding="utf-8") as f:
            self.translations = json.load(f)

    def get(self, key: str, default: str = "") -> str:
        return self.translations.get(key, default)
