# 電腦硬體健康檢測系統 — 架構選型研究筆記

> 產出日期：2026-07-04
> 性質：技術選型研究（**非**實作、非最終決策）。所有結論附來源；查不到／不確定／來源衝突處一律明確標註。
> 鐵律前提：**唯讀健康檢測**。不得實作或建議任何修改韌體、BIOS/UEFI、磁碟分割、驅動程式的操作；系統層級讀取（如 WMI）只用唯讀查詢。目標 OS：Windows 11 Pro（10.0.26200）。

---

## 0. 本機環境查證結果（實查，非猜測）

| 項目 | 查證結果 | 指令／來源 |
|---|---|---|
| Python | **3.13.14**，且為 **Microsoft Store 版**（site-packages 路徑含 `PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0`） | `python --version` / `pip --version` 實跑 |
| pip | **26.1.2** | `pip --version` 實跑 |
| 目前 shell 管理員權限 | **否（IsAdmin: False）** | `[Security.Principal.WindowsPrincipal]::IsInRole(Administrator)` 實跑 |
| LibreHardwareMonitor 安裝痕跡 | **未發現**（Program Files / (x86) 皆無） | `Test-Path` 實查 |
| OpenHardwareMonitor 安裝痕跡 | **未發現** | 同上 |
| HWiNFO 安裝痕跡 | **未發現** | 同上 |
| smartmontools 安裝痕跡 | **未發現** | 同上 |
| `root\LibreHardwareMonitor` WMI 命名空間 | **不存在**（LHM 未在跑，故無 WMI 資料源） | `Get-CimInstance -Namespace root\LibreHardwareMonitor` 實查 |
| `root\OpenHardwareMonitor` WMI 命名空間 | **不存在** | 同上 |

**環境層級重要提醒（影響方案可行性）：**

1. **目前 shell 非 admin**。下述多數感測讀取（SMART、WMI thermal zone、LHM 底層感測）**需要以系統管理員身分執行**，本工具日後實跑時必須提權，否則資料殘缺。
2. **Python 是 MS Store 版**。MS Store Python 有檔案系統重定向／沙箱特性，對需要載入原生 `.dll`（如 pythonnet 載入 `LibreHardwareMonitorLib.dll`）或安裝核心驅動的方案，**相容性我未在本機實測，標記為未查證**。若走方案 A/C，建議先在本機做一次 pythonnet 載入 DLL 的煙霧測試，或改用官方 python.org 版本以降低不確定性。

---

## 1. 逐一函式庫／方法查證

> 標示規則：✅ 活躍維護；⚠️ 有風險／有前提；❌ 已停更／不建議；🔒 需 admin；🧩 需額外安裝背景元件或驅動。

### 1.1 原生 WMI 路線：`wmi` + `pywin32`

| 項目 | 結論 | 來源 |
|---|---|---|
| `WMI`（PyPI 套件，Tim Golden） | 版本 **1.5.1**，發布 **2020-04-28**。是 pywin32 之上的輕量包裝。**⚠️ 疑似停更**（最後釋出 2020，文件僅測到 Python 2.5–3.4） | https://pypi.org/project/WMI/ |
| `pywin32`（win32com 提供 WMI 存取底層） | 為 `wmi` 套件相依，Windows 上長期標準 bindings。**注意：我未逐一查證 pywin32 目前最新版本／釋出日期**，僅確認其為 `wmi` 的相依，標記為**未逐一查證**。 | （未 fetch pywin32 頁面） |
| WMI 能拿到什麼「健康」資訊 | 主機板真感測（溫度／電壓／風扇）**基本拿不到**。`MSAcpi_ThermalZoneTemperature`（`root\WMI`）**需 admin**、回傳的是 ACPI 熱區（主機板某區域）**非** CPU 核心溫度，桌機／VM 常回「Unsupported」或不可靠。 | https://learn.microsoft.com/en-us/windows/win32/cimwin32prov | ； https://wutils.com/wmi/root/wmi/msacpi_thermalzonetemperature/ |

**結論：** `wmi`/`pywin32` 適合拿**庫存／靜態資訊**（見 RAM、GPU 型號、硬碟預測布林），但**不是**主機板／CPU/GPU 真感測的可靠來源。且核心套件 `wmi` 疑似停更（但 API 穩定、仍廣泛使用）。

### 1.2 `psutil`（跨平台系統資訊）

| 項目 | 結論 | 來源 |
|---|---|---|
| 版本／維護 | **7.2.2**，發布 **2026-01-28**，✅ 活躍維護 | https://pypi.org/project/psutil/ |
| Windows 上的感測支援 | **關鍵：`sensors_temperatures()` 與 `sensors_fans()` 在 Windows 上不可用**——這兩個函式僅 Linux（部分 FreeBSD），在 Windows 呼叫會 `AttributeError: module 'psutil' has no attribute 'sensors_temperatures'`（多個 issue 證實：#1271/#1280/#1718/#2309）。`sensors_battery()` **在 Windows 可用**。 | https://github.com/giampaolo/psutil/issues/1718 ； https://github.com/giampaolo/psutil/issues/2309 |
| Windows 上實際能拿到 | CPU 使用率、記憶體用量、磁碟用量／IO、網路、電池狀態、開機時間等。**溫度／風扇／電壓拿不到。** | 同上 |

**結論：** psutil 只能當「系統負載／用量」的輔助層，**不能**當硬體健康感測主力。不要因為它跨平台就高估其在 Windows 的硬體健康覆蓋。

### 1.3 硬碟 SMART：`pySMART` + smartmontools

| 項目 | 結論 | 來源 |
|---|---|---|
| `pySMART` 版本／維護 | **1.4.3**，發布 **2026-06-01**，✅ 活躍維護（維護者 MHerndon、ralequi） | https://pypi.org/project/pySMART/ |
| 相依 | **🧩 需另裝 smartmontools**（實際幹活的是 `smartctl`）。pySMART 只是包裝器。 | 同上（"only external dependency is the smartctl component of smartmontools"） |
| Windows 相容 | ✅ 官方宣稱相容 Linux/Windows/FreeBSD | 同上 |
| 權限 | **🔒 強烈建議 admin**：非提權下 smartctl 無法正確辨識所有裝置類型或解析全部 SMART 資訊。 | 同上 |
| 唯讀性 | smartctl 讀 SMART 屬性為唯讀查詢，符合鐵律（不要用它的 self-test 觸發等寫入型子命令即可）。 | — |

**替代（免裝 smartmontools 的較弱路線）：** WMI `MSStorageDriver_FailurePredictStatus`（`root\WMI`）只給「是否預測失效」布林 + 少量 vendor-specific 資料，**遠不如** smartctl 的完整屬性（重配置磁區數、通電時數、溫度、寫入量等）。標記為可行但資訊量低。

### 1.4 GPU

| 方案 | 結論 | 來源 |
|---|---|---|
| `nvidia-ml-py`（NVML 官方 bindings） | 版本 **13.610.43**，發布 **2026-06-01**，NVIDIA 官方維護。**僅 NVIDIA**。可拿溫度、使用率、顯存、功耗、風扇、（部分卡）ECC 記憶體錯誤計數。✅ 活躍。 | https://pypi.org/project/nvidia-ml-py/ |
| `GPUtil` | 版本 **1.4.0**，發布 **2018-12-18**，**❌ 已停更 5+ 年**，且只是包 `nvidia-smi`。**不建議採用**，NVIDIA 需求直接用 `nvidia-ml-py`。 | https://pypi.org/project/GPUtil/ |
| `pyadl`（AMD/ATI ADL 包裝，nicolargo） | 最後更新約 **2017-12**，**⚠️ 疑似停更**。僅 AMD。可拿溫度／風扇／時脈／使用率。 | https://github.com/nicolargo/pyadl ； https://pypi.org/project/pyadl/ |
| WMI `Win32_VideoController` | 僅型號、驅動版本、`AdapterRAM`（顯存，且 >4GB 常被截斷失準），**無溫度／無健康**。 | https://learn.microsoft.com/en-us/windows/win32/cimwin32prov |
| **LibreHardwareMonitor（統一 GPU 感測）** | 覆蓋 **NVIDIA / AMD / Intel** GPU 溫度、負載、顯存、風扇——見 1.6。**唯一能一套覆蓋三家的活躍方案。** | 見 1.6 |

**結論：** GPU 沒有單一跨廠商純 Python 活躍套件。NVIDIA 用 `nvidia-ml-py`；AMD 的 `pyadl` 已老；要一次覆蓋 NVIDIA/AMD/Intel，實務上要靠 **LibreHardwareMonitor**。

### 1.5 記憶體 RAM（誠實反映：消費級拿不到「健康度」）

| 能拿到 | 方法 | 來源 |
|---|---|---|
| 容量、設定時脈(MHz)、製造商、料號、Bank/通道、Form Factor | WMI `Win32_PhysicalMemory`（逐條 DIMM）。注意 `ConfiguredClockSpeed` 在 Win10/Server2016 前不支援。 | https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-physicalmemory ； https://powershell.one/wmi/root/cimv2/win32_physicalmemory |
| 是否具 ECC / 錯誤更正型別 | WMI `Win32_PhysicalMemoryArray.MemoryErrorCorrection`：`None(3)`, `Parity(4)`, `Single-bit ECC(5)`, `Multi-bit ECC(6)`, `CRC(7)` 等。 | https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-physicalmemoryarray |

**誠實標註（不可美化）：** 消費級（非 ECC）RAM **沒有**軟體可讀的「健康度百分比」或即時錯誤計數。上述 WMI 只能拿**靜態庫存/規格**與 ECC **型別宣告**，拿不到即時位元錯誤。真正的 ECC 錯誤事件要 ECC 硬體 + 平台（伺服器級 IPMI/EDAC 之類）才可能有，一般 Windows 桌機環境**不可得**。RAM 這一類在報告中只能定位為「規格盤點 + 是否 ECC」，不要宣稱能做記憶體健康診斷。（若要做壓力測試找錯誤，那屬於寫入/主動測試，超出「唯讀健康檢測」定位，本工具不做。）

### 1.6 LibreHardwareMonitor（LHM）— 主機板／多廠商感測的核心

| 項目 | 結論 | 來源 |
|---|---|---|
| 版本／維護 | **v0.9.6**，發布 **2026-02-14**，8.6k stars，1,508 commits，✅ **活躍維護** | https://github.com/LibreHardwareMonitor/LibreHardwareMonitor |
| 授權 | **MPL 2.0**（部分元件另有條款，見 THIRD-PARTY-NOTICES） | 同上 |
| 支援硬體 | 主機板、Intel/AMD CPU、**NVIDIA/AMD/Intel GPU**、HDD/SSD/NVMe（含 SMART）、網卡。程式碼含 `IsPowerMonitorEnabled`（對部分電源/PSU 有監控能力，見 1.7） | 同上 |
| 權限 | **🔒 部分感測需 admin** | 同上 |
| 底層驅動 | **🧩 新版對許多主機板系統感測需安裝 `PawnIO` 驅動**（`winget install PawnIO`）；LHM 歷史上亦使用核心層 ring0 驅動做低階存取。**此點對鐵律是灰色地帶，見第 3 節風險。** | https://pypi.org/project/HardwareMonitor/ |

**Python 接法有兩種（都查證過）：**

- **(a) WMI bridge：** LHM 執行時會把感測發布到 `root\LibreHardwareMonitor` 命名空間（`Sensor` 類，欄位 `Name/SensorType/Value/Parent`），Python 用 `wmi`/`pywin32` 查詢即可。**前提：LHM app 必須在背景執行。** 本機目前該命名空間不存在（LHM 沒裝/沒跑）。 | 來源：https://metricshub.com/docs/0.9.04/connectors/librehardwaremonitor.html ；https://hassagent.readthedocs.io/en/latest/wmi-examples/
- **(b) 直接載入 DLL（推薦）：** 用現成 PyPI 套件 **`HardwareMonitor`**（GitHub: snip3rnick/PyHardwareMonitor），它以 **pythonnet** 載入 `LibreHardwareMonitorLib.dll`，在**同一個 Python 進程內**直接讀感測，**不必開 LHM GUI app**。版本 **1.2.1 / 2026-06-07**，✅ 活躍。**🔒 需 admin**；**🧩 主機板感測需 PawnIO**。 | 來源：https://pypi.org/project/HardwareMonitor/ ；https://github.com/snip3rnick/PyHardwareMonitor
- 另有 PyPI 套件 `PyLibreHardwareMonitorLib`（同類替代），**我未逐一查證其版本/維護狀態，標記未查證**。 | 來源（僅列出、未深入）：https://pypi.org/project/PyLibreHardwareMonitorLib/

### 1.7 電源供應器 PSU（誠實反映：多數無法讀）

**誠實標註（不可硬湊）：** 一般／消費級 PSU **沒有**任何軟體可讀的健康或電力資訊——它們沒有對外資料介面。**只有「智慧型/數位 PSU」**（具 USB 監控介面者）才可讀電壓、電流、溫度、效率。目前明確可讀的主要是 **Corsair 的 i 系列**：

| 方案 | 結論 | 來源 |
|---|---|---|
| `liquidctl` | v **1.16.0 / 2026-03-03**，GPL-3.0，✅ 活躍。可讀 Corsair PSU 狀態：**HXi 系列**（HX750i/850i/1000i/1200i/1500i、ATX3.1 HX1200i）、**RMi 系列**（RM650i/750i/850i/1000i）。Windows 支援。 | https://github.com/liquidctl/liquidctl |
| ⚠️ liquidctl 的鐵律風險 | **liquidctl 是「控制」工具**，能設定風扇/幫浦轉速/燈光（寫入型）。本工具若採用，**只能呼叫其 `status`/讀取子集**，嚴禁呼叫任何 `set`/初始化寫入命令，否則直接違反唯讀鐵律。 | 同上 |
| LHM 的 PSU 支援 | LHM 程式碼有電源監控（`IsPowerMonitorEnabled`），對部分 Corsair PSU 有讀取；**具體支援型號清單我未在 LHM 文件逐一查證，標記未查證**。 | https://github.com/LibreHardwareMonitor/LibreHardwareMonitor |
| Corsair 官方 | 僅 **HXi / AXi** 標為 iCUE-enabled，提供即時電壓/電流/溫度/效率；一般型號無。 | https://www.corsair.com/us/en/explorer/diy-builder/power-supply-units/what-does-smart-power-supply-mean/ |

**PSU 結論：** 報告中 PSU 一律**條件式**處理——偵測到支援型號才給數據，否則明確回報「此 PSU 不提供軟體可讀的健康資訊」，**不得**為了畫面好看而虛構數值或宣稱能檢測。

---

## 2. 三個完整架構方案

> 五大類覆蓋度圖例：🟢完整　🟡有限/靜態　🔴基本拿不到/條件式

### 方案 A：LHM 為核心的完整感測方案 —（**建議優先關注**）

**一句話定位：** 以 LibreHardwareMonitor 當統一感測引擎，一套覆蓋主機板/CPU/GPU/硬碟真感測，WMI 補庫存資訊。

| 硬體類 | 用什麼 | 覆蓋 |
|---|---|---|
| 主機板（溫度/電壓/風扇） | `HardwareMonitor`（pythonnet+LHM DLL） | 🟢 |
| RAM | `wmi`（Win32_PhysicalMemory / MemoryErrorCorrection）+ LHM 記憶體負載 | 🟡（規格+ECC 型別，無健康度） |
| 硬碟 SMART | LHM 內建 storage SMART | 🟢（如要最完整屬性可再補 pySMART） |
| PSU | LHM 對支援型號讀取；否則回報不支援 | 🔴 條件式 |
| GPU | LHM（NVIDIA/AMD/Intel 溫度/負載/顯存/風扇） | 🟢 |

- **需 admin：** 是。
- **需額外安裝：** 需 `LibreHardwareMonitorLib.dll`（`HardwareMonitor` 套件方式可同進程載入、**不必開 GUI**）；**主機板感測需裝 `PawnIO` 核心驅動**。
- **維護風險：** 低（LHM v0.9.6 2026-02、HardwareMonitor v1.2.1 2026-06 皆活躍）。
- **唯讀鐵律相容性：** LHM 感測本身唯讀，符合。**但**：安裝 PawnIO/ring0 核心驅動屬底層硬體存取——**「安裝核心驅動」是否觸犯鐵律第 7 條『不修改驅動程式』屬灰色地帶**，需先向使用者確認（見第 3 節）。
- **主要代價/缺點：** 依賴 pythonnet + .NET 執行環境；**MS Store Python 對 pythonnet 相容性本機未驗證**；需提權；PawnIO 驅動安裝是額外門檻與鐵律灰區；RAM/PSU 覆蓋先天有限。
- **實作複雜度：** 中。

### 方案 B：純原生 WMI + pySMART 輕量方案 —（零第三方核心驅動）

**一句話定位：** 只用 Windows 原生 WMI + smartmontools，不裝 LHM、不裝任何核心驅動，最小侵入、鐵律最安全。

| 硬體類 | 用什麼 | 覆蓋 |
|---|---|---|
| 主機板 | WMI（`MSAcpi_ThermalZoneTemperature` 常不可用/失準；電壓、風扇通常拿不到） | 🔴 |
| RAM | WMI `Win32_PhysicalMemory` / `Win32_PhysicalMemoryArray` | 🟡 |
| 硬碟 SMART | `pySMART` + smartmontools（完整 SMART） | 🟢 |
| PSU | 無（誠實回報不支援） | 🔴 |
| GPU | `nvidia-ml-py`（僅 NVIDIA）+ WMI `Win32_VideoController`（僅型號/顯存） | 🟡（非 NVIDIA 只有型號） |

- **需 admin：** SMART 與 WMI thermal 需要。
- **需額外安裝：** 只需 smartmontools（`smartctl.exe`，是 CLI 工具**非常駐核心服務**）；不需 LHM、不需核心驅動。
- **維護風險：** 低–中（psutil/pySMART/nvidia-ml-py 皆活躍；`wmi` 套件疑停更但 API 穩定；**不採用已停更的 GPUtil**）。
- **唯讀鐵律相容性：** **最佳**——無核心驅動、smartctl 唯讀、WMI 唯讀，幾乎無踩線風險。
- **主要代價/缺點：** **主機板溫度/電壓/風扇覆蓋極差**（原生 WMI 拿不到真感測）；GPU 非 NVIDIA 只剩型號；整體「健康度」深度明顯不足，很多欄位只能顯示「不支援」。
- **實作複雜度：** 低–中。

### 方案 C：混合務實方案（LHM 主 + pySMART 補 + PSU 條件式）

**一句話定位：** 以最大覆蓋率為目標的務實組合，各類都用當前最合適的工具。

| 硬體類 | 用什麼 | 覆蓋 |
|---|---|---|
| 主機板/CPU/GPU 感測 | `HardwareMonitor`（LHM） | 🟢 |
| 硬碟 | `pySMART`+smartctl（比 LHM 更完整的 SMART 屬性） | 🟢 |
| RAM | WMI 庫存 + LHM 負載 | 🟡 |
| PSU | 偵測到 Corsair HXi/RMi 才用 `liquidctl` 讀 status（唯讀子集），否則回報不支援 | 🔴 條件式 |
| GPU 進階 | NVIDIA 補 `nvidia-ml-py`（ECC/顯存細節），AMD/Intel 靠 LHM | 🟢 |

- **需 admin：** 是。
- **需額外安裝：** LHM DLL、smartmontools、（條件）PawnIO、liquidctl 的 USB HID 存取。**相依面最大。**
- **維護風險：** 低（各套件都活躍），但**相依數量最多、要同時跟很多上游**。
- **唯讀鐵律相容性：** **需最嚴格紀律**——`liquidctl` 本身能控制硬體（寫入型），必須只呼叫讀取子集，誤用即違規；PawnIO/核心驅動同方案 A 的灰色地帶。
- **主要代價/缺點：** 整合最複雜、跨廠商測試成本最高、相依維護負擔最大、liquidctl 有誤用即違鐵律的風險。
- **實作複雜度：** 高。

### 方案比較速覽

| 面向 | A（LHM 核心） | B（純原生） | C（混合） |
|---|---|---|---|
| 主機板感測 | 🟢 | 🔴 | 🟢 |
| GPU 跨廠商 | 🟢 | 🟡 | 🟢 |
| 硬碟 SMART | 🟢 | 🟢 | 🟢 |
| RAM | 🟡 | 🟡 | 🟡 |
| PSU | 🔴條件 | 🔴 | 🔴條件 |
| 需核心驅動 | 是(PawnIO) | **否** | 是(PawnIO) |
| 鐵律安全度 | 中(灰區) | **高** | 中低(需紀律) |
| 維護風險 | 低 | 低-中 | 低(相依多) |
| 複雜度 | 中 | 低-中 | 高 |

---

## 3. 未查證 / 不確定 / 來源衝突事項（明確標註，未私自裁決）

1. **鐵律灰色地帶（最重要，需使用者裁決）：** 方案 A/C 需安裝 `PawnIO`（及/或 LHM 歷史上的 ring0 核心驅動）才能讀主機板感測。CLAUDE.md 鐵律第 7 條明訂「不修改驅動程式」。**「安裝一個唯讀感測用核心驅動」是否算違反此鐵律，屬解讀灰區，我不自行裁決**，需使用者拍板。若使用者判定不可裝任何核心驅動 → 只能走方案 B（主機板感測基本放棄）。
2. **`pywin32` 最新版本/釋出日期：未逐一查證**（只確認它是 `wmi` 套件相依、Windows 標準 bindings）。
3. **`PyLibreHardwareMonitorLib`（PyPI 替代套件）維護狀態：未查證**，僅列為 `HardwareMonitor` 的可能替代。
4. **LHM 內建 PSU 支援的具體型號清單：未在 LHM 官方文件逐一查證**；只確認其程式碼有電源監控能力、Corsair 官方確認 HXi/AXi 系列可讀。
5. **MS Store 版 Python + pythonnet 載入原生 DLL 的相容性：本機未實測**，標記為風險。方案 A/C 落地前應先做煙霧測試，或改用 python.org 版 Python。
6. **`wmi` 套件維護狀態**：來源顯示最後釋出為 2020，文件僅測到 Py3.4（看似停更），但它 API 穩定且至今仍被大量專案使用——「停更」與「仍可用」並存，**並列不裁決**。
7. **psutil `sensors_battery()` 在桌機（無電池）行為**：Windows 上函式可用，但無電池的桌機會回 `None`，屬預期行為，非 bug（僅提醒，非衝突）。

---

## 4. 來源清單（本次實際查閱）

- PyPI WMI：https://pypi.org/project/WMI/
- PyPI psutil：https://pypi.org/project/psutil/
- psutil issues（Windows 無 sensors_temperatures）：https://github.com/giampaolo/psutil/issues/1718 、 https://github.com/giampaolo/psutil/issues/2309
- PyPI pySMART：https://pypi.org/project/pySMART/
- PyPI GPUtil：https://pypi.org/project/GPUtil/
- PyPI nvidia-ml-py：https://pypi.org/project/nvidia-ml-py/
- pyadl：https://github.com/nicolargo/pyadl 、 https://pypi.org/project/pyadl/
- LibreHardwareMonitor：https://github.com/LibreHardwareMonitor/LibreHardwareMonitor
- PyPI HardwareMonitor（PyHardwareMonitor）：https://pypi.org/project/HardwareMonitor/ 、 https://github.com/snip3rnick/PyHardwareMonitor
- liquidctl：https://github.com/liquidctl/liquidctl
- LHM WMI 命名空間用法：https://metricshub.com/docs/0.9.04/connectors/librehardwaremonitor.html 、 https://hassagent.readthedocs.io/en/latest/wmi-examples/
- WMI 記憶體類別：https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-physicalmemory 、 https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-physicalmemoryarray 、 https://powershell.one/wmi/root/cimv2/win32_physicalmemory
- MSAcpi_ThermalZoneTemperature 限制：https://wutils.com/wmi/root/wmi/msacpi_thermalzonetemperature/
- Corsair 智慧 PSU：https://www.corsair.com/us/en/explorer/diy-builder/power-supply-units/what-does-smart-power-supply-mean/

---

## 5. 一句話建議

**優先關注方案 A（LHM + `HardwareMonitor` 套件）**，因為它是**唯一**能真正覆蓋主機板/多廠商 GPU 感測、且相依皆活躍維護的路線；**但落地前必須先請使用者裁決 PawnIO/核心驅動是否違反唯讀鐵律**。若使用者要求「零核心驅動」，則退回**方案 B**（鐵律最安全，但主機板感測基本放棄、GPU 非 NVIDIA 只剩型號）。方案 C 覆蓋最廣但相依與違規風險最高，適合在 A 站穩後再擴充。
