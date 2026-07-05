# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec：建置免安裝版 GUI exe（dist/PCHealthCheck.exe）。

執行方式（在專案根目錄執行）：
    pyinstaller pyinstaller/app.spec

只打包 GUI 進入點（ui/app.py）；CLI（main.py）不在打包範圍內，維持給開發者
用 `python src/pc_health_check/main.py` 執行。

可行性依據見 docs/build-feasibility.md：MS Store 版 Python 3.13 可直接建置，
`collect_all("HardwareMonitor")` 已足夠收齊其原生 DLL，不需要額外自訂 hook。
"""

import os

from PyInstaller.utils.hooks import collect_all

_SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))
_PROJECT_ROOT = os.path.dirname(_SPEC_DIR)
_SRC_DIR = os.path.join(_PROJECT_ROOT, "src")
_WEB_SRC = os.path.join(_SRC_DIR, "pc_health_check", "ui", "web")

_hm_datas, _hm_binaries, _hm_hiddenimports = collect_all("HardwareMonitor")

# pywebview 在 Windows 上支援多種後端（edgechromium/cef/qt/gtk/mshtml），
# 打包時預設會把「開發機上剛好裝著」的後端都當成潛在相依收進去。本專案已
# 在 docs/ui-framework-options.md 定案只用 edgechromium（WebView2），且明確
# 選用 pywebview 是為了保持 BSD 授權乾淨（見 ops/lessons.md L-005）；PyQt5
# 屬 GPL/商業雙授權，QtWebKitWidgets 等 Qt 元件不得混進最終發布的 exe，故
# 在此明確排除，不依賴「剛好沒裝」這種脆弱假設。
_EXCLUDED_GUI_BACKENDS = [
    "PyQt5",
    "PyQt6",
    "PySide2",
    "PySide6",
    "gi",
    "cefpython3",
]

a = Analysis(
    [os.path.join(_SRC_DIR, "pc_health_check", "ui", "app.py")],
    pathex=[_SRC_DIR],
    binaries=_hm_binaries,
    datas=[(_WEB_SRC, os.path.join("pc_health_check", "ui", "web"))] + _hm_datas,
    hiddenimports=_hm_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=_EXCLUDED_GUI_BACKENDS,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="PCHealthCheck",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
)
