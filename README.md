# 電腦硬體健康檢測系統（PC Health Check）

[![Release](https://img.shields.io/github/v/release/uranium328/pc-health-check?include_prereleases&label=release)](https://github.com/uranium328/pc-health-check/releases/latest)
![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078D6)

一鍵讀取主機板、CPU、記憶體、硬碟、電源供應器、顯示卡的健康狀態，用白話
文字告訴你「正常／需要注意／警告」，不用自己看一堆感測器原始數字。

**唯讀，不動你的硬體**：本工具只讀取感測資料，不寫入、不調整任何韌體、
BIOS/UEFI 設定、磁碟分割或驅動程式設定。

## 目錄

- [特色](#特色)
- [下載與安裝](#下載與安裝)
- [系統需求](#系統需求)
- [涵蓋範圍](#涵蓋範圍)
- [已知限制](#已知限制)
- [開發者](#開發者)
- [回饋與問題回報](#回饋與問題回報)

## 特色

- **六大元件一次看**：主機板、CPU、記憶體、硬碟、電源供應器、顯示卡。
- **看得懂的判讀**：每個項目直接標「正常 / 注意 / 警告」，不用自己查
  數值代表什麼意思。
- **桌面儀表板 + 命令列雙介面**：不想開終端機的話用 GUI 儀表板；想看
  完整原始感測器清單就用 CLI。
- **下載就能用**：提供免安裝版與安裝版兩種 exe，不用先裝 Python。
- **誠實優雅降級**：缺少權限或驅動時不會顯示錯誤訊息，只會老實告訴你
  「這項不可用，原因是什麼」。

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
- [PawnIO](https://pawnio.eu/) 核心驅動（唯讀用途，不涉及任何寫入操作）

## 涵蓋範圍

| 元件 | 看得到什麼 | 限制 |
|---|---|---|
| 主機板 | 溫度、電壓、風扇轉速 | 需 PawnIO 驅動＋系統管理員權限 |
| CPU | 溫度、使用率、時脈 | — |
| 記憶體 | 容量、頻率、製造商 | 僅庫存資訊，一般消費級 RAM 讀不到健康度 |
| 硬碟 | SMART 健康狀態 | 涵蓋度依裝置/廠牌而異 |
| 電源供應器 | 少數智慧型號可讀 | 多數 PSU 無法讀取，預設顯示不可用 |
| 顯示卡 | 溫度、使用率、記憶體用量 | NVIDIA 顯卡另有較完整資訊 |

## 已知限制

- PawnIO 驅動需自行至官方網站 <https://pawnio.eu/> 下載安裝；安裝版 exe
  不會自動安裝驅動，只會提示。
- 安裝版 exe 的解除安裝不會刪掉安裝目錄本身與 `Uninstall.exe`，需自行
  刪除資料夾；也沒有標準安裝精靈 UI、多語系。
- 這兩個 exe 未經數位簽章，Windows SmartScreen 可能會跳警告。

## 開發者

```powershell
pip install -r requirements.txt

python src/pc_health_check/main.py         # CLI
python src/pc_health_check/ui/app.py       # GUI 桌面儀表板
```

完整環境設定步驟（admin 權限、PawnIO 驅動安裝、常見問題排查）見
`docs/setup.md`。

## 回饋與問題回報

遇到問題、感測結果看起來不對，或有功能建議，歡迎到
[Issues](https://github.com/uranium328/pc-health-check/issues) 開單回報。
