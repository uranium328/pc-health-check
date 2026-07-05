"""輕量自製安裝程式（不依賴 Inno Setup/NSIS，本身也是單一 exe）。

用法（打包後）：
    PCHealthCheckSetup.exe          互動安裝（跳確認視窗）
    PCHealthCheckSetup.exe -y       靜默安裝（供自動化煙霧測試用，見 build_scripts/smoke_test.ps1）
    PCHealthCheckSetup.exe --uninstall [-y]   解除安裝

安裝內容：把內嵌的免安裝版 PCHealthCheck.exe 複製到
`%LOCALAPPDATA%\\Programs\\PCHealthCheck\\`、建立開始功能表捷徑、寫入
HKCU 底下的解除安裝機碼（讓「新增或移除程式」看得到）。全程只寫 HKCU，
安裝本身不需要提權；PCHealthCheck.exe 本身的管理員權限需求（讀硬體感測器）
由它自己的 exe manifest（`--uac-admin`）處理，與安裝流程無關。

鐵律延續：本程式不觸碰任何硬體/韌體/驅動程式，只做檔案複製、捷徑建立、
登錄機碼寫入這類「安裝一個應用程式」的標準動作。PawnIO 驅動（唯讀感測用途）
只用訊息視窗提示使用者自行至官方網站安裝，不自動下載或執行任何驅動安裝程式。

跟 Inno Setup/NSIS 相比的已知取捨：
沒有標準精靈 UI、升級/覆蓋安裝判斷陽春（只能覆蓋複製）、不支援多語系、
沒有簽章與 SmartScreen 信譽累積、解除安裝靠固定清單而非掃描殘留機碼、
解除安裝不會刪掉安裝目錄本身與 `Uninstall.exe`（見下方 `uninstall()` 說明）。
"""

from __future__ import annotations

import ctypes
import os
import shutil
import sys
import winreg

APP_NAME = "PCHealthCheck"
APP_DISPLAY_NAME = "電腦硬體健康檢測"
APP_VERSION = "0.1.0"
PAWNIO_URL = "https://pawnio.eu/"

INSTALL_DIR = os.path.join(os.environ["LOCALAPPDATA"], "Programs", APP_NAME)
TARGET_EXE = os.path.join(INSTALL_DIR, f"{APP_NAME}.exe")
UNINSTALLER_EXE = os.path.join(INSTALL_DIR, "Uninstall.exe")

UNINSTALL_KEY = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_NAME}"

START_MENU_DIR = os.path.join(
    os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs"
)
SHORTCUT_PATH = os.path.join(START_MENU_DIR, f"{APP_DISPLAY_NAME}.lnk")

_MB_YESNO = 0x04
_MB_ICONQUESTION = 0x20
_MB_ICONINFORMATION = 0x40
_IDYES = 6


def _ensure_utf8_console() -> None:
    """比照 main.py/app.py 的同名函式：避免 Windows 主控台編碼不一致造成中文亂碼

    本機 Python 偵測到的 stdout 編碼可能是 cp950，與主控台 codepage 顯示
    不一致，不能只印 ASCII 就假設中文輸出沒問題。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _payload_path() -> str:
    """回傳內嵌的免安裝版 exe 來源路徑。

    凍結模式：由 installer.spec 的 `datas` 放進 `sys._MEIPASS/payload/`；
    開發模式（直接用 python 執行本檔測試邏輯）：退回讀專案的 `dist/` 目錄，
    對應 build_scripts/build.ps1 先建 app.spec、再建 installer.spec 的順序。
    """
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "payload", f"{APP_NAME}.exe")  # type: ignore[attr-defined]
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "dist", f"{APP_NAME}.exe")


def _installer_source_path() -> str:
    """回傳目前正在執行的安裝程式本體路徑，供複製成 Uninstall.exe 使用。"""
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.abspath(__file__)


def _confirm(message: str) -> bool:
    result = ctypes.windll.user32.MessageBoxW(  # type: ignore[attr-defined]
        0, message, APP_DISPLAY_NAME, _MB_YESNO | _MB_ICONQUESTION
    )
    return result == _IDYES


def _show_message(message: str) -> None:
    ctypes.windll.user32.MessageBoxW(0, message, APP_DISPLAY_NAME, _MB_ICONINFORMATION)  # type: ignore[attr-defined]


def _create_shortcut() -> None:
    import win32com.client  # 延遲載入：只有安裝流程需要，减少非必要相依載入時機

    os.makedirs(START_MENU_DIR, exist_ok=True)
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(SHORTCUT_PATH)
    shortcut.Targetpath = TARGET_EXE
    shortcut.WorkingDirectory = INSTALL_DIR
    shortcut.IconLocation = TARGET_EXE
    shortcut.Description = APP_DISPLAY_NAME
    shortcut.save()


def _write_uninstall_registry() -> None:
    estimated_size_kb = 0
    if os.path.isfile(TARGET_EXE):
        estimated_size_kb = os.path.getsize(TARGET_EXE) // 1024

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_DISPLAY_NAME)
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, APP_DISPLAY_NAME)
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, INSTALL_DIR)
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, TARGET_EXE)
        winreg.SetValueEx(
            key, "UninstallString", 0, winreg.REG_SZ, f'"{UNINSTALLER_EXE}" --uninstall'
        )
        winreg.SetValueEx(key, "QuietUninstallString", 0, winreg.REG_SZ, f'"{UNINSTALLER_EXE}" --uninstall -y')
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, estimated_size_kb)


def _remove_uninstall_registry() -> None:
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except FileNotFoundError:
        pass


def install(silent: bool = False) -> int:
    payload = _payload_path()
    if not os.path.isfile(payload):
        print(f"安裝失敗：找不到內嵌的應用程式主體 {payload}", file=sys.stderr)
        return 1

    if not silent and not _confirm(
        f"要把「{APP_DISPLAY_NAME}」安裝到下列位置嗎？\n\n{INSTALL_DIR}"
    ):
        print("使用者取消安裝。")
        return 1

    os.makedirs(INSTALL_DIR, exist_ok=True)
    shutil.copy2(payload, TARGET_EXE)
    shutil.copy2(_installer_source_path(), UNINSTALLER_EXE)
    _create_shortcut()
    _write_uninstall_registry()

    reminder = (
        f"安裝完成！\n\n"
        f"本工具讀取硬體感測器（主機板/GPU/硬碟）需要「PawnIO」核心驅動\n"
        f"（唯讀用途，不做任何寫入/設定變更）。若尚未安裝，請至官方網站：\n"
        f"{PAWNIO_URL}\n"
        f"下載安裝。本安裝程式不會自動安裝驅動。\n\n"
        f"未安裝驅動時，程式仍可正常開啟，只是部分感測器會顯示「不可用」。"
    )
    print("安裝完成。")
    print(f"安裝路徑：{INSTALL_DIR}")
    print(reminder)
    if not silent:
        _show_message(reminder)

    return 0


def uninstall(silent: bool = False) -> int:
    """移除捷徑、解除安裝機碼、與應用程式主體。

    `Uninstall.exe`（本程式自己）在執行期間會被 Windows 鎖住，無法自我刪除；
    實測過用 detached 子行程延遲刪除整個資料夾的做法，在 PyInstaller onefile
    凍結後不可靠（子行程未能存活到執行完畢），且這種「悄悄 spawn 一個
    detached cmd.exe 做延遲刪除」的行為模式本身也容易被防毒軟體的行為監控
    誤判成惡意軟體的自我刪除手法，對一支要散布給別人的 exe 是不必要的風險。
    折衷做法：直接刪掉會佔空間的應用程式主體，`Uninstall.exe` 本身與安裝
    目錄留著，請使用者事後自行刪除資料夾即可，這是比 Inno Setup/NSIS 陽春
    的已知取捨之一。
    """
    if not silent and not _confirm(f"要移除「{APP_DISPLAY_NAME}」嗎？"):
        print("使用者取消解除安裝。")
        return 1

    if os.path.isfile(SHORTCUT_PATH):
        os.remove(SHORTCUT_PATH)

    _remove_uninstall_registry()

    if os.path.isfile(TARGET_EXE):
        os.remove(TARGET_EXE)

    message = (
        "解除安裝完成。\n\n"
        f"安裝目錄（{INSTALL_DIR}）內僅剩本解除安裝程式本身，\n"
        "可以手動刪除整個資料夾，或留著以備日後需要。"
    )
    print(message)
    if not silent:
        _show_message(message)

    return 0


def main(argv: list[str]) -> int:
    _ensure_utf8_console()
    silent = "-y" in argv
    if "--uninstall" in argv:
        return uninstall(silent=silent)
    return install(silent=silent)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
