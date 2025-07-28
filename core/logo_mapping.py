# core/logo_mapping.py
# 程式碼來自您上傳的 logo_mapping.py
# 定義相機製造商與 Logo 檔案的對應關係
import os

LOGO_MAPPING = {
    "Canon": "canon.png",
    "NIKON CORPORATION": "nikon.png",
    "NIKON": "nikon.png",
    "SONY": "sony.png",
    "ILCE-7M4": "sony.png",
    "FUJIFILM": "fujifilm.png",
    "Panasonic": "panasonic.png",
    "LEICA CAMERA AG": "leica.png",
    "RICOH IMAGING COMPANY, LTD.": "ricoh.png",
    "OM Digital Solutions": "omsystem.png",
    "OLYMPUS CORPORATION": "olympus.png",
}


def get_logo_path(make: str, logos_dir: str):
    if not make:
        return None

    logo_filename = LOGO_MAPPING.get(make)

    if not logo_filename:
        for key, filename in LOGO_MAPPING.items():
            if make.upper().startswith(key.upper()):
                logo_filename = filename
                break

    if logo_filename:
        path = os.path.join(logos_dir, logo_filename)
        return path if os.path.exists(path) else None

    return None
