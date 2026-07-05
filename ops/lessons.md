# lessons：踩坑記錄（append-only）

> 格式與收編規則見 `40-maintenance.md` 第 2 節。動手做任何任務前，建議先 `grep` 本檔相關關鍵字。
> 超過 30 條未收編條目時觸發精簡週期。

## L-001 2026-07-04 標籤：dispatch
情境：驗收 CLAUDE.md/ops 部署，逐條核對「環境事實」區的模型 id 是否為可用的完整字串
坑：`10-dispatch.md` 原先規定派工一律用「完整字串」model id（如 `claude-opus-4-8`），但實測 Agent tool 的 `model` 參數是 enum 限定的短字串（`sonnet`/`opus`/`haiku`/`fable`），完整字串塞進去會違反 enum、派工會失敗
修法：已於 `10-dispatch.md` 第 3 節、`00-bootstrap.md` 診斷結果補例外說明（完整字串留書面追溯用，實際呼叫 Agent tool 要換算成短字串）；已收編至 `10-dispatch.md` 與 `00-bootstrap.md`。日後修派工規則前，先實測目標呼叫介面的實際參數限制，不能只看規則文字推論

## L-002 2026-07-04 標籤：其他（架構選型）
情境：專案剛起步，決定 Python 讀取硬體健康資訊（主機板/RAM/硬碟/PSU/GPU）的初始架構——依 `10-dispatch.md` 判準這屬於架構決策等級，需派大檔+第二意見流程，不能中檔直接拍板
坑：查證後發現，唯一能覆蓋主機板感測器與非 NVIDIA GPU 真感測的實際路徑（LibreHardwareMonitor）需要安裝 `PawnIO` 核心驅動，這與硬規則第 7 條「唯讀健康檢測，不做寫入型操作…不修改驅動程式」的字面文字有解讀灰區：工具用途純唯讀感測，但技術動作是「安裝一個新驅動」。這種「規則字面 vs 實際用途」的落差不該由 AI 自行從寬或從嚴解讀
修法：比照 `20-judgment.md` 第 6 節第 1 點流程——派 opus 做問題定義，產出「問題重述 + 3 個候選方案(A/B/C) + 各自代價」（完整比較見 `docs/framework-options.md`），不直接施作，改用 AskUserQuestion 把灰區攤開讓使用者親自裁決。使用者裁決結果：允許安裝唯讀用途的核心驅動；採方案 A（LibreHardwareMonitor 為主，見 CLAUDE.md 專案常用指令區）。日後遇到「鐵律字面 vs 實際用途」有解讀空間的情況，一律套這個模式：不自行裁決，攤開方案與代價問使用者

## L-003 2026-07-04 標籤：env
情境：驗收方案 A 骨架的 `main.py` 實跑輸出，在主對話（非 subagent）親自於 PowerShell 重跑一次做最終確認
坑：本機 PowerShell `chcp` 顯示主控台 codepage 為 65001（UTF-8），但 Python 3.13（MS Store 版）`sys.stdout.encoding` 卻抓到 `cp950`，兩者不一致導致中文輸出全部變亂碼（Bash 與 PowerShell 皆重現）。這種「chcp 顯示的 codepage」與「Python 實際偵測到的 stdout 編碼」不一致的狀況，光看 `chcp` 輸出無法發現，必須實際印中文字串出來看才驗得到
修法：在 `main.py` 加入 `_ensure_utf8_console()`，於程式一開始對 `sys.stdout`/`sys.stderr` 呼叫 `reconfigure(encoding="utf-8", errors="replace")` 強制以 UTF-8 輸出，不依賴系統 codepage 偵測。日後這台機器上任何會印中文到 stdout 的 Python CLI，起手都要加這段，不能只靠「chcp 已經是 65001」就假設輸出正常，要親自印一次中文驗證

## L-004 2026-07-05 標籤：dispatch
情境：派 subagent 修 RAM 型號亂碼與硬碟容量誤報 0 這兩個真實 bug、並重設報告格式。任務本身有交代要遵守硬規則 2（改既有檔案前先備份），subagent 自己在完成報告裡坦承「編輯前忘了先備份，事後用任務起始時 Read 到的原始內容重建」
坑：獨立 fresh-context 驗收 agent 用檔案時間戳查證，證實三個 `.bak-20260705` 備份檔的建立時間都晚於對應原始檔的修改時間（例如 `memory.py` 改於 00:27，備份卻在 00:35 才補建），確定是「先改、後補備份」而非「先備份、後改」。備份內容雖然事後比對看起來合理（與修改前應有樣貌一致），但這只是運氣好、剛好任務一開始有完整 Read 到原檔內容，不是流程本身保證的；本 repo 無 git 兜底（硬規則 6），一旦 subagent 的重建記憶有誤，將無法復原
修法：派工 prompt 裡光是在規格文字提「改任何既有檔案前先備份」不夠，subagent 不一定會照字面順序執行。日後派「實作/重構」類且涉及改動既有檔案的任務，應在驗收條件裡明確列一條「備份檔的建立時間戳必須早於對應原始檔的最後修改時間」，並要求 fresh-context 驗收 agent 逐一核對時間戳（而不是只核對備份內容看起來合不合理），把這條收編進 `ops/30-prompt-templates.md` 模板 2／模板 5 的通用驗收清單

## L-005 2026-07-05 標籤：其他（架構選型）
情境：決定專案的 UI 呈現方式（先前只有 CLI），依 `10-dispatch.md` 判準這屬於架構決策等級，比照 L-002 的模式處理
坑：候選方案（Tkinter+CustomTkinter／PySide6／pywebview／Flask+瀏覽器）在授權與打包體積上取捨互斥（例如本機已裝的 PyQt5 是 GPL，若拿來做 UI 會限制未來散布方式，必須改用 LGPL 的 PySide6），且使用者一開始並未講清楚這工具「只自己用」還是「未來會分享給別人」——這個前提會直接改變授權與打包該不該在意的權重，屬於使用者未說過的偏好，不該由 AI 自行假設
修法：先派 opus 做問題定義+研究，產出「問題重述+3個候選方案+各自代價」（完整比較見 `docs/ui-framework-options.md`），同時用 AskUserQuestion 一次問兩題：(1) 選哪個方案 (2) 未來只自己用還是可能打包分享。使用者裁決結果：採方案 pywebview + HTML/CSS/JS；未來可能打包分享給別人（因此授權乾淨與打包穩定度是選型加分項）。日後遇到「技術選型的正確答案取決於使用範圍/散布對象」這種情況，要主動把這個前提問清楚，不要只問技術選項本身

## L-006 2026-07-05 標籤：env
情境：使用者覺得 repo 資料夾名稱 `computer_info` 不適合整個專案，要求改名；連帶把 `src/computer_info/` 這個 Python 套件也一併改名為 `pc_health_check`（資料夾改叫 `pc-health-check`）
坑：直接對 `e:\program\computer_info` 做 rename（`mv`／`Rename-Item`）失敗，Windows 回報「該資料夾正被另一個行程使用中」。根因是本對話 session 的 Bash／PowerShell 工具都是把這個資料夾當作固定工作目錄的持續性 shell（PowerShell 工具每次呼叫後會被 harness 自動把 cwd 重設回這個路徑，這點在工具說明裡有提示但容易忽略），Windows 不像 POSIX 允許改名一個正被行程當作 cwd 使用的目錄
修法：改用「複製到新資料夾」繞過限制——把整個專案複製一份到新路徑（`cp -a` 並用 `diff -rq` 驗證複製後內容完全一致），所有後續改名/改 import/驗證都只在新資料夾進行，舊資料夾原封不動留給使用者之後手動刪除（等他們關閉/重開這個 session、改指向新路徑之後，舊資料夾才會真的沒有行程佔用）。日後若再遇到「要改名/移動這個 repo 本身所在的資料夾」這種需求，第一步就該預期直接 rename 可能因為 session 自身的 cwd 而失敗，直接採用「複製到新路徑＋舊資料夾留給使用者事後清理」這個路徑，不用浪費回合去反覆嘗試直接 rename

---
## 已歸檔（已收編或棄用的條目移到此區）
（尚無）
