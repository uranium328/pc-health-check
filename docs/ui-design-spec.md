# UI 設計規格：電腦硬體健康檢測儀表板

依 `ops/lessons.md` L-005 決策，UI 採 pywebview + 本地 HTML/CSS/JS。本檔是套用 `ui-ux-pro-max` skill（design-system + style/color/typography/ux 四個 domain 查詢）產出的具體視覺規格，給實作 UI 骨架的人直接照做，不必重新設計。

來源查詢：`ui-ux-pro-max` skill 的 `--design-system`（health/dashboard/trustworthy 關鍵字）+ `--domain style/color/typography/ux` 補充查詢，並依專案實際需求（需同時支援亮/暗色、需要 4 級狀態徽章、非工程師受眾）調整過，非直接照搬單一查詢結果。

## 定位

- 風格基調：Minimal Flat + 卡片式資訊架構，乾淨、留白充足、圓角柔和（非 Neumorphism 的立體浮凸感、非 OLED-only 純黑、非電競 RGB／霓虹）。
- 情緒關鍵字：冷靜、值得信賴、專業但不生硬（對照 skill 的 Healthcare / Corporate Trust 分類）。
- 必須同時支援亮色與暗色模式（`prefers-color-scheme` 自動偵測 + 手動 `data-theme` 覆寫兩者都要），不能只做單一模式。

## 字體

- 標題／數值強調：**Lexend**（600/700）— skill 判定為高可讀性、無障礙友善的字體，適合非工程師受眾。
- 內文／標籤：**Source Sans 3**（400/500/600）。
- Google Fonts import：
  ```css
  @import url('https://fonts.googleapis.com/css2?family=Lexend:wght@400;500;600;700&family=Source+Sans+3:wght@400;500;600&display=swap');
  ```
  （若 pywebview 環境無網路或離線執行，需準備系統字體 fallback：`"Segoe UI", "Microsoft JhengHei", sans-serif`，不能讓字體載入失敗時整頁沒有備援字型。）
- Type scale（px）：12 / 14 / 16(base) / 18 / 24 / 32
- 內文 line-height：1.5–1.6
- 數值（溫度/使用率/轉速/電壓）：`font-variant-numeric: tabular-nums;`，字重 600，比同排標籤字級大一階，方便掃視比對。

## 色彩 Token（語意化命名，不要在元件裡寫死 hex）

### 亮色模式
```
--bg:            #ECFEFF   (頁面背景)
--card-bg:       #FFFFFF
--fg:            #164E63   (主文字)
--fg-muted:      #64748B   (次要文字)
--border:        #A5F3FC
--primary:       #0891B2   (品牌/主要互動色，例如重新整理按鈕)
--accent:        #059669
```

### 暗色模式
```
--bg:            #0F172A
--card-bg:       #1B2336
--fg:            #F8FAFC
--fg-muted:      #94A3B8
--border:        #475569
--primary:       #22D3EE
--accent:        #22C55E
```

### 狀態徽章（4 級，亮/暗各一組，皆已檢查與各自背景的對比）
| 狀態 | 亮色文字/圖示色 | 暗色文字/圖示色 | 用途 |
|---|---|---|---|
| 正常 | `#059669` | `#22C55E` | 讀數在安全範圍 |
| 注意 | `#D97706` | `#F59E0B` | 接近門檻，需留意 |
| 警告 | `#DC2626` | `#EF4444` | 已達或超過門檻 |
| 不可用 | `#64748B` | `#94A3B8` | 讀不到資料（缺權限/缺驅動/硬體不支援），中性色，不要用紅色（不可用≠警告） |

**鐵律：狀態不能只靠顏色表達**——每個徽章必須同時有「圖示 + 中文文字（正常/注意/警告/不可用）」，色弱使用者仍要能分辨。徽章底色用該狀態色的低透明度色塊（例如 `rgba(5,150,105,0.12)` 亮色 / `rgba(34,197,94,0.16)` 暗色）當背景，前景用該狀態的實色文字+圖示。

## 版面配置

1. **頂部列**：左側 App 名稱＋圖示；右側「重新整理」按鈕（含圖示）＋「最後更新：HH:MM:SS」時間戳。
2. **整體狀況橫幅**（頂部列下方，全寬）：用 4 級狀態色之一當底色調（低透明度）＋大圖示＋一行文字，例如「整體狀況：正常」／「整體狀況：有 1 項警告」。
3. **提示橫幅**（非必要時可省略，僅在非 admin／缺 PawnIO 時顯示）：中性藍/灰色調、資訊圖示（非錯誤/警告圖示），文字說明＋連結到 `docs/setup.md` 的設定步驟。不要用紅色或驚嘆號圖示，避免嚇到使用者——這只是功能受限提示，不是錯誤。
4. **元件卡片格線**：CSS Grid，`grid-template-columns: repeat(auto-fit, minmax(280px, 1fr))`；容器 gap 16px。斷點：<640px 強制單欄；640–1024px 約 2 欄；>1024px 約 3 欄（由 auto-fit + minmax 自然決定，不需寫死媒體查詢欄數，但要確認小螢幕不會橫向捲動）。
5. **卡片內部**：
   - 卡頭：元件圖示＋名稱（例如「顯示卡 NVIDIA GeForce RTX 3060 Ti」），右側放狀態徽章。
   - 卡身可用時：每個指標一行，左邊標籤（例如「溫度」）、右邊數值+單位（tabular-nums），該行若有個別判讀（例如硬碟目前溫度）可在數值後方加小徽章。
   - 卡身不可用時：中性圖示＋一句話原因（沿用 `health.py`/`report.py` 現有的白話原因文字），不要顯示空白或殘留技術字樣。
   - 卡片：`border-radius: 12px`，`border: 1px solid var(--border)`，陰影 `0 1px 3px rgba(0,0,0,.08)`（暗色模式用 `rgba(0,0,0,.4)`），內距 20px。

## 互動與動效

- 重新整理按鈕：點擊後顯示 loading 狀態（spinner 或按鈕內文字變「更新中…」+ disabled），操作耗時只要 >300ms 就要有視覺回饋，不能整頁凍結沒反應。
- 過場動畫維持 150–300ms，使用 `ease-out`；不要做超過 400ms 的轉場。
- 卡片首次載入可做淡入＋輕微上移（8px）進場動畫，逐卡 stagger 30–50ms；**必須尊重 `prefers-reduced-motion`**，該偏好開啟時直接關閉進場動畫。
- 所有可互動元素（按鈕等）要有清楚的 focus ring（鍵盤導覽可見），且 hover/press 要有視覺回饋（不需要複雜特效，顏色加深或輕微陰影即可）。

## 圖示

- 統一用同一套 SVG 線性圖示（建議 Lucide 或同等的 outline icon set，stroke 1.5–2px 一致），**不可用 emoji 當結構性圖示**。
- 五大元件建議圖示語意：主機板→電路板/晶片圖示、記憶體→記憶體條圖示、硬碟→硬碟/儲存圖示、電源供應器→插頭或電池圖示、顯示卡→顯卡圖示。
- 狀態徽章圖示建議：正常→勾選圓圈、注意→驚嘆號圓圈（非三角警示，三角警示留給「警告」）、警告→三角警示、不可用→減號/問號圓圈。

## 無障礙檢查清單（實作完成前逐項確認）

- [ ] 本文字對比 ≥ 4.5:1（亮色與暗色模式都要各自檢查，不能只驗一種模式）
- [ ] 狀態一律「圖示＋文字」並存，不單靠顏色
- [ ] 互動元素 focus ring 可見
- [ ] `prefers-reduced-motion` 有被尊重
- [ ] 小螢幕（例如視窗縮到 375px 寬）不會出現橫向捲動
- [ ] 圖示統一風格、統一 stroke 粗細

## 與既有資料層的整合原則

- 直接呼叫 `src/computer_info/report.py` 的 `generate_report()` 取得 `HealthReport`，以及 `src/computer_info/health.py` 現成的判讀/友善格式化函式，**不要在 UI 層重做健康判讀邏輯**（門檻、正常/注意/警告的判斷已經在 `health.py`，UI 只負責呈現）。
- pywebview 視窗與 Python 資料層的橋接方式（例如用 `js_api` 曝露一個「取得最新報告」的方法給前端 JS 呼叫，或是後端直接把資料序列化成 JSON 注入頁面）由實作者依 pywebview 官方建議的作法決定，只要符合「資料層不重寫、UI 只讀取現成資料」這個原則即可。
