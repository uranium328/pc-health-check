# 電腦硬體健康檢測系統（PC Health Check）

讀取並回報主機板、記憶體、硬碟、電源供應器、顯示卡等元件的健康度／狀態，
讓使用者了解自己電腦的硬體狀況。**唯讀健康檢測**：不實作、不建議任何會
修改韌體、BIOS/UEFI 設定、磁碟分割或驅動程式的操作。

## 目前狀態

初始骨架已建立（CLI + GUI 皆可執行），尚未安裝相依套件與驅動、尚未在本機
實測。詳見「已知風險與限制」。

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

## 專案結構

```
src/pc_health_check/
├── main.py          # CLI 進入點
├── report.py        # 彙整各 sensors 模組，產生 HealthReport
├── health.py         # 健康判讀（正常/注意/警告）
├── engine.py         # LibreHardwareMonitor 感測引擎封裝
├── sensors/          # cpu / motherboard / memory / disk / psu / gpu
└── ui/
    ├── app.py         # pywebview GUI 進入點
    └── web/           # index.html / style.css / script.js
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

- 本機 Python 為 Microsoft Store 版，其沙箱與路徑重新導向特性對 pythonnet
  載入原生 DLL 的相容性尚未實測，若失敗建議改用 python.org 版 Python。
- PawnIO 驅動與 `HardwareMonitor` 套件的實際打包/載入方式尚未在本機驗證。
- 詳細排查步驟與各項前提見 `docs/setup.md`。

## 文件索引

| 文件 | 內容 |
|---|---|
| `docs/setup.md` | 手動環境設定指南（admin 權限、驅動安裝、常見問題排查） |
| `docs/framework-options.md` | 感測引擎架構選型研究筆記 |
| `docs/ui-framework-options.md` | GUI 框架選型研究 |
| `docs/ui-design-spec.md` | GUI 視覺設計規格（色彩、字體、版面、無障礙檢查清單） |

## 開發協作制度

本專案套用 `project-ops-template` 模型調度制度（`CLAUDE.md` + `ops/` 目錄），
用於規範 AI 協作時的派工、驗證與教訓記錄流程，與硬體檢測功能本身無關。
制度說明見 `CLAUDE.md` 與 `ops/50-letter.md`；來源見 `DEPLOY.md`。
