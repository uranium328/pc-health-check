# project-ops-template：可移植的模型調度制度包

一套讓較低階模型（Sonnet / Haiku 等級）能穩定接管專案的制度檔案。適用於 Claude Code 或任何有 CLAUDE.md + subagent 機制的 harness。

## 包內容

```
project-ops-template/
├── README.md              ← 本檔（部署後可刪）
├── CLAUDE.md.template     ← 精簡路由型 CLAUDE.md 骨架
└── ops/
    ├── 00-bootstrap.md    ← 首次進駐診斷：環境盤點 + 三大漏洞自檢（A）
    ├── 10-dispatch.md     ← 模型調度守則：派工/升降級/驗證不自驗（C）
    ├── 20-judgment.md     ← 判斷力 rubric：升級/完成/問人/換路/品質底線（D）
    ├── 30-prompt-templates.md ← 五類派工模板：搜尋/實作/重構/研究/審查（E）
    ├── 40-maintenance.md  ← 維護協議：誰能改什麼、教訓格式、精簡週期（F）
    ├── 50-letter.md       ← 給未來 session 的信：三件事 + 退化預防（G）
    └── lessons.md         ← 踩坑記錄（空模板）
```

## 部署三步（在目標專案的第一個 session 執行）

部署步驟請看：`DEPLOY.md`

## 設計原則（改動本制度前先理解）

- **CLAUDE.md 是路由不是百科**：60 行以內，細節全在 ops/。
- **弱模型需要明確**：所有規則具體到可執行、附判準與正反例；抽象要求視同沒寫。
- **不依賴高階能力**：全部流程 Sonnet 等級可跑；超出範圍的（模糊題、品味判斷）在 `20-judgment.md` 第 6 節明寫了退場方式。
- **可長期演化**：教訓進 lessons.md、按 `40-maintenance.md` 收編與精簡，防止制度肥大或被悄悄放寬。

## 已知極限（誠實條款）

本制度補得了執行品質（拆解、驗收、多樣本評審），補不了模糊題的問題定義與品味判斷——遇到時的處置寫在 `ops/20-judgment.md` 第 6 節：升級模型、外部第二意見、或明說做不到。此外，本模板由不在目標環境內的 session 產出，`00-bootstrap.md` 的診斷程序就是為此設計的：所有環境相關事實以實地盤點為準，模板內的模型 id 僅為 2026-07 的參考值。
