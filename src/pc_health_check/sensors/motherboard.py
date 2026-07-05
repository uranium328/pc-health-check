"""主機板感測器讀取（溫度／電壓／風扇轉速），透過 LibreHardwareMonitor 引擎。

資料來源：engine.py 取得的 LibreHardwareMonitor `Computer` 物件下，
HardwareType 為 Motherboard／SuperIO 的硬體項目。若引擎未就緒（未安裝套件、
驅動、或無 admin 權限），回傳「不可用」狀態而非拋例外。

未驗證事項：LibreHardwareMonitor 的 HardwareType 列舉實際字串內容，尚未在
本機以真實安裝的套件驗證，此處以字串子集比對（大寫）降低對精確列舉值的
依賴，但仍可能與實際版本有出入。
"""

from __future__ import annotations

import dataclasses
from typing import List

from pc_health_check.engine import get_engine


@dataclasses.dataclass
class SensorReading:
    """單一感測器讀數（溫度／電壓／風扇轉速等）。"""

    name: str
    sensor_type: str
    value: float


@dataclasses.dataclass
class MotherboardReport:
    """主機板感測讀取結果。"""

    available: bool
    reason: str
    readings: List[SensorReading] = dataclasses.field(default_factory=list)


def get_motherboard_report() -> MotherboardReport:
    """讀取主機板溫度/電壓/風扇轉速；引擎未就緒時回傳不可用狀態而非拋例外。"""
    status = get_engine()
    if not status.ready:
        return MotherboardReport(available=False, reason=status.reason)

    try:
        readings: List[SensorReading] = []
        for hardware in status.computer.Hardware:
            hw_type = str(getattr(hardware, "HardwareType", "")).upper()
            if "MOTHERBOARD" not in hw_type and "SUPERIO" not in hw_type:
                continue
            hardware.Update()
            _collect_sensors(hardware, readings)
            for sub in getattr(hardware, "SubHardware", None) or []:
                sub.Update()
                _collect_sensors(sub, readings)

        if not readings:
            return MotherboardReport(
                available=False,
                reason="引擎已就緒，但未偵測到任何主機板感測器數值（可能需要系統管理員權限）。",
            )
        return MotherboardReport(available=True, reason="OK", readings=readings)
    except Exception as exc:  # noqa: BLE001 - 單一感測失敗不能讓整個模組崩潰
        return MotherboardReport(
            available=False,
            reason=f"讀取主機板感測器時發生未預期錯誤：{exc}",
        )


def _collect_sensors(hardware, readings: List[SensorReading]) -> None:
    """從一個 LHM 硬體物件收集其 Sensors 集合，忽略無值的感測器。"""
    for sensor in getattr(hardware, "Sensors", None) or []:
        value = getattr(sensor, "Value", None)
        if value is None:
            continue
        readings.append(
            SensorReading(
                name=str(getattr(sensor, "Name", "未知感測器")),
                sensor_type=str(getattr(sensor, "SensorType", "未知類型")),
                value=float(value),
            )
        )
