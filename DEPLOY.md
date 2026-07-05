# DEPLOY：部署流程（每個新專案跑一次，全程約一個 session）

## 步驟 1：把檔案放進專案（終端機執行）

```bash
# 把 <模板包路徑> 換成你解壓 project-ops-template 的位置
# 把 <專案路徑> 換成新專案根目錄
cd <專案路徑>
cp -r <模板包路徑>/ops ./ops
cp <模板包路徑>/CLAUDE.md.template ./CLAUDE.md.template
ls ops/   # 應看到 7 個 .md 檔
```

## 步驟 2：開第一個 session，貼這段（Sonnet 等級即可）

```
按 ops/00-bootstrap.md 執行首次進駐診斷，完整走完它的三個步驟：

1. 環境盤點：實際查出可用模型 id、subagent 機制、MCP、skill、記憶機制、
   effort 參數，逐項填進 00-bootstrap.md 底部的「診斷結果」區。
   查不到的寫「查不到」，禁止憑印象填。
2. 三大漏洞自檢：逐條判斷並記錄。
3. 部署：若專案已有 CLAUDE.md 先備份（cp CLAUDE.md CLAUDE.md.bak-$(date +%Y%m%d)），
   然後以 CLAUDE.md.template 為骨架建立本專案的 CLAUDE.md，
   填掉所有【】填空、刪掉 HTML 註解；舊 CLAUDE.md 仍有效的規則
   收進對應的 ops/ 檔。專案描述與常用指令不確定的，一次列出來問我。

完成後 read-back：確認 CLAUDE.md 路由表指到的每個路徑都真實存在、
沒有殘留【】填空，逐項回報 pass/fail 與證據。
```

## 步驟 3：開第二個全新 session 驗收（不要沿用步驟 2 的對話）

```
你是驗收者，與部署者無關。按 ops/30-prompt-templates.md 的模板 5，
驗收本專案的 CLAUDE.md 與 ops/ 目錄：

原始驗收條件：
1. CLAUDE.md 在 60 行以內，無殘留【】填空與 HTML 註解。
2. 路由表每個路徑真實存在（逐一 ls 驗證）。
3. 「環境事實」區的模型 id 是實際查證的完整字串，不是泛稱。
4. 00-bootstrap.md 的診斷結果區已填寫完整。
5. 各檔規則之間沒有互相矛盾的條目。

第一行回報 PASS / FAIL，逐條附證據（檔案:行號或指令輸出末行），
並以找碴立場列出至少 3 個質疑點與查證結果。FAIL 的項目直接修正後重驗。
```

## 完成判準（三項全 PASS 才算部署完成）

- [ ] 步驟 3 驗收回報 PASS
- [ ] `CLAUDE.md.template` 已可刪除（本體已生成）：`rm CLAUDE.md.template`
- [ ] 隨手開一個新 session 問「這個專案派工前要讀哪個檔？」——答得出 `ops/10-dispatch.md` 就代表路由活著

此後不需再做任何設定。踩坑記錄、規則收編、精簡週期都由 `ops/40-maintenance.md` 驅動，模型會自己觸發。
