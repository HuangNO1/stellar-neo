# -*- mode: python ; coding: utf-8 -*-

# 導入 sys 模組以判斷作業系統
import sys

# 這是 PyInstaller 的設定檔。
# 它能讓我們精確控制打包的每一個細節。

# 定義 block_cipher 變數
block_cipher = None

# --- 準備資料檔案列表 ---
# 將所有需要包含的非 .py 資源資料夾都列在這裡
datas = [
    ('assets', 'assets'),
    ('i18n', 'i18n'),
    ('template', 'template'),
    ('ui', 'ui'),
    ('core', 'core'),
    ('app.py', 'app.py')
]


a = Analysis(
    ['main.py'],  # 應用程式的主要進入點
    pathex=[],
    binaries=[],
    datas=datas, # 使用我們上面準備好的 datas 列表

    # --- 核心修正：明確加入 PyQt6.sip ---
    # 解決某些環境下 "ModuleNotFoundError: No module named 'PyQt6.sip'" 的問題
    hiddenimports=['PyQt6.sip'],

    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 排除開發用的資料夾
    excludes=[
        'preview',
        'thinking',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='StellarNeo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False, # GUI 應用必須是 False
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icons/logo.png'
)

# 使用 COLLECT 來組合最終的應用程式資料夾
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='StellarNeo'
)
