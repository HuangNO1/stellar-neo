import os
from PyInstaller.utils.hooks import collect_submodules

project_root = os.path.abspath(os.path.join(os.getcwd(), 'src'))

a = Analysis(
    ['src/main.py'],
    pathex=[project_root],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('i18n', 'i18n'),
        ('template', 'template'),
        ('ui', 'ui'),
        ('core', 'core')
    ],
    hiddenimports=['PyQt6.sip'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['preview', 'thinking'],
    cipher=None,
    noarchive=False
)

# 若 core 資料夾有額外模組，也可 collect_submodules
hidden_mods = collect_submodules('app')
a.hiddenimports += hidden_mods

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='StellarNeo',
    debug=False,
    strip=False,
    upx=True,
    console=False
)

# 使用 COLLECT 來組合最終的應用程式資料夾
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='StellarNeo'
)
