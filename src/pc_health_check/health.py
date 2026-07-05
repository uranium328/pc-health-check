"""健康判讀（正常/注意/警告）與「一般使用者看得懂」的顯示格式化邏輯。

職責邊界：本檔只負責把 `report.py` 收集到的原始 `ComponentStatus` 資料轉換成
友善的顯示文字與健康判讀，完全不做任何硬體存取或資料收集（資料一律由呼叫端
傳入），也不直接印出任何東西（印出交給 main.py）。

`THRESHOLDS` 集中收斂本檔用到的判讀門檻常數，方便使用者之後依自己需求調整；
這些數字只是骨架階段的合理預設值，不是醫療／工業級精確判斷。
"""

from __future__ import annotations

import dataclasses
import re
from typing import List, Optional, Sequence

NORMAL = "正常"
ATTENTION = "注意"
CRITICAL = "警告"

THRESHOLDS = {
    # 顯示卡核心溫度，攝氏度。
    # < attention_at 正常；attention_at ~ warning_at 之間注意；>= warning_at 警告。
    #
    # 選用「GPU Core」而非「GPU Hot Spot／記憶體接面溫度」作為代表溫度：
    # Core 溫度是消費級監控工具（工作管理員、MSI Afterburner、GPU-Z 預設頁）
    # 最常顯示、使用者最熟悉的「GPU 溫度」定義；Hot Spot/記憶體接面溫度是
    # 進階診斷用的核內熱點溫度差指標，對一般使用者的健康判讀而言，Core 溫度
    # 更直覺、也更能代表整體運作狀態。
    "gpu_core_temperature_c": {"attention_at": 80, "warning_at": 90},
    # CPU 代表溫度（優先取 Package，找不到時退而求其次採全核心平均），攝氏度。
    # 刻意不沿用上方 GPU 的 80/90 門檻：現代消費級 CPU（Intel/AMD）在多核心
    # 全負載下，Package 溫度來到 85~95°C 屬常見的正常運作範圍（廠商設計的
    # boost/turbo 演算法會主動頂到接近但不超過安全溫度上限運作），若套用
    # GPU 的 80°C 門檻，會讓大量健康、正常運作的 CPU 被誤判為「警告」。門檻
    # 改採較貼近 CPU 實際熱設計的參考值：多數現行 Intel/AMD 消費級處理器的
    # Tjmax／降頻保護點約落在 95~105°C 區間，因此以 95°C 作為「警告」門檻
    # （對應各家熱保護觸發點的保守下界），85°C 作為「注意」門檻。
    "cpu_package_temperature_c": {"attention_at": 85, "warning_at": 95},
}

# 風扇 0 RPM 時常見於「未啟動」或「低負載時暫停」（許多顯示卡/機殼風扇具備
# 零轉速待機設計），本身不代表故障，附加說明避免使用者誤以為風扇壞了。
_ZERO_FAN_NOTE = "（可能未啟動或低負載時暫停，非故障）"


@dataclasses.dataclass
class FriendlyItem:
    """一行「一般使用者看得懂」的顯示內容，附帶（若適用）健康判讀。"""

    text: str
    verdict: Optional[str] = None  # "正常"/"注意"/"警告"；None 代表本項不判讀


@dataclasses.dataclass
class FriendlyDevice:
    """單一硬體實例（例如一張顯示卡、一顆硬碟）的顯示內容。

    `name` 為 None 時代表這個元件類別不需要依硬體實例分組顯示（例如記憶體／
    電源供應器／主機板一律彙整成一個區塊）。
    """

    name: Optional[str]
    items: List[FriendlyItem] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class FriendlySection:
    """單一元件類別（顯示卡/硬碟/記憶體/電源供應器/主機板）在報告中的顯示。"""

    title: str
    available: bool
    unavailable_reason: str = ""
    devices: List[FriendlyDevice] = dataclasses.field(default_factory=list)

    def verdicts(self) -> List[str]:
        return [item.verdict for device in self.devices for item in device.items if item.verdict]


def _temperature_verdict(value_c: float, attention_at: float, warning_at: float) -> str:
    if value_c >= warning_at:
        return CRITICAL
    if value_c >= attention_at:
        return ATTENTION
    return NORMAL


def verdict_gpu_temperature(value_c: float) -> str:
    """GPU 核心溫度判讀，門檻見 `THRESHOLDS["gpu_core_temperature_c"]`。"""
    t = THRESHOLDS["gpu_core_temperature_c"]
    return _temperature_verdict(value_c, t["attention_at"], t["warning_at"])


def verdict_cpu_temperature(value_c: float) -> str:
    """CPU 代表溫度（優先 Package，找不到時為全核心平均）判讀，
    門檻見 `THRESHOLDS["cpu_package_temperature_c"]`。"""
    t = THRESHOLDS["cpu_package_temperature_c"]
    return _temperature_verdict(value_c, t["attention_at"], t["warning_at"])


def verdict_disk_temperature(
    value_c: float, warning_c: Optional[float], critical_c: Optional[float]
) -> Optional[str]:
    """用硬碟自己回報的 Warning/Critical 門檻值判讀目前溫度。

    沒有門檻值可用時，回傳 None（呼叫端只顯示數值，不做判讀），避免套用與
    這顆硬碟無關的通用門檻。
    """
    if warning_c is None or critical_c is None:
        return None
    return _temperature_verdict(value_c, warning_c, critical_c)


def _find(readings: Sequence, **filters):
    """從一組感測讀數中找出符合所有條件的第一筆，找不到回傳 None。

    支援的篩選鍵：
      sensor_type：精確比對 `sensor_type` 欄位。
      sensor_name：精確比對感測器名稱欄位（GPU/硬碟用 `sensor_name`，
                   主機板用 `name`，這裡統一以 `sensor_name` 呼叫，由
                   呼叫端在讀入前正規化欄位名稱）。
      name_contains：名稱（小寫）需包含此子字串。
      name_excludes：名稱（小寫）不得包含此序列中的任何子字串。
    """
    sensor_type = filters.get("sensor_type")
    sensor_name = filters.get("sensor_name")
    name_contains = filters.get("name_contains")
    name_excludes = filters.get("name_excludes") or ()
    for r in readings:
        if sensor_type is not None and r.sensor_type != sensor_type:
            continue
        if sensor_name is not None and r.sensor_name != sensor_name:
            continue
        lower_name = r.sensor_name.lower()
        if name_contains is not None and name_contains.lower() not in lower_name:
            continue
        if any(bad.lower() in lower_name for bad in name_excludes):
            continue
        return r
    return None


def _find_all(readings: Sequence, *, sensor_type: Optional[str] = None) -> List:
    return [r for r in readings if sensor_type is None or r.sensor_type == sensor_type]


def _core_sort_key(reading):
    """依 sensor_name 內的核心編號數字排序，而非字典序（避免核心數達兩位數時
    出現 "Core #10" 排在 "Core #2" 前面的錯亂顯示）。找不到數字則排到最後。"""
    match = re.search(r"\d+", reading.sensor_name)
    return (int(match.group()) if match else float("inf"), reading.sensor_name)


def build_cpu_section(status) -> FriendlySection:
    """組出 CPU 的友善顯示區塊。

    溫度：優先採 Package（sensor_name 含 "package"）作為代表溫度並套用
    `verdict_cpu_temperature` 判讀；這個環境/版本的 LHM 若沒有建立 Package
    感測器，退而求其次改採全部 Core 溫度（sensor_name 含 "core"）的平均值，
    同樣套用判讀（見 THRESHOLDS 註解，門檻不沿用 GPU 那組）。無論代表溫度
    是否成功取得，只要偵測到一顆以上的 per-core 溫度，都會在代表溫度下方
    額外逐一列出，供想看細節的使用者參考（不重複判讀，只顯示數值）。

    使用率：採 "CPU Total" 這類 sensor_name 含 "total" 的 Load 感測器；找不到
    則不顯示（不臆測，比照其他模組的誠實降級慣例）。不做健康判讀——高使用率
    本身不代表故障，這點與 GPU 使用率的處理方式一致。

    時脈：多核心 CPU 沒有單一「代表時脈」，這裡取所有 Clock 類讀數中數值
    最高者（通常對應目前 turbo/boost 中的核心），排除名稱含 "bus" 的匯流排
    時脈（那是參考基準頻率，不是核心運作時脈）。同樣不做健康判讀，只是
    提供資訊。
    """
    title = "CPU"
    if not status.available:
        return FriendlySection(title=title, available=False, unavailable_reason=status.reason)

    readings = list(getattr(status.data, "readings", None) or [])
    if not readings:
        return FriendlySection(title=title, available=False, unavailable_reason=status.reason)

    cpu_names: List[str] = []
    for r in readings:
        if r.cpu_name not in cpu_names:
            cpu_names.append(r.cpu_name)

    devices: List[FriendlyDevice] = []
    for cpu_name in cpu_names:
        cpu_readings = [r for r in readings if r.cpu_name == cpu_name]
        items: List[FriendlyItem] = []

        package_temp = _find(cpu_readings, sensor_type="Temperature", name_contains="package")
        core_temps = [
            r
            for r in _find_all(cpu_readings, sensor_type="Temperature")
            if "core" in r.sensor_name.lower() and re.search(r"#\d+$", r.sensor_name)
        ]

        primary_label = "溫度"
        primary_value = None
        if package_temp is not None:
            primary_value = package_temp.value
        elif core_temps:
            primary_label = "溫度（核心平均）"
            primary_value = sum(r.value for r in core_temps) / len(core_temps)

        if primary_value is not None:
            v = verdict_cpu_temperature(primary_value)
            items.append(FriendlyItem(text=f"{primary_label}：{primary_value:.0f}°C（{v}）", verdict=v))
        else:
            items.append(
                FriendlyItem(
                    text=(
                        "溫度：不可用（此環境可能需要系統管理員權限，"
                        "並安裝 PawnIO 驅動；見 docs/setup.md）"
                    )
                )
            )

        for core in sorted(core_temps, key=_core_sort_key):
            items.append(FriendlyItem(text=f"{core.sensor_name}：{core.value:.0f}°C"))

        total_load = _find(cpu_readings, sensor_type="Load", name_contains="total")
        if total_load is not None:
            items.append(FriendlyItem(text=f"使用率：{total_load.value:.0f}%"))

        clocks = [r for r in _find_all(cpu_readings, sensor_type="Clock") if "bus" not in r.sensor_name.lower()]
        if clocks:
            fastest = max(clocks, key=lambda r: r.value)
            items.append(
                FriendlyItem(text=f"目前時脈：{fastest.value:.0f} MHz（{fastest.sensor_name}，各核心中最高者）")
            )

        devices.append(FriendlyDevice(name=cpu_name, items=items))

    return FriendlySection(title=title, available=True, devices=devices)


def build_gpu_section(status) -> FriendlySection:
    """組出顯示卡的友善顯示區塊。

    只挑對健康判讀有意義的指標：溫度（GPU Core）、使用率（GPU Core 負載）、
    風扇轉速（Fan 類型，不含代表風扇 PWM 控制訊號的 Control 類型）、電壓
    （Voltage 類型）。不顯示時脈、功耗、D3D 各項引擎負載、PCIe 吞吐量、
    顯存用量等對一般使用者的健康判讀沒有直接意義的底層效能計數器——這些
    原始資料在 `--detail` 模式仍會完整顯示。
    """
    title = "顯示卡"
    if not status.available:
        return FriendlySection(title=title, available=False, unavailable_reason=status.reason)

    readings = list(getattr(status.data, "readings", None) or [])
    if not readings:
        return FriendlySection(title=title, available=False, unavailable_reason=status.reason)

    gpu_names: List[str] = []
    for r in readings:
        if r.gpu_name not in gpu_names:
            gpu_names.append(r.gpu_name)

    devices: List[FriendlyDevice] = []
    for gpu_name in gpu_names:
        gpu_readings = [r for r in readings if r.gpu_name == gpu_name]
        items: List[FriendlyItem] = []

        core_temp = _find(gpu_readings, sensor_name="GPU Core", sensor_type="Temperature")
        if core_temp is not None:
            v = verdict_gpu_temperature(core_temp.value)
            items.append(FriendlyItem(text=f"溫度：{core_temp.value:.0f}°C（{v}）", verdict=v))

        core_load = _find(gpu_readings, sensor_name="GPU Core", sensor_type="Load")
        if core_load is not None:
            items.append(FriendlyItem(text=f"使用率：{core_load.value:.0f}%"))

        for fan in _find_all(gpu_readings, sensor_type="Fan"):
            suffix = _ZERO_FAN_NOTE if fan.value == 0 else ""
            items.append(FriendlyItem(text=f"{fan.sensor_name}：{fan.value:.0f} RPM{suffix}"))

        for volt in _find_all(gpu_readings, sensor_type="Voltage"):
            items.append(FriendlyItem(text=f"電壓：{volt.value:.2f} V"))

        devices.append(FriendlyDevice(name=gpu_name, items=items))

    return FriendlySection(title=title, available=True, devices=devices)


def build_disk_section(status) -> FriendlySection:
    """組出硬碟的友善顯示區塊。

    同時呈現「目前溫度」（若這個環境/權限下 LHM 有提供）與「廠商警告/臨界
    門檻」，兩者不混淆；容量僅在有可信的 Total Space 讀數時才顯示（見
    sensors/disk.py 模組 docstring 的調查記錄：本機此讀數恆為不可信的 0，
    已在 sensors 層濾除，不會出現在這裡）。
    """
    title = "硬碟"
    if not status.available:
        return FriendlySection(title=title, available=False, unavailable_reason=status.reason)

    readings = list(getattr(status.data, "readings", None) or [])
    if not readings:
        return FriendlySection(title=title, available=False, unavailable_reason=status.reason)

    disk_names: List[str] = []
    for r in readings:
        if r.disk_name not in disk_names:
            disk_names.append(r.disk_name)

    devices: List[FriendlyDevice] = []
    for disk_name in disk_names:
        disk_readings = [r for r in readings if r.disk_name == disk_name]
        items: List[FriendlyItem] = []

        warning = _find(disk_readings, sensor_type="Temperature", name_contains="warning")
        critical = _find(disk_readings, sensor_type="Temperature", name_contains="critical")
        current = _find(
            disk_readings,
            sensor_type="Temperature",
            name_excludes=("warning", "critical"),
        )

        if current is not None:
            v = verdict_disk_temperature(
                current.value,
                warning.value if warning is not None else None,
                critical.value if critical is not None else None,
            )
            verdict_text = f"（{v}）" if v else ""
            items.append(FriendlyItem(text=f"目前溫度：{current.value:.0f}°C{verdict_text}", verdict=v))
        else:
            items.append(
                FriendlyItem(
                    text=(
                        "目前溫度：不可用（此環境可能需要系統管理員權限，"
                        "並安裝 PawnIO 驅動；見 docs/setup.md）"
                    )
                )
            )

        if warning is not None and critical is not None:
            # 誠實標註：LibreHardwareMonitor 在讀不到硬碟真實韌體門檻時，
            # 會回退成一組通用預設值（實測本機兩顆不同品牌/型號的硬碟
            # 門檻完全相同，即為此通用預設值，非各碟真實韌體設定），
            # 因此不能標成「廠商」門檻，避免誤導使用者。
            items.append(
                FriendlyItem(
                    text=(
                        f"參考溫度門檻：注意 {warning.value:.0f}°C／警告 {critical.value:.0f}°C"
                        "（此為監控工具的通用預設值，未必是這顆硬碟真實韌體設定的門檻）"
                    )
                )
            )

        total = _find(disk_readings, sensor_name="Total Space", sensor_type="Data")
        used = _find(disk_readings, sensor_name="Used Space")
        free = _find(disk_readings, sensor_name="Free Space")
        if total is not None:
            # 容量單位假設：依 LibreHardwareMonitor 慣例，SensorType.Data = GB。
            # 尚未能以本機真實非零數值驗證（這顆感測器目前恆為前述調查記錄中
            # 的不可信 0 值，已在 sensors 層濾除）；若之後在有權限的環境下
            # 讀到非 0 數值，建議覆核這個單位假設是否正確。
            line = f"總容量：約 {total.value:.0f} GB"
            if used is not None:
                line += f"（已用 {used.value:.0f} GB）"
            elif free is not None:
                line += f"（剩餘 {free.value:.0f} GB）"
            items.append(FriendlyItem(text=line))

        devices.append(FriendlyDevice(name=disk_name, items=items))

    return FriendlySection(title=title, available=True, devices=devices)


def build_memory_section(status) -> FriendlySection:
    """組出記憶體的友善顯示區塊。

    誠實標註：消費級 RAM 沒有健康度可讀，此區塊只顯示庫存資訊（容量/頻率/
    型號/插槽），不做任何健康判讀（沿用 sensors/memory.py 既有的誠實標註
    邏輯）。PartNumber 若被偵測為無效/損壞資料，會顯示「未提供」而不是亂碼
    （見 sensors/memory.py 的 `_clean_part_number` 與模組 docstring）。
    """
    title = "記憶體"
    if not status.available:
        return FriendlySection(title=title, available=False, unavailable_reason=status.reason)

    modules = list(getattr(status.data, "modules", None) or [])
    if not modules:
        return FriendlySection(title=title, available=False, unavailable_reason=status.reason)

    total_gb = sum(m.capacity_bytes for m in modules) / (1024**3)
    items: List[FriendlyItem] = [
        FriendlyItem(
            text=(
                f"共 {len(modules)} 條，總容量約 {total_gb:.0f} GB"
                "（消費級記憶體無可讀健康度指標，以下僅為庫存資訊，不代表健康狀態）"
            )
        )
    ]
    for m in modules:
        gb = m.capacity_bytes / (1024**3)
        items.append(
            FriendlyItem(
                text=(
                    f"- {m.device_locator}：{m.manufacturer}，{gb:.0f} GB，"
                    f"{m.speed_mhz} MHz，型號：{m.part_number}"
                )
            )
        )

    return FriendlySection(title=title, available=True, devices=[FriendlyDevice(name=None, items=items)])


def build_psu_section(status) -> FriendlySection:
    """組出電源供應器的友善顯示區塊，沿用既有誠實標註邏輯（不硬湊判讀）。"""
    title = "電源供應器"
    if not status.available:
        return FriendlySection(title=title, available=False, unavailable_reason=status.reason)

    readings = list(getattr(status.data, "readings", None) or [])
    if not readings:
        return FriendlySection(
            title=title, available=False, unavailable_reason="未偵測到任何可用讀數。"
        )

    items = [FriendlyItem(text=f"{r.sensor_name}：{r.value:.2f}") for r in readings]
    return FriendlySection(title=title, available=True, devices=[FriendlyDevice(name=None, items=items)])


# 主機板感測器的常見單位對照。主機板晶片/風扇的合理「危險」門檻因板廠、
# 晶片組而異，本專案骨架階段尚無可靠的通用門檻依據（不像 GPU/硬碟有廠商
# 提供或消費級工具慣用的參考值），因此刻意不對主機板讀數做健康判讀，只
# 誠實顯示數值＋單位，避免用沒有根據的門檻誤導使用者。
_MOTHERBOARD_UNIT_BY_SENSOR_TYPE = {
    "Temperature": "°C",
    "Voltage": "V",
    "Fan": " RPM",
    "Load": "%",
    "Control": "%",
}


def build_motherboard_section(status) -> FriendlySection:
    """組出主機板的友善顯示區塊；刻意不做健康判讀，理由見上方常數註解。"""
    title = "主機板"
    if not status.available:
        return FriendlySection(title=title, available=False, unavailable_reason=status.reason)

    readings = list(getattr(status.data, "readings", None) or [])
    if not readings:
        return FriendlySection(
            title=title, available=False, unavailable_reason="未偵測到任何可用讀數。"
        )

    items = []
    for r in readings:
        unit = _MOTHERBOARD_UNIT_BY_SENSOR_TYPE.get(r.sensor_type, "")
        items.append(FriendlyItem(text=f"{r.name}：{r.value:.2f}{unit}"))
    return FriendlySection(title=title, available=True, devices=[FriendlyDevice(name=None, items=items)])


def overall_summary(sections: Sequence[FriendlySection]) -> str:
    """彙整所有區塊的判讀結果為單行整體摘要。

    規則：任一項「警告」→ 整體警告；沒有警告但有「注意」→ 整體注意；否則
    正常。項目本身不可用/無法讀取不影響整體判讀（`verdicts()` 本就不會納入
    沒有判讀結果的項目）。
    """
    all_verdicts = [v for section in sections for v in section.verdicts()]
    critical_count = all_verdicts.count(CRITICAL)
    attention_count = all_verdicts.count(ATTENTION)
    if critical_count:
        return f"整體狀況：有 {critical_count} 項警告"
    if attention_count:
        return f"整體狀況：有 {attention_count} 項需要{ATTENTION}"
    return f"整體狀況：{NORMAL}"
