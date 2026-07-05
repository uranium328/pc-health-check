# UI 框架選型研究（桌面圖形介面）

> 目的：為「電腦硬體健康檢測系統」決定並建立一個**桌面圖形介面**，取代/補充目前純 CLI 的呈現。
> 目標使用者：**一般不懂技術的電腦使用者**——UI 必須好看、好懂，不能像工程除錯畫面。
> 鐵律：**唯讀健康檢測**。UI 只能呈現資料、觸發重新讀取，**不得**有任何修改韌體 / BIOS/UEFI / 磁碟分割 / 驅動程式的操作或按鈕。
>
> 研究日期：2026-07-05。本檔為研究筆記，**不修改任何既有檔案**，也未寫任何程式碼。
> 所有版本號/授權/相容性結論皆附來源；查不到或不確定者一律標註（見文末「未查證 / 衝突事項」）。

---

## 0. 本機環境查證結果（實測，非臆測）

以下為 2026-07-05 在本機（Windows 11 Pro 26200、Python 3.13.14）實際執行 `python`/`winreg`/`pip` 查得：

| 項目 | 查證方式 | 結果 |
|---|---|---|
| Python | `python --version` / `where python` | **3.13.14，MS Store 版**（路徑 `C:\Users\Shinichicken\AppData\Local\Microsoft\WindowsApps\python.exe`） |
| tkinter 能否 import | `import tkinter` | **成功**。`TkVersion=8.6`、`TclVersion=8.6` |
| tkinter 能否**開窗** | `tk.Tk(); r.update(); r.destroy()` | **成功**建立並更新一個 Tk root 視窗，無例外。**→ 本機 MS Store 版 Python 的 tkinter 未壞、Tcl/Tk DLL 齊全，可用。**（推翻「MS Store 版 tkinter 一定壞」的假設；本機實測正常。） |
| WebView2 Runtime | 查登錄檔 `HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}` 的 `pv` | **已安裝**，版本 `149.0.4022.98`，system-wide（HKLM）。**→ pywebview 預設 renderer 在本機可直接用，開發機不需另裝任何東西。** |
| 目前已裝 GUI 相關套件 | `pip list` | 見下表 |

### 本機 `pip list` 中與 UI / 打包 / 資料層相關的既有套件

**GUI 相關（已裝）**
- `customtkinter 5.2.2`（本機此版授權顯示為 **CC0-1.0**；相依 `darkdetect`、`packaging`；`darkdetect 0.8.0`、`pillow 11.3.0` 均在）
- `PyQt5 5.15.11`（+ `PyQt5-Qt5 5.15.2`、`PyQt5_sip 12.17.0`）→ **注意：PyQt5 是 GPL/商業雙授權，散布限制大，見 §4 授權說明**
- `pygame 2.6.1`（非本研究主線，僅記錄）

**打包相關（已裝）**
- `pyinstaller 6.19.0`、`pyinstaller-hooks-contrib 2026.2`

**Web / 伺服器（已裝）**
- `Flask 3.1.1`（+ `Werkzeug 3.1.3`、`Jinja2 3.1.6`、`click`、`itsdangerous`、`blinker`）
- `FastAPI` **未裝**、`uvicorn` **未裝**

**圖表 / 圖像（已裝）**
- `matplotlib 3.10.8`、`seaborn 0.13.2`、`pillow 11.3.0`、`reportlab 4.4.7`、`fpdf2 2.8.5`

**資料層依賴（已裝，供整合參考）**
- `HardwareMonitor 1.2.1`、`pythonnet 3.1.0`、`clr_loader 0.3.1`、`nvidia-ml-py 13.610.43`、`WMI 1.5.1`、`pywin32 312`

**候選 UI 方案中「尚未安裝」者**
- **`PySide6` 未裝**、**`pywebview` 未裝**、**`flet` 未裝**、**`dearpygui` 未裝**

> 關鍵協同點：**`pythonnet 3.1.0` 已因資料層（HardwareMonitor）而安裝**。pywebview 在 Windows 的預設 renderer 也正是走 pythonnet + WebView2，**兩者共用同一條 pythonnet 路徑**——若資料層的 pythonnet native DLL 載入在 MS Store 版 Python 上可行，pywebview 這條路很可能同樣可行（詳見 §5 風險）。

---

## 1. 現有資料層可以怎麼接（三個 UI 方案都一樣）

已讀 `src/computer_info/report.py`、`health.py`、`main.py`，資料層與呈現層**分離良好**，任何 UI 都能直接重用，**不需要改動資料層**：

- `report.generate_report()` → 回傳 `HealthReport`，其 `.components` 是 dict（key：`motherboard`/`memory`/`disk`/`psu`/`gpu`），每個值是 `ComponentStatus(name, available, reason, data)`。
- `health.build_motherboard_section(status)` … `build_gpu_section(status)`（共 5 個）→ 各回傳一個 `FriendlySection(title, available, unavailable_reason, devices[])`。
  - `FriendlyDevice(name, items[])`；`FriendlyItem(text, verdict)`。
  - **`verdict` 欄位值只會是 `"正常"/"注意"/"警告"` 或 `None`**——這正好對應 UI 的**綠/黃/紅**色階，是「給外行人看」的天然著色依據。
- `health.overall_summary(sections)` → 回傳一行整體摘要字串。

`main.py._print_friendly_report()` 已示範完整呼叫順序（建 5 個 section → `overall_summary` → 逐 section/device/item 走訪）。**任何 GUI 只要照抄這個走訪迴圈，把 `print()` 換成畫元件即可。**

**整合建議（三方案共用）**：新增一個薄薄的 `presenter`/adapter，把 `FriendlySection` 系列 dataclass 轉成 UI 要的形狀：
- Web 系（pywebview / Flask）：`dataclasses.asdict()` 直接轉 JSON 丟給前端；`verdict` → CSS class。
- 原生系（PySide6 / Tkinter）：直接走訪 dataclass，`verdict` → 對應顏色的 badge/label。
- **「重新整理」按鈕**：只重跑 `generate_report()`（唯讀），完全符合鐵律。**不要**加任何寫入型按鈕。

> 資料層改動需求：**基本上為零**。頂多加一個唯讀的 adapter 函式（放新檔），不動 `report.py`/`health.py`。

---

## 2. 候選框架逐一查證（含來源）

### A. Tkinter / ttk（+ 可選 CustomTkinter）
- **內建 tkinter**：本機實測可用（見 §0）。CPython 核心元件，維護最穩，零額外套件、零授權疑慮（PSF 授權）。
- **CustomTkinter**：讓外觀現代化（圓角、深/淺色、現代配色）。
  - 最新版 **6.0.0，2026-06-24 發布，PyPI 標示 MIT 授權**。來源：[customtkinter · PyPI](https://pypi.org/project/customtkinter/)、[TomSchimansky/CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
  - **本機已裝的是 5.2.2（授權顯示為 CC0-1.0）**——與最新 6.0.0（MIT）**版本與授權都不同**（見 §6 未查證項）。CC0 與 MIT 皆為寬鬆授權，**散布皆無限制**，差別不影響能否自由散布。
  - 相依：`darkdetect`、`packaging`（本機皆已裝）。
  - 維護：6.0.0 為 2026-06 的近期釋出，是**正面訊號**；GitHub star 約 1.3 萬。惟為**單一主要維護者**專案，社群過去曾討論其活躍度時有起伏（本研究未能精確核實 commit 頻率，標為部分未查證）。

### B. PySide6（Qt for Python，官方 Qt binding）
- 最新版 **6.11.1，2026-05-13 發布**。來源：[PySide6 · PyPI](https://pypi.org/project/PySide6/)
- **Python 3.13 支援：有**（PyPI classifier 列出 3.10/3.11/3.12/**3.13**/3.14）。
- **授權：`LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only`**（PyPI 標示）。關鍵：**可用 LGPLv3 自由散布（含商業、含閉源）**，只要遵守 LGPL（動態連結、允許使用者替換 Qt 函式庫、附上授權文字）。這與 PyQt 的 GPL/商業雙授權是**重大差異**（見 §4）。來源：[PyQt vs PySide Licensing](https://www.pythonguis.com/faq/pyqt-vs-pyside/)
- **體積**：PyPI 上 `PySide6` 那顆 wheel 只有 ~561–578 KB——**那是薄的 meta-package**，會再拉進 `PySide6-Essentials` + `PySide6-Addons`，**實際安裝體積遠大於此（社群常引 150MB 量級）**。來源：[PySide6-Essentials · PyPI](https://pypi.org/project/PySide6-Essentials/)
- 打包：PyInstaller **內建 PySide6 hook，開箱即可打包**；但 exe 明顯偏大。來源：[pyinstaller · PyPI](https://pypi.org/project/pyinstaller/)

### C. pywebview + 本地 HTML/CSS/JS
- 最新版 **6.2.1，2026-04-15 發布，BSD 3-Clause 授權**。來源：[pywebview · PyPI](https://pypi.org/project/pywebview/)
- **Python 3.13 支援：有**（PyPI classifier 含 3.13；`Requires-Python >=3.8`）。
- **Windows 依賴**：預設 renderer 為 **EdgeChromium / WebView2**，需要 **`pythonnet`（>.NET 4.0）** 與 **WebView2 Runtime**。來源：[pywebview 安裝文件](https://pywebview.flowrl.com/guide/installation.html)
  - **本機兩者皆已就緒**：`pythonnet 3.1.0`（資料層已裝）＋ WebView2 `149.0.4022.98`（系統層已裝）。→ **開發機零額外 runtime 安裝即可跑。**
- 維護：6.2.1（2026-04）近期釋出，活躍。來源同上、[r0x0r/pywebview](https://github.com/r0x0r/pywebview/)
- **打包已知坑**（重要，來自 GitHub issues）：
  - 打包後 HTML/靜態檔**路徑解析失敗、出現 404 / 「index.html not found」**——需正確處理 PyInstaller 的 `sys._MEIPASS` 與資料檔收集。來源：[issue #1402](https://github.com/r0x0r/pywebview/issues/1402)、[issue #1010](https://github.com/r0x0r/pywebview/issues/1010)
  - 舊版 **pywebview 3.0 + PyInstaller `--noconsole` 在 Win10 會 crash**（issue #347）；**是否仍影響 6.2.1 未查證**（見 §6）。來源：[issue #347](https://github.com/r0x0r/pywebview/issues/347)
  - exe 體積可達 **80–90MB**。來源：[issue #353](https://github.com/r0x0r/pywebview/issues/353)。PyInstaller 3.6+ 已改良 pywebview hook（只收 Windows 所需 lib）。

### D. Flask / FastAPI + 瀏覽器分頁
- `Flask 3.1.1` **已裝**；`FastAPI`/`uvicorn` **未裝**。
- 實作最單純（起本機伺服器 + 開瀏覽器分頁），但體驗上**不像獨立小工具**：佔用一個本機 port、使用者要自己開/切分頁；若沒特別處理，**關掉終端機視窗會連帶關掉服務**（除非打包成背景程序）。對「外行人用的單機小工具」定位偏弱。

### E. 其他納入比較者
- **Flet**：最新穩定 **0.85.3（2026-06-08）**，`Apache-2.0`，`Requires-Python >=3.10`（3.13 是否明確支援**未逐一核實**，見 §6）；底層是編譯後的 Flutter desktop client，外觀漂亮。**但打包很重**：官方 `flet build windows` **需要 Flutter SDK + Visual Studio「使用 C++ 的桌面開發」workload + 開啟開發者模式**，遠比 PyInstaller 麻煩；且 0.x 版 API 仍在演進、跨小版本曾有破壞性變更。來源：[flet · PyPI](https://pypi.org/project/flet/)、[Flet 打包 Windows 文件](https://flet.dev/docs/publish/windows/)
- **DearPyGui**：最新 **2.3.1（2026-05-01）**，**MIT**，支援 Python 3.8–3.14（含 3.13），Production/Stable、有贊助支持、活躍。來源：[dearpygui · PyPI](https://pypi.org/project/dearpygui/)、[hoffstadt/DearPyGui](https://github.com/hoffstadt/DearPyGui)。**但**它是 GPU 加速的 immediate-mode（Dear ImGui 風格），**預設外觀偏「工程師 / 遊戲除錯面板」味**，要做到「給外行人的溫柔儀表板」不如 Web/Qt 直覺。故不列為主推。

---

## 3. 三個完整方案（技術棧 + 呈現方式）

> 三個方案對資料層的整合方式相同（見 §1），差別在呈現層與打包/授權/體積。

### 方案一（建議關注）：pywebview + 本地 HTML/CSS/JS 儀表板
- **一句話定位**：用 Python 開一個原生視窗，內容用網頁技術做成現代化健康儀表板；外觀天花板最高，且本環境的 `ui-ux-pro-max` skill 正好擅長 HTML/CSS 設計，能把「給外行人看」做到最好。
- **套件組合**：`pywebview 6.2.1`（BSD）＋ **重用已裝的 `pythonnet 3.1.0`＋系統 WebView2 v149**（開發機零新增 runtime）。前端純 HTML/CSS/JS（可不引任何前端框架，靜態檔即可）。
- **整合方式**：`generate_report()` → 5 個 `build_*_section` → `overall_summary`；用 `dataclasses.asdict()` 把 sections 轉 JSON，透過 pywebview 的 `js_api` / `evaluate_js` 餵給前端；`verdict`（正常/注意/警告）→ 前端綠/黃/紅色階。**資料層不動**，只加一個唯讀 adapter。「重新整理」鈕呼叫一個 Python 端唯讀函式重跑 `generate_report()`。
- **外觀 / 適合外行人**：**最佳**。CSS 完全可控，可做卡片式、色階清楚、圖示化的消費級儀表板；配合 `ui-ux-pro-max` skill 產出質感最高。
- **打包難易**：PyInstaller 可行，但**有已知坑**——HTML/靜態檔要正確收進 bundle 並處理 `sys._MEIPASS` 路徑（否則 404）；舊版曾有 `--noconsole` crash（6.2.1 是否仍有**未查證**，需實測）。exe 約數十 MB。
- **授權 / 散布**：pywebview **BSD-3，自由散布無虞**。**WebView2 Runtime**：本開發機已有；**終端使用者機器需要有**（Win10/11 多半內建 Evergreen runtime，但**不保證每台都有**，散布時應驗證或附帶 bootstrapper——見 §6）。
- **維護風險**：低—中（6.2.1 為 2026-04 近期釋出，活躍）。
- **主要代價 / 缺點**：雙語言棧（Python + HTML/JS）；打包 web 資產有已知路徑坑；**依賴 pythonnet 在 MS Store 版 Python 上載入原生元件（與資料層同一項未實測風險，見 §5）**；使用者端需 WebView2。
- **實作複雜度**：中（多了前端 + 橋接；但 `ui-ux-pro-max` 大幅降低 UI 工作量）。

### 方案二（建議的原生替代）：PySide6 原生 Qt 桌面程式
- **一句話定位**：全 Python、純原生 Qt 元件的專業桌面 App，不依賴 WebView2、像一個「真正安裝的應用程式」。
- **套件組合**：`PySide6 6.11.1`（LGPLv3）。UI 全用 Qt Widgets，`verdict` 用彩色 badge/label 呈現；需要圖表時可嵌 matplotlib（已裝）。
- **整合方式**：同 §1，直接走訪 `FriendlySection` dataclass 畫成 Qt 卡片。**資料層不動**。
- **外觀 / 適合外行人**：很好。原生元件專業、穩定，可用 Qt Style Sheets（QSS）美化到消費級。要做到「驚豔」比自由的 HTML 稍費工，但完全做得到。
- **打包難易**：PyInstaller **內建 hook，開箱可打包**；但 **exe 偏大**（數十 MB 到 100MB+ 量級，取決於收錄的 Qt 模組）。
- **授權 / 散布**：**LGPLv3——可自由散布（含商業、含閉源）**，前提是遵守 LGPL（動態連結 Qt、允許使用者替換 Qt 函式庫、附授權文字）。**這正是選 PySide6 而非本機已裝之 `PyQt5` 的關鍵理由**（PyQt5 是 GPL/商業雙授權，見 §4）。
- **維護風險**：**最低**（Qt 官方出品，6.11.1 為 2026-05 近期釋出）。
- **主要代價 / 缺點**：**下載/安裝與 exe 體積大**（需新裝 ~150MB 量級的 PySide6）；學習曲線較陡；打包產物大不利於「輕巧小工具」的觀感。
- **實作複雜度**：中—高。

### 方案三（最輕、風險最低的基準）：Tkinter + CustomTkinter 原生程式
- **一句話定位**：用 Python 內建 tkinter（本機實測可用）＋ CustomTkinter 現代化外觀，零重量級依賴、最小體積、最快落地。
- **套件組合**：stdlib `tkinter`（已驗證可開窗）＋ `customtkinter`（本機已裝 5.2.2 / 最新 6.0.0）＋ 已裝的 `darkdetect`、`pillow`。需要圖表時嵌 matplotlib（已裝）。
- **整合方式**：同 §1，走訪 dataclass 畫成 `CTkFrame` 卡片、`verdict` → 彩色 label。**資料層不動**。
- **外觀 / 適合外行人**：**誠實評估**——比原生 tkinter 好看（圓角、深/淺色、現代配色），乾淨、堪用；但**在「一眼驚豔的消費級儀表板」這件事上，仍不及方案一（Web）或方案二（Qt）**。適合「清爽夠用」而非「行銷級精美」。
- **打包難易**：PyInstaller 可行、tkinter 收錄無礙；**CustomTkinter 需額外收其資產檔**（常見要 `--collect-data customtkinter` 或加 hook，否則執行期找不到主題檔）——小坑但已知可解。exe 相對最小（~15–30MB 量級）。
- **授權 / 散布**：tkinter（PSF）＋ CustomTkinter（MIT / 本機 5.2.2 為 CC0）→ **完全自由散布**。
- **維護風險**：tkinter = CPython 核心，**極穩**；CustomTkinter = **單一維護者**專案，6.0.0（2026-06）是正面訊號，但活躍度歷史有起伏、且 5.2.2→6.0.0 破壞性變更**未查證**（見 §6）。可用「釘住已驗證可用的 5.2.2」或「必要時退回純 ttk」來降風險。
- **主要代價 / 缺點**：外觀天花板最低；CustomTkinter 單一維護者風險；升級 6.0.0 的相容性未明。
- **實作複雜度**：**低—中（三者中最低）**。

---

## 4. 授權重點（會真正影響能否自由散布）

- **PyQt5（本機已裝 5.15.11）＝ GPL v3 / 商業雙授權**。若要**自由散布一個不開源的工具**，用 PyQt5 必須**買商業授權**，否則整個程式得以 GPL 開源。**→ 本專案若要散布，不建議用已裝的 PyQt5。**來源：[PyQt vs PySide Licensing](https://www.pythonguis.com/faq/pyqt-vs-pyside/)
- **PySide6 ＝ LGPLv3（可另選 GPL）**。**可自由散布（含閉源、含商業）**，遵守 LGPL 即可（動態連結、允許替換 Qt、附授權文字）。**→ 要用 Qt 就選 PySide6，不要用 PyQt5。**
- **pywebview ＝ BSD-3**、**CustomTkinter ＝ MIT（本機 5.2.2 為 CC0）**、**DearPyGui ＝ MIT**、**Flet ＝ Apache-2.0**、**tkinter ＝ PSF**：以上**散布皆無實質限制**。
- **WebView2 Runtime**（方案一）：非 pip 套件，是微軟的系統 runtime；散布 App 時使用者機器需具備（Evergreen 版在 Win10/11 多為內建），可附微軟提供的 bootstrapper 安裝——**這是「散布依賴」而非「授權限制」**。

---

## 5. 一個橫跨方案一與資料層的共同風險（務必先煙霧測試）

`CLAUDE.md` 已載明：**MS Store 版 Python 以 pythonnet 載入原生 DLL 的相容性「尚未實測」**，是資料層動工第一步就要煙霧測試的項目。

- **方案一（pywebview）在 Windows 也走 pythonnet + WebView2**，因此**同屬這條未實測路徑**。
- **但正面看**：資料引擎 `HardwareMonitor` 本來就靠 pythonnet 載 .NET DLL；**若資料層的 pythonnet 煙霧測試通過，pywebview 這條路極可能一併可行**（同一套 `pythonnet 3.1.0`）。
- **方案二（PySide6）、方案三（Tkinter）不經 pythonnet 畫 UI**，故 UI 呈現層本身**不受這條風險影響**（資料層仍各自需要 pythonnet，但那是既有風險、與 UI 選型無關）。

---

## 6. 未查證 / 不確定 / 來源衝突事項（禁止腦補，逐條標註）

1. **CustomTkinter 5.2.2 → 6.0.0 是否有破壞性 API 變更：未查證。** GitHub Releases 頁面實測為空（該專案用 git tag / CHANGELOG，不用 GitHub Releases），未能取得 6.0.0 詳細變更清單。升級前需自行查 repo 的 CHANGELOG 或 diff。
2. **CustomTkinter 授權隨版本不同：** 本機已裝 5.2.2 的 metadata 顯示 **CC0-1.0**；PyPI 最新 6.0.0 顯示 **MIT**。兩者皆寬鬆、**都不限制散布**，但「實際適用哪個授權」取決於最後打包的是哪一版。非阻斷性，但需留意。
3. **CustomTkinter 維護活躍度：** 6.0.0（2026-06）為正面近期訊號，但為單一維護者、歷史活躍度時有討論；**本研究未精確核實其近期 commit 頻率**，標為部分未查證。
4. **pywebview 6.2.1 + PyInstaller `--noconsole` 是否仍會 crash：未查證。** crash 回報針對舊版 3.0（issue #347）；6.2.1 是否已解需**實測**。打包 HTML 靜態檔的路徑/404 坑則是**確定存在、需預先處理**的已知問題。
5. **pythonnet 在 MS Store 版 Python 3.13 載入原生元件：未實測**（見 §5，`CLAUDE.md` 既有風險項）。影響資料層與方案一，動工第一步應煙霧測試。
6. **終端使用者機器是否都有 WebView2 Runtime：** 本開發機**有**（v149，system-wide）；Win10/11 一般內建 Evergreen runtime，但**不保證每台目標機都有**，散布時需驗證或附 bootstrapper。
7. **PyInstaller 產物體積數字為社群回報的約略範圍**（PySide6 數十 MB～100MB+；pywebview 80–90MB；Tkinter+CTk ~15–30MB），**非本專案實測值**，僅供量級比較。
8. **Flet 0.85.x 是否明確支援 Python 3.13：未逐一核實**（PyPI 僅標 `Requires-Python >=3.10`）。其打包需 Flutter SDK + Visual Studio C++ workload 的重型工具鏈則已確認。

---

## 7. 結論與建議

- **主推：方案一（pywebview + 本地 HTML/CSS/JS）**。理由：(1) 對「給外行人看、要好看好懂」這個核心目標，外觀天花板最高，且本環境的 `ui-ux-pro-max` skill 能直接放大這項優勢；(2) 其 Windows runtime 依賴（pythonnet、WebView2）**本機皆已就緒**，開發機零額外安裝；(3) BSD 授權乾淨。代價是雙語言棧、打包 web 資產有已知路徑坑、且與資料層共用同一條「pythonnet 於 MS Store Python」的未實測風險（但資料層本就要測這條，通過即一併解決）。
- **原生替代：方案二（PySide6）**。若偏好「不依賴 WebView2、像真正安裝的獨立 App」，選 PySide6（**務必用 PySide6 的 LGPL，不要用已裝的 GPL 版 PyQt5**）。代價是體積大、學習曲線陡。
- **最輕基準：方案三（Tkinter + CustomTkinter）**。若要最快落地、最小體積、最低外部風險，用內建 tkinter（本機已驗證可用）＋ CustomTkinter；代價是外觀天花板最低、CustomTkinter 單一維護者風險。

---

## 來源

- [customtkinter · PyPI](https://pypi.org/project/customtkinter/)
- [TomSchimansky/CustomTkinter · GitHub](https://github.com/TomSchimansky/CustomTkinter)
- [PySide6 · PyPI](https://pypi.org/project/PySide6/)
- [PySide6-Essentials · PyPI](https://pypi.org/project/PySide6-Essentials/)
- [PyQt vs PySide Licensing: GPL vs LGPL Differences Explained · pythonguis](https://www.pythonguis.com/faq/pyqt-vs-pyside/)
- [PyQt6 vs PySide6 Licensing · pythonguis](https://www.pythonguis.com/faq/licensing-differences-between-pyqt6-and-pyside6/)
- [pywebview · PyPI](https://pypi.org/project/pywebview/)
- [pywebview 安裝文件（Windows 依賴 / WebView2 / pythonnet）](https://pywebview.flowrl.com/guide/installation.html)
- [r0x0r/pywebview · GitHub](https://github.com/r0x0r/pywebview/)
- [pywebview issue #1402（PyInstaller 打包問題）](https://github.com/r0x0r/pywebview/issues/1402)
- [pywebview issue #347（3.0 + --noconsole crash）](https://github.com/r0x0r/pywebview/issues/347)
- [pywebview issue #353（PyInstaller 產物體積）](https://github.com/r0x0r/pywebview/issues/353)
- [pyinstaller · PyPI](https://pypi.org/project/pyinstaller/)
- [flet · PyPI](https://pypi.org/project/flet/)
- [Flet 打包 Windows 文件（需 Flutter SDK + VS C++）](https://flet.dev/docs/publish/windows/)
- [dearpygui · PyPI](https://pypi.org/project/dearpygui/)
- [hoffstadt/DearPyGui · GitHub](https://github.com/hoffstadt/DearPyGui)
