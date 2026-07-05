"""CLI 進入點：產生硬體健康報告並印出人類可讀的文字報告到 stdout。

唯讀健康檢測工具：本程式與其呼叫的所有模組只讀取硬體/系統資訊，不做任何
寫入、修改韌體、BIOS/UEFI 設定、磁碟分割或驅動程式的操作。

鐵律：即使所有硬體感測都不可用（例如尚未安裝 PawnIO / LibreHardwareMonitor、
尚未安裝 requirements.txt 內的套件、或未以系統管理員身分執行），本程式也
絕不能以未處理例外的方式中止並把 Python traceback 印給一般使用者看；必須
印出清楚的「哪些項目不可用、為什麼、要怎麼做才能啟用」。

執行方式（工作目錄在專案根目錄 E:/program/pc-health-check/）：
    python src/pc_health_check/main.py
"""

from __future__ import annotations

import argparse
import os
import sys

# 本程式預期以 `python src/pc_health_check/main.py` 直接執行（而非
# `python -m pc_health_check.main`），此時 Python 只會把本檔案所在目錄
# （.../src/pc_health_check）放進 sys.path，並不包含其上層的 .../src。
# 為了讓 `import pc_health_check.xxx` 這種絕對匯入能成功解析，這裡手動把
# .../src（本套件的上層目錄）加進 sys.path。專案目前未走 `pip install -e .`
# 安裝流程，這是骨架階段刻意的簡化作法。
_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)


def _ensure_utf8_console() -> None:
    """避免 Windows 主控台編碼（例如系統『非 Unicode 程式語言』設為 cp950）
    與主控台實際 codepage 不一致，導致中文輸出變亂碼。強制以 UTF-8 編碼寫出，
    無法 reconfigure 的串流（例如被重新導向的舊式物件）則略過不處理。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _print_header(report) -> None:
    print("=" * 60)
    print("電腦硬體健康檢測報告")
    print(f"產生時間：{report.generated_at}")
    print("=" * 60)


def _print_footer() -> None:
    print()
    print("=" * 60)
    print("提示：若多數項目顯示不可用，通常代表：")
    print("  1) 尚未安裝 requirements.txt 內的套件（pip install -r requirements.txt）")
    print("  2) 尚未安裝 LibreHardwareMonitor 所需的 PawnIO 驅動")
    print("  3) 目前並非以系統管理員身分執行本程式")
    print("詳細設定步驟請見 docs/setup.md。")
    print("=" * 60)


def _print_friendly_report(report) -> None:
    """把 HealthReport 印成一般使用者看得懂的精簡健康報告（預設模式）。

    只顯示對健康判讀有意義的指標（溫度/使用率/時脈/風扇/電壓/容量），並附上
    正常/注意/警告三級判讀；完整原始感測器清單請用 `--detail`/`-v` 參數。
    """
    # 延後 import：與 report/sensors 模組一致的原則，避免非預期匯入期例外
    # 影響到最外層 main() 的 try/except 兜底。
    from pc_health_check import health

    sections = [
        health.build_cpu_section(report.components["cpu"]),
        health.build_motherboard_section(report.components["motherboard"]),
        health.build_memory_section(report.components["memory"]),
        health.build_disk_section(report.components["disk"]),
        health.build_psu_section(report.components["psu"]),
        health.build_gpu_section(report.components["gpu"]),
    ]

    _print_header(report)
    print()
    print(health.overall_summary(sections))

    for section in sections:
        print()
        if not section.available:
            print(f"[{section.title}]")
            print(f"  不可用：{section.unavailable_reason}")
            continue
        for device in section.devices:
            header = f"[{section.title}]"
            if device.name:
                header += f" {device.name}"
            print(header)
            for item in device.items:
                print(f"  {item.text}")

    _print_footer()


def _print_detail_report(report) -> None:
    """把 HealthReport 印成完整原始感測器清單（`--detail`/`-v` 模式）。

    供進階使用者查看未經篩選的底層資料；資料本身已套用 sensors/ 層的
    正確性修正（RAM PartNumber 亂碼偵測、硬碟容量明顯錯誤 0 值濾除等），
    但不做健康判讀，也不篩選/簡化任何原始感測器項目。
    """
    _print_header(report)

    for status in report.components.values():
        print()
        print(f"[{status.name}]")
        if status.available:
            print("  狀態：可用")
            data = status.data
            readings = getattr(data, "readings", None)
            modules = getattr(data, "modules", None)
            if readings:
                for r in readings:
                    print(f"    - {r}")
            elif modules:
                for m in modules:
                    print(f"    - {m}")
            else:
                print(f"    (資料：{data})")

            if hasattr(data, "nvidia_detail_reason"):
                nv_state = "可用" if getattr(data, "nvidia_detail_available", False) else "不可用"
                print(f"    NVIDIA(nvidia-ml-py) 專屬細節：{nv_state} - {data.nvidia_detail_reason}")
        else:
            print("  狀態：不可用")
            print(f"  原因：{status.reason}")

    _print_footer()


def _parse_args(argv) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="電腦硬體健康檢測報告：預設輸出精簡易懂版本，"
        "加上 --detail/-v 可查看完整原始感測器清單。",
    )
    parser.add_argument(
        "--detail",
        "-v",
        action="store_true",
        help="顯示完整原始感測器清單（進階模式），預設不開啟。",
    )
    return parser.parse_args(argv)


def main() -> int:
    """程式主入口。任何未預期例外都會在此被攔截並印出可讀訊息，不外洩 traceback。"""
    try:
        _ensure_utf8_console()
        args = _parse_args(sys.argv[1:])

        # 延後 import：確保即使 report/sensors 內部模組在 import 期間
        # 發生非預期問題，也能被這裡的 try/except 捕捉到並友善提示，
        # 而不是讓使用者看到裸露的 Python traceback。
        from pc_health_check.report import generate_report

        report = generate_report()
        if args.detail:
            _print_detail_report(report)
        else:
            _print_friendly_report(report)
        return 0
    except Exception as exc:  # noqa: BLE001 - 最外層兜底，鐵律：不得讓使用者看到 traceback
        print("=" * 60, file=sys.stderr)
        print("電腦硬體健康檢測系統發生未預期錯誤，程式已安全中止。", file=sys.stderr)
        print(f"錯誤訊息：{exc}", file=sys.stderr)
        print("請參考 docs/setup.md 確認相依套件安裝與權限設定是否正確。", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
