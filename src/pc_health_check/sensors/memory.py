"""記憶體基本資訊讀取（容量/頻率/製造商），透過 wmi 的 Win32_PhysicalMemory。

誠實標註：消費級（非 ECC）RAM **沒有**可讀的「健康度」指標可言——一般
桌上型/筆電記憶體模組不具備對外暴露的溫度、錯誤率或壽命感測器。本模組
只能提供庫存層級的靜態資訊（容量、頻率、製造商、插槽位置等），僅供
使用者確認硬體組態，不代表任何健康狀態評估。

Win32_PhysicalMemory 查詢為唯讀 SELECT 類查詢，符合本專案唯讀健康檢測鐵律。

PartNumber 亂碼根因調查記錄（2026-07-05，實機驗證）：
本機（Kingston RAM x2）曾出現 `part_number` 顯示為
`'<<<<<<<0-16     <<<<'`、`'KF560C40- <'` 這類亂碼。已用兩種方式排除
「本專案 Python 程式碼解碼/切片錯誤」的可能性：
  1) 直接以 PowerShell `Get-CimInstance Win32_PhysicalMemory` 查詢同一台機器，
     結果逐位元組（byte）相同的亂碼。
  2) 繞過本模組、直接用 `wmi` 套件讀取 `PartNumber` 並印出 `repr()`／逐字元
     hex code，同樣是這組亂碼，證實從 WMI 供應器拿到的字串「本身」就已經
     包含這些字元（例如 `<` = 0x3C），不是本程式後續 `.strip()`／編碼處理
     造成的字元錯位或 bytes/wide-char 誤解讀。
  3) 目前查到最相符的解釋：這是主機板韌體（SMBIOS Type 17 Memory Device
     結構）回報給 WMI 的 PartNumber 欄位資料本身已損壞，常見於啟用
     XMP/DOCP/EXPO 記憶體超頻設定檔、或特定 BIOS/AGESA 版本的已知韌體回報
     瑕疵；並非本程式能在軟體層「還原」的問題。
因此修法採 `_clean_part_number()`：正確 `.strip()` 去除欄位右側補的空白
（SMBIOS 定長欄位慣例），並偵測「內容本身就不像合法型號」的情況（含
允許字元集以外的符號，例如 `<`），一旦判定為無效資料就誠實顯示「未提供」，
不硬湊或截斷出看似合理但其實錯誤的字串。
"""

from __future__ import annotations

import dataclasses
import re
from typing import List, Optional

# 合法記憶體 PartNumber 預期只會出現英數字與常見分隔符號（- _ . / 空白）。
# 已知的韌體回報瑕疵會混入如 `<` 這類在真實型號中幾乎不可能出現的字元，
# 一旦偵測到就代表這筆資料本身已不可信賴（見上方模組 docstring 的調查記錄），
# 顯示「未提供」比硬顯示亂碼或用不可靠的切片邏輯猜測正確字元更誠實。
_PART_NUMBER_ALLOWED_CHARS = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-_./ ]*[A-Za-z0-9]$|^[A-Za-z0-9]$")
_NOT_PROVIDED = "未提供"


def _clean_part_number(raw: Optional[str]) -> str:
    """清理 WMI 回傳的 PartNumber：去除 SMBIOS 定長欄位右側補的空白，
    並在偵測到內容本身就是無效/損壞資料時，回傳「未提供」而非亂碼。"""
    if raw is None:
        return _NOT_PROVIDED
    # SMBIOS 定長欄位慣例是右側補空白，strip() 才是正確作法（不能只砍固定
    # 長度，否則遇到較短型號會誤刪合法字元；也不能用 bytes 切片，避免把
    # 多位元組字元切錯位置）。
    cleaned = str(raw).strip()
    if not cleaned:
        return _NOT_PROVIDED
    if not _PART_NUMBER_ALLOWED_CHARS.match(cleaned):
        return _NOT_PROVIDED
    return cleaned


@dataclasses.dataclass
class MemoryModuleInfo:
    """單一實體記憶體模組的庫存資訊（非健康度）。"""

    manufacturer: str
    capacity_bytes: int
    speed_mhz: int
    part_number: str
    device_locator: str


@dataclasses.dataclass
class MemoryReport:
    """記憶體讀取結果。"""

    available: bool
    reason: str
    modules: List[MemoryModuleInfo] = dataclasses.field(default_factory=list)


def get_memory_report() -> MemoryReport:
    """透過 WMI（唯讀 SELECT 查詢）讀取實體記憶體模組基本資訊。

    消費級 RAM 沒有健康度可讀，此函式只回傳容量/頻率/製造商等庫存資訊。
    """
    try:
        import wmi  # type: ignore
    except ImportError as exc:
        return MemoryReport(
            available=False,
            reason=(
                "未安裝 'wmi'／'pywin32' 套件，無法讀取記憶體資訊："
                f"{exc}。請執行 `pip install -r requirements.txt`。"
            ),
        )
    except Exception as exc:  # noqa: BLE001
        return MemoryReport(
            available=False,
            reason=f"匯入 'wmi' 套件時發生未預期錯誤：{exc}",
        )

    try:
        conn = wmi.WMI()
        modules: List[MemoryModuleInfo] = []
        # Win32_PhysicalMemory：唯讀查詢，僅列舉現有記憶體模組的靜態屬性，
        # 不呼叫任何會變更系統狀態的方法。
        for mem in conn.Win32_PhysicalMemory():
            modules.append(
                MemoryModuleInfo(
                    manufacturer=str(getattr(mem, "Manufacturer", None) or "未知"),
                    capacity_bytes=int(getattr(mem, "Capacity", 0) or 0),
                    speed_mhz=int(getattr(mem, "Speed", 0) or 0),
                    part_number=_clean_part_number(getattr(mem, "PartNumber", None)),
                    device_locator=str(getattr(mem, "DeviceLocator", None) or "未知"),
                )
            )

        if not modules:
            return MemoryReport(
                available=False,
                reason="WMI 查詢成功，但未回傳任何記憶體模組資料。",
            )
        return MemoryReport(available=True, reason="OK", modules=modules)
    except Exception as exc:  # noqa: BLE001 - WMI 連線/查詢失敗時優雅降級
        return MemoryReport(
            available=False,
            reason=f"透過 WMI 讀取記憶體資訊時發生未預期錯誤（可能需要系統管理員權限）：{exc}",
        )
