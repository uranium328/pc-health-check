# 00-bootstrap：首次進駐診斷（新專案第一個 session 必跑，跑完即歸檔）

> 讀者：任何等級的模型。目的：把「這個環境長什麼樣」從猜測變成落檔事實。
> 本檔跑完一次後，把結果寫進本檔底部的「診斷結果」區，之後的 session 只讀結果、不重跑（除非環境明顯變了）。

## 第一步：環境盤點（逐項執行，查不到就寫「查不到」，禁止憑印象填）

依序執行並記錄結果：

1. **可用模型與型號字串**：執行 `claude --help` 或查 `/model` 指令、`.claude/settings.json`、`ANTHROPIC_MODEL` 環境變數。把實際可用的 model id 原文抄下來（例如 `claude-sonnet-4-6`）。不要寫「Sonnet」這種泛稱，派工時要用完整字串。
2. **subagent 機制**：確認是否有 Task tool / subagent 可派。查 `.claude/agents/` 目錄是否有自訂 agent 定義。記下每個 agent 的名字與用途。
3. **CLAUDE.md 現況**：`wc -l CLAUDE.md`，並記下它引用了哪些其他檔案。
4. **MCP 與 skill**：執行 `claude mcp list` 或查設定檔；查 `.claude/skills/` 或 `~/.claude/skills/`。逐一記名字。
5. **記憶機制**：確認是否有 auto-memory、`# 記憶` 指令、或專案內約定的 lessons 檔。
6. **effort / thinking 參數**：查當前環境是否支援 effort 或 extended thinking 設定，語法是什麼。查不到就記「本環境無此參數」。

## 第二步：三大常見漏洞自檢（附判準與修法）

以下是 agent harness 最常見的三種失效模式。逐條對照你剛盤點的環境，判斷是否命中，命中就把修法寫進 CLAUDE.md 的硬規則區。

### 漏洞 1：主對話下場做大量讀取（最漏 token）
- **判準**：翻最近的對話紀錄或憑本次 session 觀察——主對話裡是否出現整檔 `cat`、整頁網頁內容、超過 50 行的檔案原文貼進主 context？
- **為什麼致命**：主對話 context 是全 session 共用資源，被原始資料淹掉後，後面每一步的判斷品質都下降，而且不可逆。
- **修法**：寫死規則「大量讀取、掃 repo、查網頁、批次改檔一律派 subagent，主對話只收結論與 檔案:行號」。詳見 `10-dispatch.md`。

### 漏洞 2：無驗收條件的派工與自我驗證（最容易出錯）
- **判準**：派工 prompt 裡是否缺「驗收條件」？做完的東西是否由同一個寫它的 context 自己說「完成了」？
- **為什麼致命**：寫程式的 context 驗自己的程式，會繼承同一套錯誤假設；「看起來對」不等於「跑得動」。
- **修法**：派工一律用 `30-prompt-templates.md` 的模板（含驗收條件填空）；驗收一律派 fresh-context agent，程式碼用測試或實跑、檔案用 read-back。詳見 `10-dispatch.md` 的「驗證不自驗」。

### 漏洞 3：重試循環（最容易失焦）
- **判準**：同一個錯誤、同一種方法，是否重試超過 2 次？context 裡是否出現連續多輪相似的失敗輸出？
- **為什麼致命**：重試不改變方法只燒 token，而且失敗輸出堆在 context 裡會讓模型愈來愈傾向重複同樣的錯。
- **修法**：硬上限「同一件事最多重試兩輪」，第三次必須換路：升級模型、換方法、或停下問使用者。判斷「該升級」見 `20-judgment.md` 第 1 條、「該換路」見第 4 條。

## 第三步：部署模板

1. 若專案已有 CLAUDE.md：`cp CLAUDE.md CLAUDE.md.bak-$(date +%Y%m%d)` 先備份。
2. 用 `CLAUDE.md.template` 為骨架重寫：舊內容中仍有效的規則收進對應的 ops/ 檔案，CLAUDE.md 本體只留路由與硬規則（目標 60 行以內）。
3. 把 ops/ 目錄複製進專案（建議放 `.claude/ops/` 或專案根目錄 `ops/`，路由表裡的路徑要跟著改）。
4. 把第一、二步的盤點結果填進本檔底部。
5. 跑一次 read-back：逐檔 `head -5` 確認每個被路由表引用的檔案真實存在。路由指向不存在的檔案，等於沒寫。

## 診斷結果（首次 session 填寫）

```
盤點日期：2026-07-04

可用模型（完整 id）：
  主對話目前使用：claude-sonnet-5（本 session 內使用者剛執行 `/model sonnet`，
    回應「Set model to claude-sonnet-5」；系統層亦明載 exact model ID 為 claude-sonnet-5）。
  環境內另有可指定的 id：claude-opus-4-8（Opus 4.8，升級檔位用）、
    claude-haiku-4-5-20251001（Haiku 4.5，小檔位用）、claude-fable-5（Fable 5）。
  全域 ~/.claude/settings.json 記的是泛稱 "model": "sonnet"，不是完整 id，派工時不可引用這行。
  環境變數 ANTHROPIC_MODEL：查不到（env 內無此 key）。
  備註：本 shell 的 PATH 內查不到 `claude` 執行檔（which/--version 皆失敗）——
    這是透過 VS Code 擴充套件（Antigravity IDE 內 anthropic.claude-code-2.1.201）
    以 SDK 模式呼叫，不是獨立終端機 CLI，所以 `claude --help`、`claude mcp list`
    這類指令在本環境的 Bash 工具裡不可執行，只能查設定檔佐證。

subagent 機制：
  Agent tool 存在且可直接呼叫（非 deferred tool），支援 model 覆寫、
    isolation（worktree/remote）、run_in_background 等參數，但沒有 per-call
    的 reasoning effort 欄位。
  查無 `.claude/agents/`（專案內、全域皆不存在）——沒有自訂 agent 定義檔。
  可派的 agent type 是 harness 內建（非本地檔案，系統直接告知清單）：
    claude（catch-all）、claude-code-guide（Claude Code/SDK/API 問答專用）、
    Explore（唯讀搜尋）、general-purpose（多步驟研究/執行）、
    Plan（架構規劃，唯讀）、statusline-setup。
  （2026-07-04 驗收 session 補充查證，證據：Agent tool 的參數 schema）
    Agent tool 的 `model` 參數實測是 enum 限定的短字串，只接受
    `sonnet`/`opus`/`haiku`/`fable` 四個值，不接受本檔上方記錄的完整
    id 字串（如 `claude-opus-4-8`）。這與 `10-dispatch.md` 原先「每次
    派工都明寫 model id（完整字串）」的指示有落差，已於 10-dispatch.md
    第 3 節補一條例外說明（見該檔 2026-07-04 修訂）：完整字串留給書面
    記錄追溯用，實際呼叫 Agent tool 時要換算成對應短字串。

CLAUDE.md 現況：
  `wc -l CLAUDE.md` = 39 行（2026-07-04 這版；含空行，無 frontmatter，
    結尾以換行結尾、無多餘空行）。遠低於路由表本身要求的「60 行以內」
    目標，也遠低於 `40-maintenance.md` 精簡週期的 80 行硬觸發門檻。
  引用的其他檔案：路由表引用 `ops/00-bootstrap.md`、`ops/10-dispatch.md`、
    `ops/20-judgment.md`、`ops/30-prompt-templates.md`、
    `ops/40-maintenance.md`、`ops/50-letter.md`、`ops/lessons.md` 共 7 個
    ops/ 檔；「專案常用指令」區另引用 `DEPLOY.md`。以上 8 個路徑已逐一用
    `test -f` 驗證存在，無斷鏈。

MCP / skill 清單：
  MCP：`claude mcp list` 不可執行（CLI 不在 PATH），改查
    ~/.claude/mcp-needs-auth-cache.json，查到 3 個已設定但「尚未授權」的
    claude.ai connector：claude.ai Gmail、claude.ai Google Calendar、
    claude.ai Google Drive。本 session 無法使用其工具，需使用者在
    claude.ai connector 設定或 /mcp 完成授權。未查到其他 MCP server。
  Skill：查無 `.claude/skills/`（專案與全域皆無本地檔案）。系統層告知的可用
    skill 清單為：ui-ux-pro-max:ui-ux-pro-max（唯一第三方 plugin skill，
    來自 marketplace nextlevelbuilder/ui-ux-pro-max-skill，已在全域
    settings.json 的 enabledPlugins 啟用）；其餘 dataviz、artifact-design、
    update-config、keybindings-help、verify、code-review、simplify、
    fewer-permission-prompts、loop、schedule、claude-api、run、init、
    review、security-review 為 harness/擴充套件內建（不是本地可編輯檔案）。

記憶機制：
  確認為 auto-memory 檔案系統，路徑
    C:\Users\Shinichicken\.claude\projects\e--program-computer-info\memory\，
    目前為空目錄（本專案第一次有 session，尚無任何記憶檔或 MEMORY.md）。
  機制：MEMORY.md 為索引檔（每個 session 自動載入），個別記憶檔用
    frontmatter 標記 type（user/feedback/project/reference），語意式組織。
  與本模板既有的 `ops/lessons.md` 是兩套並存但不同層的機制：auto-memory
    是 harness 全域機制、寫在使用者主目錄下、不進 repo；lessons.md 是這套
    ops 模板自帶、寫進 repo 本身、給任何接手這個 repo 的模型看的踩坑記錄。
    兩者不互相取代，記教訓時兩邊都可能要寫（跨專案通用的教訓才寫 auto-memory）。

effort 參數：
  存在。環境變數 CLAUDE_EFFORT=xhigh，且全域 settings.json 有
    "effortLevel": "xhigh"。這是全域分級設定，可能透過類似 /model 的
    slash 指令調整（本次觀察到的是 /model，effort 調整指令名稱查不到）。
  從 code-review skill、ReportFindings 工具等處觀察到的分級詞彙是
    low / medium / high / xhigh / max，共 5 檔——比本模板 10-dispatch.md
    原先假設的「小/中/大」3 檔模型階梯更細；兩者是不同維度（model 選哪顆、
    effort 選多用力想），不要混用。
  Agent tool 呼叫本身沒有 per-call 的 effort 參數（只有 model / isolation /
    run_in_background 等）；per-agent 的 reasoning effort 由該 agent 定義的
    frontmatter 設定，但本環境未建立任何 `.claude/agents/*.md`，確切
    frontmatter 欄位名稱查不到（無範例檔可查證，禁止憑印象填）。

三大漏洞命中情況：
  漏洞1（主對話下場）：命中，但有正當理由。
    證據：本次為了盤點，把 00-bootstrap.md、10~50 五個 ops 檔、lessons.md、
      CLAUDE.md.template、DEPLOY.md、README.md 共 9 個檔案（合計約 480 行）
      整檔讀進主對話，遠超過判準的 50 行。
    理由：這批檔案是「部署與盤點」這個任務本身的規格輸入——CLAUDE.md 之所以
      要求路由表存在，就是為了讓主對話（未來的指揮官）記得規則本文，這次是
      建置規則本身，不是可以外包給 subagent 摘要轉述的「原始資料收集」；
      若改由 subagent 讀後摘要，反而會在部署階段就開始失真。
    修正／記錄：日後若同一批 ops 檔案只是要「查一條規則」而非重新盤點/部署，
      應改用 Grep/Explore 只取需要的段落，不應整檔重讀。

  漏洞2（無驗收派工）：未命中（本次尚未派工），但下一步有已知風險先記下。
    證據：截至目前 session 尚未呼叫 Agent tool，沒有派工，所以此漏洞在
      「盤點」這步不適用。
    已知風險：本次部署（第三步）結束後的「完成」宣告，若由本 session
      自己 read-back 自己剛寫的 CLAUDE.md，屬於自驗，不合格。
    修正：DEPLOY.md 步驟 3 已明寫要開全新 session 驗收，本次執行只做部署者
      該做的 read-back（確認路徑存在、無殘留【】），不宣稱「已通過驗收」，
      並在回報中明確提醒使用者還需要開新 session 跑步驟 3。

  漏洞3（重試循環）：未命中。
    證據：本次尚未出現同一件事重試的情況。

已採取的修正：
  1. 派工／查規則時，優先用 Grep/Explore 抓「需要的那幾行」，不整檔重讀
     已經讀過的 ops 檔（本次盤點是必要的一次性例外，未來 session 不應
     重跑此步驟，只讀本區塊的結論）。
  2. 「完成部署」與「驗收通過」分開宣告：本 session 只做到部署 +
     部署者自查（read-back），驗收 PASS/FAIL 留給 DEPLOY.md 步驟 3
     的全新 session 判定。
  3. 記下 effort 為 5 檔（low/medium/high/xhigh/max）而非模板假設的 3 檔，
     日後修 10-dispatch.md 時應把這個維度差異寫清楚，避免和模型階梯搞混。
```
