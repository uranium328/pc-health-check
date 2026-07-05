"""顯示卡溫度/使用率/顯存讀取。

主要路徑：透過 engine.py 的 LibreHardwareMonitor 感測（HardwareType 含
GPU 字樣，涵蓋 NVIDIA/AMD/Intel，實際列舉字串如 GpuNvidia/GpuAmd/GpuIntel
未在本機驗證，故以大寫子字串比對降低依賴）。

可選路徑：若已安裝 `nvidia-ml-py`（import 名稱為 `pynvml`），可額外取得
NVIDIA 專屬細節（此骨架示範讀取溫度）。找不到 NVML 函式庫、或系統上沒有
NVIDIA 裝置，都必須優雅降級，不得影響其他 GPU 資料（例如 AMD/Intel）的回報。
"""

from __future__ import annotations

import dataclasses
from typing import List

from pc_health_check.engine import get_engine


@dataclasses.dataclass
class GpuSensorReading:
    """單一 GPU 感測讀數。"""

    gpu_name: str
    sensor_name: str
    sensor_type: str
    value: float


@dataclasses.dataclass
class GpuReport:
    """GPU 感測讀取結果。

    `available`/`reason` 反映透過 LibreHardwareMonitor（或退而求其次由
    NVML 補上）取得的整體結果；`nvidia_detail_available`/`nvidia_detail_reason`
    則單獨描述可選的 NVML 補充資訊是否可用，兩者是分開追蹤的狀態。
    """

    available: bool
    reason: str
    readings: List[GpuSensorReading] = dataclasses.field(default_factory=list)
    nvidia_detail_available: bool = False
    nvidia_detail_reason: str = "尚未嘗試讀取"


def get_gpu_report() -> GpuReport:
    """讀取 GPU 感測數值（優先走 LibreHardwareMonitor，涵蓋多廠牌）。

    另外嘗試以可選套件 `nvidia-ml-py` 補充 NVIDIA 專屬細節；該補充動作
    本身完全獨立 try/except，失敗不影響本函式回傳的主要資料。
    """
    status = get_engine()
    if not status.ready:
        report = GpuReport(available=False, reason=status.reason)
    else:
        try:
            readings: List[GpuSensorReading] = []
            for hardware in status.computer.Hardware:
                hw_type = str(getattr(hardware, "HardwareType", "")).upper()
                if "GPU" not in hw_type:
                    continue
                hardware.Update()
                gpu_name = str(getattr(hardware, "Name", "未知顯示卡"))
                for sensor in getattr(hardware, "Sensors", None) or []:
                    value = getattr(sensor, "Value", None)
                    if value is None:
                        continue
                    readings.append(
                        GpuSensorReading(
                            gpu_name=gpu_name,
                            sensor_name=str(getattr(sensor, "Name", "未知感測器")),
                            sensor_type=str(getattr(sensor, "SensorType", "未知類型")),
                            value=float(value),
                        )
                    )

            if not readings:
                report = GpuReport(
                    available=False,
                    reason="引擎已就緒，但未偵測到任何 GPU 感測數值。",
                )
            else:
                report = GpuReport(available=True, reason="OK", readings=readings)
        except Exception as exc:  # noqa: BLE001
            report = GpuReport(
                available=False,
                reason=f"讀取 GPU 感測資訊時發生未預期錯誤：{exc}",
            )

    _try_enrich_with_nvml(report)
    return report


def _try_enrich_with_nvml(report: GpuReport) -> None:
    """可選：嘗試用 nvidia-ml-py（pynvml）補充 NVIDIA 專屬細節。

    任何失敗（未安裝、初始化失敗、無 NVIDIA 裝置、讀取失敗）都必須優雅
    降級，只更新 report 的 nvidia_detail_* 欄位，絕不拋出例外給呼叫端。
    """
    try:
        import pynvml  # type: ignore
    except ImportError as exc:
        report.nvidia_detail_available = False
        report.nvidia_detail_reason = f"未安裝 'nvidia-ml-py'（可選套件）：{exc}"
        return
    except Exception as exc:  # noqa: BLE001 - 匯入期任何非預期錯誤也要優雅降級
        report.nvidia_detail_available = False
        report.nvidia_detail_reason = f"匯入 'nvidia-ml-py' 時發生未預期錯誤：{exc}"
        return

    try:
        pynvml.nvmlInit()
    except Exception as exc:  # noqa: BLE001
        report.nvidia_detail_available = False
        report.nvidia_detail_reason = f"初始化 NVML 失敗（可能無 NVIDIA 裝置或驅動）：{exc}"
        return

    try:
        device_count = pynvml.nvmlDeviceGetCount()
        if device_count == 0:
            report.nvidia_detail_available = False
            report.nvidia_detail_reason = "未偵測到任何 NVIDIA 裝置。"
            return

        added = 0
        for index in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(index)
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode("utf-8", errors="replace")
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            report.readings.append(
                GpuSensorReading(
                    gpu_name=str(name),
                    sensor_name="NVML Temperature",
                    sensor_type="Temperature",
                    value=float(temp),
                )
            )
            added += 1

        report.nvidia_detail_available = True
        report.nvidia_detail_reason = "OK"
        if not report.available and added > 0:
            report.available = True
            report.reason = "LHM 感測不可用，但透過 nvidia-ml-py 取得部分 NVIDIA GPU 資訊。"
    except Exception as exc:  # noqa: BLE001
        report.nvidia_detail_available = False
        report.nvidia_detail_reason = f"讀取 NVML 資訊時發生未預期錯誤：{exc}"
    finally:
        try:
            pynvml.nvmlShutdown()
        except Exception:  # noqa: BLE001 - shutdown 失敗不應影響已收集到的資料
            pass
