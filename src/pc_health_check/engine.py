"""LibreHardwareMonitor 感測引擎的初始化與包裝層。

架構方案 A（已定案）：透過 `HardwareMonitor` PyPI 套件（其內部使用 pythonnet
綁定 LibreHardwareMonitorLib.dll）存取主機板、GPU、硬碟等硬體感測器。

鐵律：本模組只讀取硬體感測數值，不做任何寫入／設定變更操作。

若 `HardwareMonitor` 套件未安裝、pythonnet 載入失敗、或 LibreHardwareMonitor
所需的 PawnIO 核心驅動尚未安裝，本模組必須優雅降級為「未就緒」狀態並附上
原因說明，而不是讓 import 這個模組或呼叫 get_engine() 直接拋例外中斷全程式。

未驗證事項（誠實標註，非腦補）：
- pythonnet 在 Microsoft Store 版 Python 3.13 上載入原生 DLL 的相容性，
  尚未在本機實測（本機目前也未安裝 HardwareMonitor / pythonnet）。
- 下方 `Computer` 物件的 `IsXxxEnabled` 屬性名稱是依 LibreHardwareMonitor
  官方文件與常見範例慣例填寫，尚未在本機以真實安裝的套件驗證；若實際
  屬性名稱不同，初始化會在下方 try/except 中被攔截，回傳「未就緒」而不會
  讓程式崩潰。
"""

from __future__ import annotations

import dataclasses
from typing import Any, Optional


@dataclasses.dataclass
class EngineStatus:
    """描述 LibreHardwareMonitor 感測引擎目前的就緒狀態。"""

    ready: bool
    reason: str
    computer: Optional[Any] = None  # 就緒時為 HardwareMonitor.Hardware.Computer 實例


_engine_status: Optional[EngineStatus] = None


def get_engine() -> EngineStatus:
    """取得（並視需要初始化）LibreHardwareMonitor 引擎狀態。

    回傳：
        EngineStatus：ready=True 時 computer 欄位帶有可用的 Computer 物件；
        ready=False 時 reason 說明具體原因（缺套件／載入失敗／驅動未安裝等）。
        呼叫端（各 sensors 模組）應以此訊息告知使用者如何啟用，而不是讓
        例外往上炸穿整個程式。
    """
    global _engine_status

    if _engine_status is not None:
        return _engine_status

    try:
        # HardwareMonitor 套件在 import 時會透過 pythonnet 嘗試載入
        # LibreHardwareMonitorLib.dll。未安裝 HardwareMonitor 套件本身時，
        # 這裡是 ImportError；套件已裝但 DLL/驅動缺失時，可能是其他例外
        # （型別未知，一律用廣義 Exception 攔截）。
        from HardwareMonitor.Hardware import Computer  # type: ignore
    except ImportError as exc:
        _engine_status = EngineStatus(
            ready=False,
            reason=(
                "未安裝 'HardwareMonitor' 套件（或其相依的 pythonnet 無法載入）："
                f"{exc}。請先執行 `pip install -r requirements.txt`，並參考 "
                "docs/setup.md 安裝 PawnIO 驅動。"
            ),
        )
        return _engine_status
    except Exception as exc:  # noqa: BLE001 - 任何底層載入例外都要優雅降級，不得讓程式崩潰
        _engine_status = EngineStatus(
            ready=False,
            reason=f"載入 LibreHardwareMonitor 引擎時發生未預期錯誤：{exc}",
        )
        return _engine_status

    try:
        computer = Computer()
        # 以下屬性依 LibreHardwareMonitor 官方 API 慣例設定，僅啟用本專案
        # 會用到 LHM 的部分（CPU／主機板／GPU／硬碟）。記憶體改走 wmi
        # （見 sensors/memory.py），PSU 目前多數型號無感測來源。
        computer.IsCpuEnabled = True
        computer.IsMotherboardEnabled = True
        computer.IsGpuEnabled = True
        computer.IsStorageEnabled = True
        computer.Open()
    except Exception as exc:  # noqa: BLE001
        _engine_status = EngineStatus(
            ready=False,
            reason=(
                "LibreHardwareMonitor 引擎初始化失敗（可能是缺少 PawnIO 驅動、"
                f"或未以系統管理員權限執行本程式）：{exc}"
            ),
        )
        return _engine_status

    _engine_status = EngineStatus(ready=True, reason="OK", computer=computer)
    return _engine_status


def reset_engine() -> None:
    """重置快取的引擎狀態（供測試或想重新嘗試初始化時使用）。"""
    global _engine_status
    _engine_status = None
