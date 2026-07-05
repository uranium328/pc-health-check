"""pywebview 桌面 UI 進入點：把 CLI 版的硬體健康檢測報告改用圖形介面呈現。

唯讀健康檢測工具：本檔與其呼叫的所有資料層模組（report.py/health.py/
engine.py）只讀取硬體/系統資訊，本檔本身不新增任何寫入操作；前端只呼叫
下方 `Api.get_report()` / `Api.refresh()` 兩個「重新讀取」方法，兩者都只是
呼叫既有的 `generate_report()`，不做任何硬體/韌體/磁碟/驅動程式的寫入。

鐵律延續（比照 main.py 的 CLI 版本）：即使所有硬體感測都不可用（例如尚未
安裝 PawnIO / LibreHardwareMonitor、尚未安裝 requirements.txt 內的套件、或
未以系統管理員身分執行），本視窗也絕不能因為感測失敗而整個崩潰或讓使用者
看到裸露的 Python traceback；必須正常開啟，並在畫面上顯示「不可用＋原因」。

執行方式（工作目錄在專案根目錄 E:/program/pc-health-check/）：
    python src/pc_health_check/ui/app.py
"""

from __future__ import annotations

import datetime
import os
import sys

# 本程式預期以 `python src/pc_health_check/ui/app.py` 直接執行。此時 Python
# 只會把本檔案所在目錄（.../src/pc_health_check/ui）放進 sys.path，並不包含
# 上層的 .../src，因此 `import pc_health_check.xxx` 這種絕對匯入會失敗。
# 這裡手動把 .../src（本套件的上層目錄）加進 sys.path，寫法與寫法比照
# main.py 的 `_SRC_DIR` 處理（此檔比 main.py 多巢狀一層 ui/ 目錄，因此多
# 一次 dirname）。專案目前未走 `pip install -e .` 安裝流程，這是骨架階段
# 刻意的簡化作法。
#
# 經 PyInstaller 打包凍結後（`sys.frozen` 為 True），`pc_health_check` 套件
# 已隨 PYZ 一併打包、可直接 import，不需要也不應該手動塞 sys.path；靜態
# 資源（ui/web 底下的 index.html 等）則改用 `pyinstaller/app.spec` 的
# `datas` 設定，複製到 `sys._MEIPASS` 底下相同的相對路徑結構。
if getattr(sys, "frozen", False):
    _WEB_DIR = os.path.join(sys._MEIPASS, "pc_health_check", "ui", "web")  # type: ignore[attr-defined]
else:
    _SRC_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _SRC_DIR not in sys.path:
        sys.path.insert(0, _SRC_DIR)
    _WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

_INDEX_HTML = os.path.join(_WEB_DIR, "index.html")

APP_TITLE = "電腦硬體健康檢測"
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 720
WINDOW_MIN_SIZE = (760, 480)

# 六大元件在報告中固定的顯示順序（對照 report.py 的 `components` dict keys）。
_SECTION_ORDER = ("cpu", "motherboard", "memory", "disk", "psu", "gpu")


def _ensure_utf8_console() -> None:
    """比照 main.py 的同名函式：避免 Windows 主控台編碼不一致造成中文亂碼。

    本視窗程式本身不靠 stdout 顯示報告內容（顯示交給 HTML 頁面），但啟動期
    的例外訊息仍可能印到 stderr（例如終端機直接執行時），保留這層保護與
    CLI 版本一致，避免中文錯誤訊息在終端機顯示為亂碼。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _level_from_verdicts(verdicts) -> str:
    """把一組 health.py 判讀字串（正常/注意/警告）化簡成單一等級字串。

    只讀取 health.py 已經算好的 NORMAL/ATTENTION/CRITICAL 常數做比對，不
    新增任何門檻或判讀邏輯——沿用既有判讀結果，只是聚合成一個代表性等級
    給卡頭徽章 / 整體橫幅使用。
    """
    from pc_health_check import health

    if health.CRITICAL in verdicts:
        return "critical"
    if health.ATTENTION in verdicts:
        return "attention"
    return "normal"


def _serialize_section(key: str, section) -> dict:
    """把一個 `health.FriendlySection` 轉成前端可用的 JSON 結構。

    純資料轉換：不重算任何判讀，`badge_level`/每個 item 的 verdict 全部
    直接沿用 `section`/`item` 既有欄位。
    """
    if not section.available:
        badge_level = "unavailable"
    else:
        badge_level = _level_from_verdicts(section.verdicts())

    devices = [
        {
            "name": device.name,
            "items": [{"text": item.text, "verdict": item.verdict} for item in device.items],
        }
        for device in section.devices
    ]

    return {
        "key": key,
        "title": section.title,
        "available": section.available,
        "unavailable_reason": section.unavailable_reason,
        "badge_level": badge_level,
        "devices": devices,
    }


def _format_timestamp(iso_string: str) -> str:
    try:
        dt = datetime.datetime.fromisoformat(iso_string)
        return dt.strftime("%H:%M:%S")
    except (TypeError, ValueError):
        return ""


def build_report_payload() -> dict:
    """呼叫既有資料層（report.py/health.py/engine.py）產生一份可序列化給
    前端的報告 payload。

    鐵律延續：任何例外都必須在此被攔截，回傳一個 `ok=False` 的錯誤結構，
    絕不能讓例外往外拋到 pywebview 的 js_api 呼叫邊界——那會讓前端只看到
    一個被 reject 的 Promise 與不可預期的錯誤訊息，等同違反「不能因為感測
    失敗讓整個 UI 掛掉」的要求。
    """
    try:
        from pc_health_check import engine, health
        from pc_health_check.report import generate_report

        report = generate_report()

        section_builders = {
            "cpu": health.build_cpu_section,
            "motherboard": health.build_motherboard_section,
            "memory": health.build_memory_section,
            "disk": health.build_disk_section,
            "psu": health.build_psu_section,
            "gpu": health.build_gpu_section,
        }

        sections_by_key = [
            (key, section_builders[key](report.components[key])) for key in _SECTION_ORDER
        ]
        sections = [section for _, section in sections_by_key]

        overall_text = health.overall_summary(sections)
        all_verdicts = [v for section in sections for v in section.verdicts()]
        overall_level = _level_from_verdicts(all_verdicts)

        try:
            engine_status = engine.get_engine()
            engine_ready = bool(engine_status.ready)
            engine_reason = str(engine_status.reason)
        except Exception as exc:  # noqa: BLE001 - 查詢引擎狀態本身也不能讓 UI 崩潰
            engine_ready = False
            engine_reason = f"查詢感測引擎狀態時發生未預期例外：{exc}"

        return {
            "ok": True,
            "generated_at": report.generated_at,
            "generated_at_display": _format_timestamp(report.generated_at),
            "overall": {"level": overall_level, "text": overall_text},
            "info_banner": {
                "show": not engine_ready,
                "text": (
                    "部分硬體感測目前不可用（通常是尚未以系統管理員身分執行，"
                    "或尚未安裝 LibreHardwareMonitor 所需的 PawnIO 驅動）。"
                    f"詳細原因：{engine_reason}"
                ),
            },
            "sections": [_serialize_section(key, section) for key, section in sections_by_key],
        }
    except Exception as exc:  # noqa: BLE001 - 鐵律：資料層任何未預期例外都不能讓 UI 崩潰
        now = datetime.datetime.now()
        return {
            "ok": False,
            "error": str(exc),
            "generated_at": now.isoformat(),
            "generated_at_display": now.strftime("%H:%M:%S"),
        }


class Api:
    """曝露給前端 JS 呼叫的方法（pywebview `js_api`）。

    前端透過 `window.pywebview.api.get_report()` / `.refresh()` 呼叫，兩者
    都只是重新讀取（唯讀），不做任何寫入操作；兩個方法刻意保持一致行為，
    區分命名只是對應「初次取得」與「使用者按下重新整理」兩種語意。
    """

    def get_report(self) -> dict:
        return build_report_payload()

    def refresh(self) -> dict:
        return build_report_payload()


def _on_window_closed() -> None:
    """視窗關閉時強制結束整個 Python 行程，避免背景殘留。

    pythonnet 載入 LibreHardwareMonitor DLL 後可能存在非 daemon 的 CLR
    執行緒；只結束主執行緒不保證行程一併結束，因此這裡用 `os._exit`
    直接終止整個行程，確保「關閉視窗＝行程結束」，不留殘留行程。
    """
    os._exit(0)


def main() -> int:
    _ensure_utf8_console()

    try:
        import webview
    except Exception as exc:  # noqa: BLE001 - 鐵律：不得讓使用者看到 traceback
        print(f"無法載入 pywebview 套件：{exc}", file=sys.stderr)
        print("請先執行 `pip install pywebview`（或 `pip install -r requirements.txt`）。", file=sys.stderr)
        return 1

    try:
        api = Api()
        window = webview.create_window(
            APP_TITLE,
            _INDEX_HTML,
            js_api=api,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            resizable=True,
            min_size=WINDOW_MIN_SIZE,
        )
        window.events.closed += _on_window_closed
        # 明確指定 edgechromium（WebView2）後端，對應 Windows 選型決策。
        # 固定後端而非讓 pywebview 自動偵測，可避免
        # PyInstaller 打包時把開發機上剛好裝著、但本專案不會用到的其他後端
        # （例如 GPL 授權的 PyQt5）誤判成相依套件一併打包進 exe。
        webview.start(gui="edgechromium")
        return 0
    except Exception as exc:  # noqa: BLE001 - 鐵律：不得讓使用者看到 traceback
        print("=" * 60, file=sys.stderr)
        print("電腦硬體健康檢測 UI 發生未預期錯誤，程式已安全中止。", file=sys.stderr)
        print(f"錯誤訊息：{exc}", file=sys.stderr)
        print("請參考 docs/setup.md 確認相依套件安裝與權限設定是否正確。", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        return 1


def _run_selftest() -> int:
    """免開視窗的自我檢查：供打包後的自動化煙霧測試使用（見 build_scripts/smoke_test.ps1）。

    只確認「靜態資源找得到路徑」與「資料層流程跑得完不崩潰」兩件事，不驗證
    實際硬體感測數值是否正確——那必須在真實硬體上人工核對。
    """
    _ensure_utf8_console()

    if not os.path.isfile(_INDEX_HTML):
        print(f"selftest 失敗：找不到 {_INDEX_HTML}", file=sys.stderr)
        return 1

    payload = build_report_payload()
    if not isinstance(payload, dict) or "generated_at" not in payload:
        print("selftest 失敗：build_report_payload() 回傳格式不符預期", file=sys.stderr)
        return 1

    print("selftest ok")
    print(f"index_html={_INDEX_HTML}")
    print(f"report_ok={payload.get('ok')}")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_run_selftest())
    sys.exit(main())
