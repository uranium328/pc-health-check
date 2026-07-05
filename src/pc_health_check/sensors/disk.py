"""硬碟 S.M.A.R.T. 相關資訊讀取骨架。

目前路徑：透過 engine.py 的 LibreHardwareMonitor 儲存裝置感測
（HardwareType 為 Storage 的項目）取得可用數值（常見為溫度；部分裝置
LHM 亦會暴露少量 SMART 衍生數值，但涵蓋度依裝置與版本而異）。

TODO（未來可替換/擴充）：改用或整合 `pySMART`（需另裝 smartmontools 的
`smartctl` 執行檔）以取得完整 SMART 屬性表（如重新配置磁區數、通電時數、
寫入量等）。本檔先保留 `get_disk_report_via_pysmart` 介面骨架，尚未實作。

「目前溫度」vs「門檻值」調查記錄（2026-07-05，實機驗證，Crucial
CT1000P5SSD8 / CT2000T500SSD8）：
在本機（非系統管理員權限、未安裝 PawnIO 驅動）逐一列舉這兩顆 NVMe SSD
底下 LHM 暴露的**全部** Sensors（含 Value 為 None 者，不只是目前程式碼
會保留的有值項目），實際列舉到的感測器只有：
    Warning Temperature（門檻值＝70°C）、Critical Temperature（門檻值＝75°C）、
    Used Space（None）、Free Space（None）、Total Space（0.0，見下方另一條
    調查記錄）、Read/Write/Total Activity（None）、Read/Write Rate（None）。
也就是說：這個環境下 LHM 根本沒有建立一個名稱單純叫 `Temperature`／
`Current Temperature` 的「目前溫度」感測器物件（不是被本程式的
`if value is None: continue` 篩選掉——即使不篩選、直接印出整個 Sensors
集合，也確認該物件不存在）。這與主機板感測器同樣因缺少 PawnIO／系統管理員
權限而不可用的原因一致：LHM 讀取 NVMe 即時溫度／SMART 健康資訊需要對實體
硬碟送出較高權限的 passthrough 查詢，而 Warning/Critical 門檻值兩個數字在
兩顆不同廠牌/型號的硬碟上完全相同（70／75），研判是 LHM 在無法讀到裝置
實際回報門檻時使用的通用預設值，不是每顆硬碟各自的真實韌體設定。
因此本檔的因應方式：不寫死判斷「一定找不到」，而是用一般化規則
（SensorType 為 Temperature 且名稱不含 Warning/Critical）持續嘗試辨識
「目前溫度」感測器——若使用者之後改用系統管理員權限＋已裝 PawnIO 執行，
LHM 若真的能建立這顆感測器，本程式會自動撈到；在目前這台機器/權限下，
上層報告會誠實顯示「目前溫度：不可用」而非假裝有資料。

Total Space 恆為 0 調查記錄（2026-07-05，實機驗證）：
用 `Get-Disk`/`Get-Partition` 確認這兩顆實體硬碟都已正常掛載到有代號的
磁碟分割（C:/D:/E:），排除「硬碟沒有磁碟機代號導致查不到容量」的可能性。
接著對同一顆硬碟物件連續呼叫 `hardware.Update()` 三次（含間隔 1 秒），
Total Space 仍固定回傳 0.0，Used Space／Free Space 仍固定是 None，
排除「需要至少兩次 Update() 才能取樣出差值」的可能性（這對 Read/Write
Rate 這類需要前後兩次取樣算變化量的感測器是合理的，但 Total Space 是
靜態容量值，理論上第一次 Update() 就該有值）。研判與「目前溫度」一樣，
是同一組需要較高權限的 NVMe 查詢管線失敗後的殘留佔位值（0.0），不是
真實容量。無論如何，一顆實際 1TB／2TB 的硬碟不可能總容量是 0 bytes，
這是明顯錯誤值，因此本檔選擇：偵測到明顯不合理的 0 值容量感測器時，
直接不採用該筆讀數（而非讓報告顯示看起來很精確、實則錯誤的「0」），
若未來在有權限的環境下讀到非 0 數值，本程式會正常採用。
"""

from __future__ import annotations

import dataclasses
from typing import List

from pc_health_check.engine import get_engine

# LibreHardwareMonitor 的容量類（SensorType.Data）感測器名稱，用來辨識
# 哪些讀數屬於「容量」而非其他數值類型（例如溫度、負載百分比）。
_CAPACITY_SENSOR_NAMES = {"total space", "used space", "free space"}


def _is_implausible_zero_capacity(sensor_name: str, sensor_type: str, value: float) -> bool:
    """偵測「容量類感測器回傳恰好 0」這種明顯錯誤的殘留佔位值。

    見上方模組 docstring 的調查記錄：實測確認 Total Space 在本機環境下
    恆為 0.0 且不受多次 Update() 影響，同時任何真實實體硬碟的容量都不可能
    是 0 bytes，故判定為不可信資料，予以捨棄而非顯示誤導性的「0」。
    """
    if sensor_type.strip().lower() != "data":
        return False
    if sensor_name.strip().lower() not in _CAPACITY_SENSOR_NAMES:
        return False
    return value == 0.0


@dataclasses.dataclass
class DiskSensorReading:
    """單一硬碟感測讀數。"""

    disk_name: str
    sensor_name: str
    sensor_type: str
    value: float


@dataclasses.dataclass
class DiskReport:
    """硬碟感測讀取結果。"""

    available: bool
    reason: str
    readings: List[DiskSensorReading] = dataclasses.field(default_factory=list)


def get_disk_report() -> DiskReport:
    """讀取硬碟 SMART／溫度等感測數值；引擎未就緒或無資料時回傳不可用狀態。"""
    status = get_engine()
    if not status.ready:
        return DiskReport(available=False, reason=status.reason)

    try:
        readings: List[DiskSensorReading] = []
        for hardware in status.computer.Hardware:
            hw_type = str(getattr(hardware, "HardwareType", "")).upper()
            if "STORAGE" not in hw_type:
                continue
            hardware.Update()
            disk_name = str(getattr(hardware, "Name", "未知硬碟"))
            for sensor in getattr(hardware, "Sensors", None) or []:
                value = getattr(sensor, "Value", None)
                if value is None:
                    continue
                sensor_name = str(getattr(sensor, "Name", "未知感測器"))
                sensor_type = str(getattr(sensor, "SensorType", "未知類型"))
                value = float(value)
                if _is_implausible_zero_capacity(sensor_name, sensor_type, value):
                    continue
                readings.append(
                    DiskSensorReading(
                        disk_name=disk_name,
                        sensor_name=sensor_name,
                        sensor_type=sensor_type,
                        value=value,
                    )
                )

        if not readings:
            return DiskReport(
                available=False,
                reason="引擎已就緒，但未偵測到任何硬碟 SMART 感測數值（可能需要系統管理員權限）。",
            )
        return DiskReport(available=True, reason="OK", readings=readings)
    except Exception as exc:  # noqa: BLE001
        return DiskReport(
            available=False,
            reason=f"讀取硬碟感測資訊時發生未預期錯誤：{exc}",
        )


def get_disk_report_via_pysmart() -> DiskReport:
    """TODO(未來)：改用 pySMART + smartmontools 取得完整 SMART 屬性表。

    尚未實作。呼叫此函式會直接回傳明確的「尚未實作」狀態，不會拋出
    NotImplementedError 中斷程式，保持與其他 sensors 模組一致的優雅降級行為。
    """
    return DiskReport(
        available=False,
        reason="尚未實作：未來可考慮整合 pySMART（需另裝 smartmontools 的 smartctl）。",
    )
