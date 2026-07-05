# 電腦硬體健康檢測系統（PC Health Check）

[![Release](https://img.shields.io/github/v/release/uranium328/pc-health-check?include_prereleases&label=release)](https://github.com/uranium328/pc-health-check/releases/latest)
![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078D6)
![Python](https://img.shields.io/badge/python-3.13-3776AB)

一鍵讀取主機板、CPU、記憶體、硬碟、電源供應器、顯示卡的健康狀態，用白話
文字告訴你「正常／需要注意／警告」，不用自己看一堆感測器原始數字。

**唯讀，不動你的硬體**：本工具只讀取感測資料，不寫入、不調整任何韌體、
BIOS/UEFI 設定、磁碟分割或驅動程式設定。

## 目錄

- [特色](#特色)
- [下載與安裝](#下載與安裝)
- [系統需求](#系統需求)
- [開發者從原始碼執行](#開發者從原始碼執行)
- [打包成 exe](#打包成-exe)
- [專案結構](#專案結構)
- [各元件資料來源摘要](#各元件資料來源摘要)
- [已知限制](#已知限制)
- [文件索引](#文件索引)
- [回饋與問題回報](#回饋與問題回報)

## 特色

- **六大元件一次看**：主機板溫度/電壓/風扇、CPU、記憶體、硬碟 SMART、
  電源供應器、顯示卡（多廠牌，NVIDIA 另有補充資訊）。
- **看得懂的判讀**：每個項目直接標「正常 / 注意 / 警告」，不用自己查
  數值代表什麼意思。
- **桌面儀表板 + 命令列雙介面**：不想開終端機的話用 GUI 儀表板；
  要接腳本或想看完整原始感測器清單就用 CLI。
- **下載就能用**：提供免安裝版與安裝版兩種 exe，不用先裝 Python。
- **誠實優雅降級**：缺少權限或驅動時不會顯示 Python 錯誤訊息，只會
  老實告訴你「這項不可用，原因是什麼」。

## 下載與安裝

一般使用者不需要自己架 Python 環境，直接到
**[Releases 頁面](https://github.com/uranium328/pc-health-check/releases/latest)**
下載打包好的 exe：

| 版本 | 適合情境 |
|---|---|
| `PCHealthCheck.exe`（免安裝版） | 下載後雙擊即可執行，不會在系統裡留下任何安裝痕跡 |
| `PCHealthCheckSetup.exe`（安裝版） | 下載後雙擊執行，會安裝到本機並建立開始功能表捷徑，之後可在「新增或移除程式」解除安裝 |

> 兩者啟動時都會跳出 UAC 提權對話框，這是正常現象——讀取硬體感測器需要
> 系統管理員權限。首次使用前建議先安裝 [PawnIO](https://pawnio.eu/) 驅動
> （唯讀感測用途），否則程式仍會正常開啟，只是部分感測器會顯示「不可用」。

## 系統需求

- Windows 10/11（64-bit）
- 系統管理員權限（完整讀取硬體感測器所需）
- [PawnIO](https://pawnio.eu/) 核心驅動（LibreHardwareMonitor 讀取硬體
  暫存器所需，唯讀用途，不涉及任何寫入操作）

## 開發者從原始碼執行

```powershell
pip install -r requirements.txt

# CLI：精簡健康報告
python src/pc_health_check/main.py

# CLI：完整原始感測器清單
python src/pc_health_check/main.py --detail

# GUI：桌面儀表板
python src/pc_health_check/ui/app.py
```

完整前置設定步驟（admin 權限、PawnIO 驅動安裝、Microsoft Store 版 Python
相容性風險）見 **`docs/setup.md`**。

技術棧：**Python 3.13** + **LibreHardwareMonitor**（透過 `HardwareMonitor`
PyPI 套件 + pythonnet 綁定其 DLL，涵蓋主機板感測器、多廠牌 GPU、硬碟
SMART）+ **WMI**（記憶體庫存資訊）+ 可選 **nvidia-ml-py**（NVIDIA 專屬
細節）+ **pywebview**（桌面 GUI，資料層與 CLI 共用、不重做判讀邏輯）。
完整選型比較見 `docs/framework-options.md`（感測引擎）與
`docs/ui-framework-options.md`（GUI 框架）。

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

建置產物（`dist/`）不進 git 版控，發布時改用 GitHub Releases 附加 exe
檔——可行性驗證結果、已知限制與跟 Inno Setup/NSIS 相比的取捨，見
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

## 已知限制

- PawnIO 驅動需自行至官方網站 <https://pawnio.eu/> 下載安裝；安裝版 exe
  不會自動安裝驅動，只會提示。
- 安裝版 exe 的解除安裝不會刪掉安裝目錄本身與 `Uninstall.exe`，需使用者
  自行刪除資料夾；也沒有標準安裝精靈 UI、多語系、簽章——這些是刻意不依賴
  Inno Setup/NSIS 換來的已知取捨，見 `docs/build-feasibility.md`。
- 從原始碼直接執行時，若本機 Python 為 Microsoft Store 版：其沙箱與路徑
  重新導向特性經實測**不影響** PyInstaller 建置與 pythonnet 載入原生
  DLL，但會影響「直接用 MS Store `python.exe` 寫入 Start Menu 等系統
  資料夾」這類操作，凍結成 exe 後不受影響，詳見 `ops/lessons.md` L-008。
- 詳細排查步驟見 `docs/setup.md`。

## 文件索引

| 文件 | 內容 |
|---|---|
| `docs/setup.md` | 手動環境設定指南（admin 權限、驅動安裝、常見問題排查） |
| `docs/framework-options.md` | 感測引擎架構選型研究筆記 |
| `docs/ui-framework-options.md` | GUI 框架選型研究 |
| `docs/ui-design-spec.md` | GUI 視覺設計規格（色彩、字體、版面、無障礙檢查清單） |
| `docs/build-feasibility.md` | exe 打包可行性驗證結果與已知取捨 |

## 回饋與問題回報

遇到問題、感測結果看起來不對，或有功能建議，歡迎到
[Issues](https://github.com/uranium328/pc-health-check/issues) 開單回報。

---

<sub>本專案套用 `project-ops-template` 模型調度制度（`CLAUDE.md` + `ops/`
目錄），用於規範 AI 協作時的派工、驗證與教訓記錄流程，與硬體檢測功能本身
無關。制度說明見 `CLAUDE.md` 與 `ops/50-letter.md`；來源見 `DEPLOY.md`。</sub>
