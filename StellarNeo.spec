# -*- mode: python ; coding: utf-8 -*-

# 這是 PyInstaller 的設定檔。
# 它能讓我們精確控制打包的每一個細節。

# 定義 block_cipher 變數
block_cipher = None


a = Analysis(
    ['main.py'],  # 應用程式的主要進入點
    pathex=[],
    binaries=[],

    # --- 核心設定：告訴 PyInstaller 需要包含哪些資料檔案 ---
    # 格式為 ('來源路徑', '打包後在根目錄下的目標路徑')
    datas=[
        ('assets', 'assets'),          # 包含整個 assets 資料夾
        ('i18n', 'i18n'),              # 包含整個 i18n 資料夾
        ('template', 'template'),      # 包含整個 template 資料夾
        ('ui/components', 'ui/components') # 包含所有的 .ui 檔案
    ],

    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],

    # --- 核心設定：告訴 PyInstaller 需要排除哪些檔案或資料夾 ---
    # 這裡我們排除所有開發相關、不需要發布的內容。
    excludes=[
        'preview',   # 排除 README 用的圖片
        'thinking',  # 排除您的開發筆記
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
    name='StellarNeo',  # 執行檔的名稱
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # 如果有安裝 UPX，可以壓縮執行檔大小
    runtime_tmpdir=None,
    console=False,  # 對於 GUI 應用程式，必須是 False
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icons/logo.png'  # 修正：icon 應為字串
)

# 使用 COLLECT 來組合最終的應用程式資料夾
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='StellarNeo' # 最終輸出的資料夾名稱
)