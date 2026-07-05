# 環境設定

這份文件教你怎麼把 PC Health Check 從原始碼跑起來。如果只是想用打包好的
exe，不用看這份文件，照 README 的下載說明抓來用就好。

這個工具只讀取硬體感測資料，不會寫入或修改任何韌體、BIOS/UEFI 設定、
磁碟分割或驅動程式設定。以下步驟裡唯一牽涉到安裝的東西是 PawnIO 驅動，
用途也只是唯讀感測，不涉及任何寫入操作。

## 1. 用系統管理員權限執行

大部分硬體感測（主機板溫度/電壓/風扇、硬碟 SMART、部分記憶體/WMI 查詢）
在 Windows 上需要系統管理員權限才能拿到完整資料。沒用管理員權限執行的
話，常見結果是感測器清單是空的，或 WMI 查詢直接回「Unsupported」。

- 想看到完整資料，就用「系統管理員身分執行」開啟 PowerShell 或 cmd，
  再執行 `python src/pc_health_check/main.py`。
- 沒用 admin 執行也沒關係，程式不會壞掉，只是會老實告訴你哪些項目
  「不可用」以及原因。

## 2. 安裝 PawnIO 驅動

這個工具的核心感測引擎是透過 `HardwareMonitor` 這個 Python 套件（底層用
pythonnet 綁定 LibreHardwareMonitorLib.dll）讀取主機板/GPU/硬碟的感測器。
比較新版的 LibreHardwareMonitor 改用 **PawnIO** 這個核心驅動做唯讀的硬體
暫存器存取，取代了舊的 WinRing0。

1. 到 PawnIO 官方網站 <https://pawnio.eu/> 下載安裝（安裝過程需要 admin
   權限，會跳出 Windows 的驅動程式安裝確認畫面）。
2. `pip install -r requirements.txt` 會順便裝好 `HardwareMonitor` 套件，
   裡面附的 LibreHardwareMonitorLib.dll 不用另外處理，pythonnet 可以
   直接載入。
3. 沒裝這個驅動的話，`engine.get_engine()` 會回傳「還沒準備好」，對應的
   感測器模組會顯示「不可用」跟原因，程式不會因此當掉。

## 3. Microsoft Store 版 Python 相容性

如果你用的是 Microsoft Store 版 Python（site-packages 路徑裡會有
`PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0` 這種字樣）：實測過
pythonnet 在這個環境下可以正常載入 LibreHardwareMonitorLib.dll，不會因為
Store 版的應用程式沙箱而失敗，可以放心直接用。

如果還是遇到 DLL 載入、CLR 初始化，或「找不到組件」之類的例外
（`engine.py` 會攔截起來，顯示在主機板/硬碟/顯示卡的「不可用原因」欄位
裡），可以照這個順序排查：

1. 確認有沒有用系統管理員身分執行。
2. 確認 `pip install -r requirements.txt` 有在同一個 Python 環境裝好
   `pythonnet` 和 `HardwareMonitor`（`pip show pythonnet` 看一下）。
3. 還是不行的話，換官方 python.org 版的 Python 3.13（不是 Store 版）
   重新建一個虛擬環境試試看。

## 4. 安裝套件、執行程式

```powershell
# 在專案根目錄 E:/program/pc-health-check/ 下執行
pip install -r requirements.txt

python src/pc_health_check/main.py
```

如果是一般身分執行、也還沒裝上面的套件跟驅動，每個元件會顯示「不可用」
跟原因（像是「未安裝 'HardwareMonitor' 套件」），這是正常的降級行為，
不是程式壞掉。想看到完整報告，先照第 1～3 節把權限、驅動、環境都弄好
再執行。

## 5. 各元件的資料來源與限制

| 元件 | 資料來源 | 限制 |
|---|---|---|
| 主機板 | LibreHardwareMonitor | 需要 PawnIO 驅動 + admin 權限，沒裝就顯示不可用 |
| 記憶體 | WMI（`Win32_PhysicalMemory`） | 只有容量/頻率/製造商這些庫存資訊，一般消費級 RAM 讀不到健康度 |
| 硬碟 | LibreHardwareMonitor 的儲存裝置感測 | 涵蓋度依裝置/廠牌而異 |
| 電源供應器 | LibreHardwareMonitor（如果偵測到 PSU） | 大多數 PSU 沒有軟體可讀資訊，只有少數智慧型號（部分 Corsair）可能讀得到，其餘預設不可用 |
| 顯示卡 | LibreHardwareMonitor，NVIDIA 另外用 `nvidia-ml-py` 補充 | 找不到 NVIDIA 裝置或沒裝套件時會自動降級，不影響其他元件 |

## 6. 啟動 GUI 版本

除了上面的 CLI，這個工具也有一個 pywebview 桌面 GUI，用同一份資料
（`report.py`/`health.py` 產生的結果，GUI 只負責畫面呈現，判讀邏輯完全
共用）畫成一個本地網頁儀表板，比較適合不熟終端機的人用。

```powershell
pip install -r requirements.txt   # 已經包含 pywebview，裝過可以跳過

python src/pc_health_check/ui/app.py
```

- 跟 CLI 一樣會優雅降級：就算目前沒用 admin、沒裝 PawnIO 驅動，視窗
  還是會正常開啟，畫面上會用提示橫幅顯示「不可用＋原因」，不會跳出
  錯誤訊息或整個崩潰。
- 右上角的「重新整理」按鈕會重新抓一次最新的硬體狀態；關掉視窗程式就
  整個結束，不會留下背景行程。
- 想看到完整資料，一樣要先滿足第 1～2 節的權限跟驅動需求，GUI 跟 CLI
  共用同一套資料層。
