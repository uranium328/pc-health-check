"""CPU 資訊讀取（型號/溫度/使用率/時脈），透過 LibreHardwareMonitor 引擎。

資料來源：engine.py 取得的 LibreHardwareMonitor `Computer` 物件下，
HardwareType 為 Cpu 的硬體項目（唯讀查詢：`.Update()` 後讀取 Sensors 集合，
不呼叫任何 Set/Write 類 API，符合本專案唯讀健康檢測鐵律）。

寫法比照 sensors/gpu.py：每一筆讀數都附帶所屬處理器名稱（`cpu_name`），
以支援多顆實體 CPU（例如工作站/伺服器等多路平台）的情境，即使絕大多數
消費級桌機/筆電只有一顆 CPU。本模組只負責「收集」CPU 底下所有有值的
感測器（溫度/負載/時脈/電壓/功耗等，只要 LHM 有回報就收），如何從中挑選
對一般使用者健康判讀有意義的欄位（package 溫度、CPU Total 使用率、最高
核心時脈）留給 health.py 的 `build_cpu_section` 處理，職責邊界與其他
sensors 模組一致。

未驗證事項（誠實標註，比照本專案其他 sensors 模組慣例，非腦補）：
- LibreHardwareMonitor 的 HardwareType 列舉在 CPU 項目上的實際字串內容
  （預期為 `Cpu`），尚未在本機以真實安裝的套件驗證，此處以字串子集比對
  （大寫）降低對精確列舉值的依賴，寫法與 motherboard.py/gpu.py 一致。
- CPU 感測器的實際命名（例如 `CPU Package`、`CPU Total`、`CPU Core #1`
  等）依 LibreHardwareMonitor 官方文件與社群常見範例慣例假設，尚未在本機
  以真實安裝的套件驗證；找不到預期名稱時，本模組仍會透過通用規則（只要
  `Value` 不是 None 就收集）盡量收集到可用讀數，篩選/挑選邏輯留給
  health.py，本模組本身不會因為找不到特定名稱就整體回報不可用。
"""

from __future__ import annotations

import dataclasses
from typing import List

from pc_health_check.engine import get_engine


@dataclasses.dataclass
class CpuSensorReading:
    """單一 CPU 感測讀數（溫度／負載／時脈等）。"""

    cpu_name: str
    sensor_name: str
    sensor_type: str
    value: float


@dataclasses.dataclass
class CpuReport:
    """CPU 感測讀取結果。"""

    available: bool
    reason: str
    readings: List[CpuSensorReading] = dataclasses.field(default_factory=list)


def get_cpu_report() -> CpuReport:
    """讀取 CPU 溫度/負載/時脈等感測數值；引擎未就緒時回傳不可用狀態而非拋例外。"""
    status = get_engine()
    if not status.ready:
        return CpuReport(available=False, reason=status.reason)

    try:
        readings: List[CpuSensorReading] = []
        for hardware in status.computer.Hardware:
            hw_type = str(getattr(hardware, "HardwareType", "")).upper()
            if "CPU" not in hw_type:
                continue
            hardware.Update()
            cpu_name = str(getattr(hardware, "Name", "未知處理器"))
            for sensor in getattr(hardware, "Sensors", None) or []:
                value = getattr(sensor, "Value", None)
                if value is None:
                    continue
                readings.append(
                    CpuSensorReading(
                        cpu_name=cpu_name,
                        sensor_name=str(getattr(sensor, "Name", "未知感測器")),
                        sensor_type=str(getattr(sensor, "SensorType", "未知類型")),
                        value=float(value),
                    )
                )

        if not readings:
            return CpuReport(
                available=False,
                reason="引擎已就緒，但未偵測到任何 CPU 感測數值（可能需要系統管理員權限）。",
            )
        return CpuReport(available=True, reason="OK", readings=readings)
    except Exception as exc:  # noqa: BLE001 - 單一感測失敗不能讓整個模組崩潰
        return CpuReport(
            available=False,
            reason=f"讀取 CPU 感測資訊時發生未預期錯誤：{exc}",
        )
