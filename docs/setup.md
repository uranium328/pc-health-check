# 環境設定說明（手動操作指南）

> 本文件給「要實際跑起這個骨架」的使用者看。目前這份專案只是**初始骨架**，
> 尚未安裝任何相依套件、驅動或背景服務——這些都需要你自己手動操作，
> 骨架本身**不會**自動安裝任何東西。

鐵律提醒：本工具是**唯讀健康檢測**，不實作、不建議任何會修改韌體、
BIOS/UEFI 設定、磁碟分割或驅動程式的操作。以下所有步驟也只涉及「安裝
唯讀感測用途的驅動／函式庫」，不涉及任何寫入型操作。

---

## 1. 需要系統管理員（admin）權限執行

大部分硬體感測（主機板溫度/電壓/風扇、硬碟 SMART、部分記憶體/WMI 查詢）
在 Windows 上**需要以系統管理員身分執行**才能拿到完整資料，非提權執行時
常見結果是感測器清單為空、或 WMI 查詢回傳 "Unsupported"。

- 若要看到完整感測資料，請以「系統管理員身分執行」開啟終端機（PowerShell
  或 cmd），再於該終端機內執行 `python src/pc_health_check/main.py`。
- 若不用 admin 執行，本程式仍不會崩潰，只會誠實回報「不可用」與原因。

## 2. 安裝 LibreHardwareMonitor 所需的 PawnIO 驅動（需要你手動操作）

本專案的核心感測引擎（`src/pc_health_check/engine.py`）透過 `HardwareMonitor`
這個 PyPI 套件（內部使用 pythonnet 綁定 LibreHardwareMonitorLib.dll）讀取
主機板/GPU/硬碟感測器。較新版的 LibreHardwareMonitor 底層改用 **PawnIO**
這個核心驅動來做唯讀的硬體暫存器存取（取代舊有的 WinRing0）。

背景（已由使用者裁決）：安裝 PawnIO 驅動的用途僅限於唯讀感測數值讀取，
不涉及任何寫入型操作；使用者已明確允許安裝此驅動。

**這一步需要你自己手動操作，本骨架不會、也不能自動安裝：**

1. 至 PawnIO 官方網站 <https://pawnio.eu/>（2026-07-05 查證，LibreHardwareMonitor
   專案已改用此驅動取代舊有 WinRing0）下載並安裝 PawnIO 核心驅動（安裝過程
   需要 admin 權限，會跳出 Windows 驅動程式安裝確認）。
2. 確認 LibreHardwareMonitorLib.dll（隨 `HardwareMonitor` PyPI 套件一起
   發佈，或視套件實作方式可能需要額外放置 DLL 檔案——實際打包方式請以
   `pip install HardwareMonitor` 後套件內容為準，本骨架尚未實測）已存在
   於可被 pythonnet 載入的路徑。
3. 若上述步驟未完成，`engine.get_engine()` 會回傳 `ready=False`，各
   sensors 模組會各自顯示「不可用」與具體原因，`main.py` 不會因此崩潰。

## 3. Microsoft Store 版 Python 的 pythonnet 相容性風險

本機環境查證結果（見 `docs/framework-options.md` 第 0 節）：目前 Python
為 **3.13.14 的 Microsoft Store 版**（site-packages 路徑含
`PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0`）。

**已知風險（尚未在本機實測，誠實標註）：**
Microsoft Store 版 Python 有應用程式沙箱與檔案系統重新導向的特性，對
`pythonnet` 這類需要載入原生 `.dll`（CLR 執行環境 + LibreHardwareMonitorLib.dll）
的套件，相容性未經本機驗證。

若安裝 `pythonnet` 後執行 `main.py` 出現與 DLL 載入、CLR 初始化、或
「找不到組件」相關的例外（`engine.py` 會攔截並顯示在「主機板/硬碟/顯示卡」
的不可用原因欄位中），建議依序排查：

1. 確認是否以系統管理員身分執行。
2. 確認 `pip install -r requirements.txt` 是否在同一個 Python 環境下成功
   安裝了 `pythonnet` 與 `HardwareMonitor`（`pip show pythonnet` 檢查）。
3. 若懷疑是 MS Store 版 Python 的沙箱/路徑限制導致，**建議改用官方
   python.org 發行版的 Python 3.13**（非 Store 版）重新建立虛擬環境後再試，
   這是目前研究筆記中對此風險的建議規避方案，但尚未實測驗證其必然解決問題。

## 4. 安裝相依套件與執行程式

```powershell
# 於專案根目錄 E:/program/pc-health-check/ 下執行
pip install -r requirements.txt

python src/pc_health_check/main.py
```

- 若你是以一般（非 admin）身分、且尚未安裝上述套件與驅動的狀態下執行，
  預期會看到每個元件顯示「狀態：不可用」與對應原因（例如「未安裝
  'HardwareMonitor' 套件」「未安裝 'wmi' 套件」等），這是**預期中的優雅
  降級行為**，不是程式錯誤。
- 若要重新產生完整報告，請依序完成本文件第 1～3 節後再執行。

## 5. 各元件資料來源與已知限制（誠實摘要）

| 元件 | 主要資料來源 | 已知限制 |
|---|---|---|
| 主機板 | LibreHardwareMonitor（`engine.py`） | 需 PawnIO 驅動 + admin，未安裝時顯示不可用 |
| 記憶體 | `wmi`（`Win32_PhysicalMemory`） | 僅庫存資訊（容量/頻率/製造商），消費級 RAM 無健康度可讀 |
| 硬碟 | LibreHardwareMonitor 儲存裝置感測 | 涵蓋度依裝置/版本而異；未來可考慮改用 pySMART + smartmontools |
| 電源供應器 | LibreHardwareMonitor（若偵測到 PSU 硬體項目） | 一般 PSU 無軟體可讀資訊，僅少數智慧型號（如部分 Corsair）可能可讀，預設視為不可用 |
| 顯示卡 | LibreHardwareMonitor（多廠牌）＋ 可選 `nvidia-ml-py`（僅 NVIDIA） | NVML 補充資訊為可選功能，找不到 NVIDIA 裝置或未安裝套件會優雅降級 |

## 6. 如何啟動圖形介面（GUI）版本

除了第 4 節的 CLI 版本，本專案也提供一個 pywebview 桌面 GUI 骨架，把同一份
健康報告（仍是 `report.py`/`health.py` 產出的資料，GUI 只負責呈現，判讀邏輯
不重做）用本地網頁儀表板呈現，方便非工程師使用者閱讀。

```powershell
# 於專案根目錄 E:/program/pc-health-check/ 下執行
pip install -r requirements.txt   # 已包含 pywebview，若已裝過可省略

python src/pc_health_check/ui/app.py
```

- 與 CLI 版本相同的優雅降級原則：即使目前是非 admin、尚未安裝 PawnIO 驅動
  （sensors 完全讀不到資料的狀態），視窗仍會正常開啟，並在畫面上以中性提示
  橫幅顯示「不可用＋原因」，不會跳出 Python traceback 或整個視窗崩潰。
- 視窗右上角「重新整理」按鈕會重新呼叫 `generate_report()`，抓取最新的硬體
  狀態；關閉視窗即結束整個程式，不會留下背景殘留行程。
- 若要看到完整感測資料，同樣需要滿足第 1～3 節（admin 權限、PawnIO 驅動、
  MS Store Python 相容性風險）的前提，GUI 版本與 CLI 版本共用同一套資料層，
  沒有另外的權限或安裝需求。
- GUI 介面的視覺規格（色彩、字體、版面、無障礙檢查清單等）定義於
  `docs/ui-design-spec.md`，不在本文件重複列出。
