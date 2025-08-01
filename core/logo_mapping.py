# core/logo_mapping.py
import os

# 定義相機製造商與 Logo 檔案的對應關係
LOGO_MAPPING = {
    "Canon": "canon.png",
    "CANON": "canon.png",

    "NIKON CORPORATION": "nikon.png",
    "NIKON": "nikon.png",
    "Nikon": "nikon.png",

    "SONY": "sony.png",
    "Sony": "sony.png",
    "ILCE-7M4": "sony.png",  # 特定 Sony 機型

    "FUJIFILM": "fujifilm.png",
    "Fujifilm": "fujifilm.png",

    "Panasonic": "panasonic.png",
    "PANASONIC": "panasonic.png",
    "Panasonic Corp.": "panasonic.png",

    "LEICA CAMERA AG": "leica.png",
    "Leica": "leica.png",

    "RICOH IMAGING COMPANY, LTD.": "ricoh.png",
    "Ricoh": "ricoh.png",

    "OM Digital Solutions": "omsystem.png",
    "OLYMPUS CORPORATION": "olympus.png",
    "Olympus": "olympus.png",

    "PENTAX": "pentax.png",
    "PENTAX Corporation": "pentax.png",
    "Asahi Optical Co., Ltd.": "pentax.png",

    "HASSELBLAD": "hasselblad.png",
    "Hasselblad": "hasselblad.png",

    "Sigma": "sigma.png",
    "SIGMA": "sigma.png",

    "Minolta": "minolta.png",
    "Konica Minolta": "minolta.png",

    "KODAK": "kodak.png",
    "Eastman Kodak Company": "kodak.png",

    "Casio": "casio.png",
    "CASIO COMPUTER CO.,LTD.": "casio.png",

    "Vivitar": "vivitar.png",
    "Vivitar Corporation": "vivitar.png",

    "Zeiss": "zeiss.png",
}
# 手機品牌
LOGO_MAPPING.update({
    "Apple": "apple.png",
    "Apple Inc.": "apple.png",

    "SAMSUNG": "samsung.png",
    "Samsung": "samsung.png",
    "SAMSUNG ELECTRONICS": "samsung.png",

    "HUAWEI": "huawei.png",
    "Huawei": "huawei.png",

    "Xiaomi": "xiaomi.png",
    "XIAOMI": "xiaomi.png",
    "MIUI": "xiaomi.png",  # 有時記錄系統名

    "OPPO": "oppo.png",
    "Oppo": "oppo.png",

    "Vivo": "vivo.png",
    "VIVO": "vivo.png",

    "Google": "google.png",
    "Google Pixel": "google.png",

    "OnePlus": "oneplus.png",
    "ONEPLUS": "oneplus.png",

    "Sony Ericsson": "sony.png",  # 舊款手機

    "Realme": "realme.png",
    "REALME": "realme.png",

    "LG": "lg.png",
    "LG Electronics": "lg.png",

    "Meizu": "meizu.png",
    "MEIZU": "meizu.png",
})

# 無人機 / 行動攝影裝置
LOGO_MAPPING.update({
    "DJI": "dji.png",
    "DJI Technology Co., Ltd": "dji.png",

    "GoPro": "gopro.png",
    "GoPro, Inc.": "gopro.png",

    "Autel Robotics": "autel.png",
    "Parrot": "parrot.png",
    "Yuneec": "yuneec.png",

    "Insta360": "insta360.png",
    "INSTA360": "insta360.png",

    "Blackmagic Design": "blackmagic.png",
    "Blackmagic": "blackmagic.png",

    "Garmin": "garmin.png",
    "Garmin Ltd.": "garmin.png",
})

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
