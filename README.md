# 電腦硬體健康檢測系統（PC Health Check）

讀取並回報主機板、記憶體、硬碟、電源供應器、顯示卡等元件的健康度／狀態，
讓使用者了解自己電腦的硬體狀況。**唯讀健康檢測**：不實作、不建議任何會
修改韌體、BIOS/UEFI 設定、磁碟分割或驅動程式的操作。

## 目前狀態

骨架（CLI + GUI）與 Windows 打包（免安裝版 + 安裝版 exe）皆已完成並實測
通過，見「下載與安裝」與「打包成 exe」。從原始碼執行時仍需自行安裝相依
套件與 PawnIO 驅動，詳見「已知風險與限制」。

## 下載與安裝

不想自己跑 Python 環境的話，直接用打包好的 exe（見「打包成 exe」章節
的建置方式取得 `dist/` 產出）：

- **免安裝版 `PCHealthCheck.exe`**：下載後雙擊即可執行，不會在系統裡留下
  任何安裝痕跡。
- **安裝版 `PCHealthCheckSetup.exe`**：下載後雙擊執行，會複製到
  `%LOCALAPPDATA%\Programs\PCHealthCheck\`、建立開始功能表捷徑，並可在
  「新增或移除程式」解除安裝。

兩者都會在啟動時跳出 UAC 提權對話框（讀取硬體感測器需要系統管理員權限），
這是正常現象。首次使用前請先依「已知風險與限制」安裝 PawnIO 驅動，否則
程式仍會正常開啟，只是部分感測器顯示「不可用」。

## 技術棧

- **Python 3.13**
- **LibreHardwareMonitor**（透過 `HardwareMonitor` PyPI 套件 + pythonnet 綁定其
  DLL）為主感測引擎，涵蓋主機板感測器、多廠牌 GPU、硬碟 SMART
- **WMI**（`wmi` / `pywin32`）：記憶體庫存資訊（`Win32_PhysicalMemory`）
- **nvidia-ml-py**（可選）：NVIDIA GPU 專屬細節補充
- **pywebview + 本地 HTML/CSS/JS**：桌面 GUI 儀表板，資料層與 CLI 共用，
  不重做判讀邏輯

完整選型比較與取捨見 `docs/framework-options.md`（感測引擎）與
`docs/ui-framework-options.md`（GUI 框架）。

## 快速開始

```powershell
pip install -r requirements.txt

# CLI：精簡健康報告
python src/pc_health_check/main.py

# CLI：完整原始感測器清單
python src/pc_health_check/main.py --detail

# GUI：桌面儀表板
python src/pc_health_check/ui/app.py
```

需要系統管理員權限與 LibreHardwareMonitor 所需的 PawnIO 驅動才能取得完整
感測資料；未滿足前提時，程式會優雅降級並顯示「不可用＋原因」，不會顯示
Python traceback。完整前置設定步驟（admin 權限、PawnIO 驅動安裝、
Microsoft Store 版 Python 相容性風險）見 **`docs/setup.md`**。

## 打包成 exe

只打包 GUI 儀表板（CLI 維持用 `python` 執行，不進打包範圍）。只用
PyInstaller，不依賴 Inno Setup/NSIS，兩個產出都是「下載、雙擊就動」的
單一 exe：

```powershell
# 於專案根目錄執行，依序建置免安裝版與安裝版
powershell -File build_scripts\build.ps1

# 建置完成後，用系統管理員身分開啟的 PowerShell 跑自動化驗收
powershell -File build_scripts\smoke_test.ps1
```

- `pyinstaller/app.spec`：免安裝版（`dist/PCHealthCheck.exe`），onefile、
  內嵌 `--uac-admin`、收齊 `HardwareMonitor` 套件的原生 DLL，並明確排除
  `PyQt5`/`PySide6` 等 pywebview 用不到的後端（避免誤把 GPL 授權的元件
  打包進去）。
- `installer/installer.py` + `installer.spec`：安裝版
  （`dist/PCHealthCheckSetup.exe`），自製輕量安裝機制（複製檔案、建捷徑、
  寫 `HKCU` 解除安裝機碼），本身也是 PyInstaller onefile exe。

可行性驗證結果、已知限制與跟 Inno Setup/NSIS 相比的取捨，見
`docs/build-feasibility.md` 與 `ops/lessons.md`（L-007～L-010）。

## 專案結構

```
src/pc_health_check/
├── main.py          # CLI 進入點
├── report.py        # 彙整各 sensors 模組，產生 HealthReport
├── health.py         # 健康判讀（正常/注意/警告）
├── engine.py         # LibreHardwareMonitor 感測引擎封裝
├── sensors/          # cpu / motherboard / memory / disk / psu / gpu
└── ui/
    ├── app.py         # pywebview GUI 進入點（含 --selftest 自我檢查旗標）
    └── web/           # index.html / style.css / script.js

pyinstaller/app.spec          # 免安裝版 exe 打包設定
installer/installer.py        # 安裝版邏輯（安裝/解除安裝）
installer/installer.spec      # 安裝版 exe 打包設定
build_scripts/build.ps1       # 依序建置免安裝版＋安裝版
build_scripts/smoke_test.ps1  # 建置後自動化驗收（需系統管理員權限執行）
```

## 各元件資料來源摘要

| 元件 | 主要資料來源 | 已知限制 |
|---|---|---|
| 主機板 | LibreHardwareMonitor | 需 PawnIO 驅動 + admin |
| 記憶體 | WMI（`Win32_PhysicalMemory`） | 僅庫存資訊，消費級 RAM 無健康度可讀 |
| 硬碟 | LibreHardwareMonitor 儲存裝置感測 | 涵蓋度依裝置/版本而異 |
| 電源供應器 | LibreHardwareMonitor（若偵測到 PSU 項目） | 多數 PSU 無軟體可讀資訊，預設視為不可用 |
| 顯示卡 | LibreHardwareMonitor＋可選 nvidia-ml-py | NVML 為可選補充，找不到裝置會優雅降級 |

## 已知風險與限制（誠實標註）

- PawnIO 驅動（LibreHardwareMonitor 讀取硬體暫存器所需，唯讀用途）需自行
  至官方網站 <https://pawnio.eu/> 下載安裝；安裝版 exe 不會自動安裝驅動，
  只會提示。
- 從原始碼直接執行時，本機 Python 為 Microsoft Store 版：其沙箱與路徑
  重新導向特性經實測**不影響** PyInstaller 建置與 pythonnet 載入原生
  DLL（見 `docs/build-feasibility.md`），但會影響「直接用 MS Store
  `python.exe` 寫入 Start Menu 等系統資料夾」這類操作（寫入會被靜默導向
  虛擬儲存區，使用者看不到），凍結成 exe 後不受影響，詳見
  `ops/lessons.md` L-008。
- 安裝版 exe 的解除安裝不會刪掉安裝目錄本身與 `Uninstall.exe`，需使用者
  自行刪除資料夾；也沒有標準安裝精靈 UI、多語系、簽章——這些是刻意不依賴
  Inno Setup/NSIS 換來的已知取捨，見 `docs/build-feasibility.md`。
- 詳細排查步驟與各項前提見 `docs/setup.md`。

## 文件索引

| 文件 | 內容 |
|---|---|
| `docs/setup.md` | 手動環境設定指南（admin 權限、驅動安裝、常見問題排查） |
| `docs/framework-options.md` | 感測引擎架構選型研究筆記 |
| `docs/ui-framework-options.md` | GUI 框架選型研究 |
| `docs/ui-design-spec.md` | GUI 視覺設計規格（色彩、字體、版面、無障礙檢查清單） |
| `docs/build-feasibility.md` | exe 打包可行性驗證結果與已知取捨 |

## 開發協作制度

本專案套用 `project-ops-template` 模型調度制度（`CLAUDE.md` + `ops/` 目錄），
用於規範 AI 協作時的派工、驗證與教訓記錄流程，與硬體檢測功能本身無關。
制度說明見 `CLAUDE.md` 與 `ops/50-letter.md`；來源見 `DEPLOY.md`。
