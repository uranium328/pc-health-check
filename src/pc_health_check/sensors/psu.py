"""電源供應器（PSU）資訊讀取骨架。

誠實標註：絕大多數 PSU **沒有**可供軟體讀取的健康／監控資訊——一般 PSU
不具備對外暴露感測資料的通訊介面。僅極少數「智慧型」PSU（例如部分
Corsair 系列，透過廠商專屬協定/Corsair Link）可能可讀電壓、功率、風扇
轉速等資訊，且該協定不在 LibreHardwareMonitor 的主流／穩定涵蓋範圍內，
支援與否隨裝置型號與 LHM 版本而異。

本骨架預設一律回傳「不支援/不可用」，即使引擎已就緒、即使掃描到疑似
PSU 硬體項目也會盡量誠實描述來源的不確定性，不假裝擁有可靠資料。
"""

from __future__ import annotations

import dataclasses
from typing import List

from pc_health_check.engine import get_engine


@dataclasses.dataclass
class PsuSensorReading:
    """單一 PSU 感測讀數（若能取得）。"""

    sensor_name: str
    sensor_type: str
    value: float


@dataclasses.dataclass
class PsuReport:
    """PSU 讀取結果。預設情況下 available 應為 False。"""

    available: bool
    reason: str
    readings: List[PsuSensorReading] = dataclasses.field(default_factory=list)


def get_psu_report() -> PsuReport:
    """嘗試透過 LibreHardwareMonitor 讀取 PSU 感測；預設情況下多半不可用。

    這是刻意保守的介面：找不到明確的 PSU 硬體項目時，直接回傳不可用，
    不推測、不假造數值。
    """
    status = get_engine()
    if not status.ready:
        return PsuReport(
            available=False,
            reason=(
                "感測引擎未就緒（"
                + status.reason
                + "）。且一般 PSU 本就無軟體可讀資訊，僅特定智慧型號可能支援。"
            ),
        )

    try:
        readings: List[PsuSensorReading] = []
        for hardware in status.computer.Hardware:
            hw_type = str(getattr(hardware, "HardwareType", "")).upper()
            if "PSU" not in hw_type:
                continue
            hardware.Update()
            for sensor in getattr(hardware, "Sensors", None) or []:
                value = getattr(sensor, "Value", None)
                if value is None:
                    continue
                readings.append(
                    PsuSensorReading(
                        sensor_name=str(getattr(sensor, "Name", "未知感測器")),
                        sensor_type=str(getattr(sensor, "SensorType", "未知類型")),
                        value=float(value),
                    )
                )

        if not readings:
            return PsuReport(
                available=False,
                reason=(
                    "未偵測到任何 PSU 感測裝置。一般 PSU 無軟體可讀資訊，"
                    "僅特定智慧型號（如部分 Corsair）可能可讀，且非本骨架保證支援。"
                ),
            )
        return PsuReport(available=True, reason="OK", readings=readings)
    except Exception as exc:  # noqa: BLE001
        return PsuReport(
            available=False,
            reason=f"讀取 PSU 感測資訊時發生未預期錯誤：{exc}",
        )
