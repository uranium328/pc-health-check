"""彙整各 sensors 模組的讀取結果為一份結構化健康報告。

鐵律：任何單一 sensor 模組（cpu/motherboard/memory/disk/psu/gpu）的非預期例外，
都必須在此被攔截並轉換為「不可用」項目，絕不能讓單一模組的例外導致整份
報告的產生失敗。
"""

from __future__ import annotations

import dataclasses
import datetime
from typing import Any, Callable, Dict


@dataclasses.dataclass
class ComponentStatus:
    """單一元件（主機板/記憶體/硬碟/PSU/GPU）在報告中的呈現狀態。"""

    name: str
    available: bool
    reason: str
    data: Any = None


@dataclasses.dataclass
class HealthReport:
    """整份硬體健康檢測報告。"""

    generated_at: str
    components: Dict[str, ComponentStatus] = dataclasses.field(default_factory=dict)


def _safe_collect(component_name: str, collector: Callable[[], Any]) -> ComponentStatus:
    """呼叫單一 sensor 模組的收集函式，並保證不會讓例外往外拋。"""
    try:
        result = collector()
        return ComponentStatus(
            name=component_name,
            available=bool(getattr(result, "available", False)),
            reason=str(getattr(result, "reason", "未知")),
            data=result,
        )
    except Exception as exc:  # noqa: BLE001 - 鐵律：單一模組失敗不能拖垮整份報告
        return ComponentStatus(
            name=component_name,
            available=False,
            reason=f"呼叫 {component_name} 感測模組時發生未預期例外：{exc}",
        )


def generate_report() -> HealthReport:
    """收集 CPU/主機板/記憶體/硬碟/PSU/GPU 六大類健康狀態，組成一份結構化報告。"""
    # 延後匯入 sensors 子模組：即使其中某個子模組在 import 期間就發生問題，
    # 也應該只影響該單一元件，不應該讓 report.py 本身無法被匯入。
    try:
        from pc_health_check.sensors import cpu
    except Exception as exc:  # noqa: BLE001
        cpu = None  # type: ignore
        cpu_import_error = exc
    else:
        cpu_import_error = None

    try:
        from pc_health_check.sensors import motherboard
    except Exception as exc:  # noqa: BLE001
        motherboard = None  # type: ignore
        motherboard_import_error = exc
    else:
        motherboard_import_error = None

    try:
        from pc_health_check.sensors import memory
    except Exception as exc:  # noqa: BLE001
        memory = None  # type: ignore
        memory_import_error = exc
    else:
        memory_import_error = None

    try:
        from pc_health_check.sensors import disk
    except Exception as exc:  # noqa: BLE001
        disk = None  # type: ignore
        disk_import_error = exc
    else:
        disk_import_error = None

    try:
        from pc_health_check.sensors import psu
    except Exception as exc:  # noqa: BLE001
        psu = None  # type: ignore
        psu_import_error = exc
    else:
        psu_import_error = None

    try:
        from pc_health_check.sensors import gpu
    except Exception as exc:  # noqa: BLE001
        gpu = None  # type: ignore
        gpu_import_error = exc
    else:
        gpu_import_error = None

    report = HealthReport(generated_at=datetime.datetime.now().isoformat())

    report.components["cpu"] = (
        _safe_collect("CPU", cpu.get_cpu_report)
        if cpu is not None
        else ComponentStatus(
            name="CPU",
            available=False,
            reason=f"無法匯入 cpu 感測模組：{cpu_import_error}",
        )
    )
    report.components["motherboard"] = (
        _safe_collect("主機板", motherboard.get_motherboard_report)
        if motherboard is not None
        else ComponentStatus(
            name="主機板",
            available=False,
            reason=f"無法匯入 motherboard 感測模組：{motherboard_import_error}",
        )
    )
    report.components["memory"] = (
        _safe_collect("記憶體", memory.get_memory_report)
        if memory is not None
        else ComponentStatus(
            name="記憶體",
            available=False,
            reason=f"無法匯入 memory 感測模組：{memory_import_error}",
        )
    )
    report.components["disk"] = (
        _safe_collect("硬碟", disk.get_disk_report)
        if disk is not None
        else ComponentStatus(
            name="硬碟",
            available=False,
            reason=f"無法匯入 disk 感測模組：{disk_import_error}",
        )
    )
    report.components["psu"] = (
        _safe_collect("電源供應器", psu.get_psu_report)
        if psu is not None
        else ComponentStatus(
            name="電源供應器",
            available=False,
            reason=f"無法匯入 psu 感測模組：{psu_import_error}",
        )
    )
    report.components["gpu"] = (
        _safe_collect("顯示卡", gpu.get_gpu_report)
        if gpu is not None
        else ComponentStatus(
            name="顯示卡",
            available=False,
            reason=f"無法匯入 gpu 感測模組：{gpu_import_error}",
        )
    )

    return report
