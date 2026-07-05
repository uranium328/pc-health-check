# CLAUDE.md

## 專案是什麼

電腦硬體健康檢測系統：讀取並回報主機板、記憶體、硬碟、電源供應器、顯示卡等元件的健康度/狀態，讓使用者了解自己電腦的硬體狀況。
目前階段：技術棧與初始架構已於 2026-07-04 定案（見下方「專案常用指令」與 `docs/framework-options.md`），骨架程式碼尚待建立。本專案套用了 project-ops-template 這套模型調度制度（見下方路由表與 ops/ 目錄）。

## 硬規則（每個 session、每個 subagent 都必須遵守，無例外）

1. **指揮官不下場**：大量讀取（>50 行原文）、掃 repo、查網頁、批次改檔，一律派 subagent。主對話只收結論與 檔案:行號。做法見 `ops/10-dispatch.md`。
2. **改任何既有檔案前先備份**：`cp <檔> <檔>.bak-$(date +%Y%m%d)`。新內容寫新檔，不塞進舊檔。
3. **驗證不自驗**：宣稱「完成」之前，必須有 fresh-context 驗收或實跑證據。判準見 `ops/20-judgment.md` 第 2 條。
4. **同一件事最多重試兩輪**：第三次必須換方法、升級模型、或問使用者。
5. **不確定就查，查不到就標註**：禁止憑印象填工具名、路徑、模型 id、API 參數。
6. **本目錄未受 git 版控**：備份完全依賴規則 2 的 `.bak` 檔，沒有 git 可以兜底復原，改檔前的備份與改完的 read-back 要比一般專案更嚴格執行。
7. **唯讀健康檢測，不做寫入型操作**：本工具的定位是讀取並回報硬體狀態，不實作、不建議任何會修改韌體、BIOS/UEFI 設定、磁碟分割或驅動程式的操作。需要系統層級資訊讀取（如 WMI）時，只用唯讀查詢。

## 路由表（做某類事之前，先讀對應檔案）

| 情境 | 讀這個 |
|---|---|
| 新環境第一次進駐、或環境大改 | `ops/00-bootstrap.md` |
| 要派工給 subagent、選模型、選 effort | `ops/10-dispatch.md` |
| 拿不準「該不該升級／算不算完成／要不要問人／方向對不對」 | `ops/20-judgment.md` |
| 寫派工 prompt（搜尋/實作/重構/研究/審查） | `ops/30-prompt-templates.md`，直接套模板 |
| 想修改 ops/ 下任何檔案、或踩了坑要記錄 | `ops/40-maintenance.md` |
| session 開場想快速了解這套制度的來歷與陷阱 | `ops/50-letter.md` |
| 查歷史教訓（動手前 grep 相關關鍵字） | `ops/lessons.md` |

## 專案常用指令

- 技術棧：Python 3.13（本機為 Microsoft Store 版）。架構採方案 A：**LibreHardwareMonitor**（透過 `HardwareMonitor` PyPI 套件 + pythonnet 載入其 DLL）為主感測引擎，涵蓋主機板感測器、多廠牌 GPU、硬碟 SMART；記憶體/GPU 基本資訊視需要輔以 WMI（`wmi`/`pywin32`）與 `nvidia-ml-py`。決策過程、方案比較、代價取捨全文見 `docs/framework-options.md`；決策記錄見 `ops/lessons.md` L-002。
- 執行前置：需系統管理員權限；需安裝 LibreHardwareMonitor 所需的 PawnIO 核心驅動（唯讀感測用途，使用者已於 2026-07-04 明確裁決允許，見 `ops/lessons.md` L-002）。MS Store 版 Python 與 pythonnet 載入原生 DLL 的相容性尚未實測，動工時第一步應先做煙霧測試，測不過再改裝 python.org 版 Python。
- 建置：尚未建立（架構已定案但骨架程式碼尚未建立；待建立後在此補上安裝/建置指令）
- 測試：尚未建立（測試框架選定後補上；在此之前驗收一律走 `ops/30-prompt-templates.md` 模板 5 的 fresh-context read-back）
- 本 repo 沿用的模型調度制度來源：`DEPLOY.md`（project-ops-template 的部署說明）
- UI：採 **pywebview + 本地 HTML/CSS/JS** 儀表板（BSD 授權），資料來源直接呼叫既有 `report.py`/`health.py`，不重做判讀邏輯。本機開發環境 WebView2 Runtime 已就緒、零額外安裝。使用者已表態未來可能打包成 exe 分享給別人，故授權乾淨（BSD，非 GPL）與打包穩定度是選型考量之一；PyInstaller 打包 pywebview 網頁資產有已知路徑/404 坑，正式打包前需先煙霧測試。方案比較全文見 `docs/ui-framework-options.md`；決策記錄見 `ops/lessons.md` L-005。

## 環境事實（由 00-bootstrap 診斷後填入，禁止憑印象改）

- 可用模型 id：主對話目前用 `claude-sonnet-5`；環境內另可指定 `claude-opus-4-8`（升級用）、`claude-haiku-4-5-20251001`（小檔位用）、`claude-fable-5`
- subagent 機制：Agent tool（內建 agent type：claude / claude-code-guide / Explore / general-purpose / Plan / statusline-setup；本專案未建立 `.claude/agents/` 自訂 agent）
- 已裝 MCP / skill：MCP 僅 3 個待授權的 claude.ai connector（Gmail/Calendar/Drive）；Skill 見 `ops/00-bootstrap.md` 診斷結果區完整清單（含唯一第三方 plugin `ui-ux-pro-max`）
