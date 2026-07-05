# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec：建置安裝版 exe（dist/PCHealthCheckSetup.exe）。

執行方式（在專案根目錄執行，且必須先跑過 pyinstaller/app.spec 產生
dist/PCHealthCheck.exe，因為本檔會把它當 payload 內嵌進來）：
    pyinstaller installer/installer.spec

不依賴 Inno Setup/NSIS：本身也是單一 exe，使用者下載雙擊即可安裝。
"""

import os

_SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))
_PROJECT_ROOT = os.path.dirname(_SPEC_DIR)
_PAYLOAD_EXE = os.path.join(_PROJECT_ROOT, "dist", "PCHealthCheck.exe")

if not os.path.isfile(_PAYLOAD_EXE):
    raise SystemExit(
        f"找不到 {_PAYLOAD_EXE}，請先執行 `pyinstaller pyinstaller/app.spec` 產生免安裝版 exe。"
    )

a = Analysis(
    [os.path.join(_SPEC_DIR, "installer.py")],
    pathex=[_SPEC_DIR],
    binaries=[],
    datas=[(_PAYLOAD_EXE, "payload")],
    hiddenimports=["win32com.client", "win32timezone"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="PCHealthCheckSetup",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=False,
)
