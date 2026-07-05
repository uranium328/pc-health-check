# 打包可行性驗證結果（2026-07-05）

## 結論

**本機 Microsoft Store 版 Python 3.13.14 可以直接用來建置可正常執行的 PyInstaller onefile exe，不需要另外安裝 python.org 版 Python 做建置機。**

## 驗證方式與結果

1. **基本 PyInstaller onefile 建置**：用一個 `print()` 的 hello-world 腳本跑
   `pyinstaller --onefile`，建置成功、`dist/hello.exe` 雙擊/執行皆正常輸出，
   無 `PermissionError`/`OSError` 等 MS Store 檔案系統虛擬化相關錯誤。

2. **pythonnet + HardwareMonitor 原生 DLL 載入**（本專案真正的風險點，見
   `engine.py` 模組docstring 的「未驗證事項」）：另寫一支腳本呼叫
   `pc_health_check.engine.get_engine()`（實際 import
   `HardwareMonitor.Hardware.Computer`、建立 `Computer()`、呼叫 `.Open()`），
   分別在「未凍結（直接 `python freeze_test.py`）」與「凍結（PyInstaller
   onefile + `--collect-all HardwareMonitor`）」兩種模式下執行，結果一致：

   ```
   Admin privileges are required for 'HardwareMonitor' to work properly.
   ready: True
   reason: OK
   ```

   凍結後的 exe 能正常載入 LibreHardwareMonitorLib 相關原生 DLL 並成功
   `Open()` 引擎，回傳 `ready=True`。（"Admin privileges..." 是
   HardwareMonitor 套件自己印出的警告，非例外，不影響 `ready` 狀態；正式
   打包仍應加 `--uac-admin` 讓使用者一啟動就用管理員權限執行，確保感測器
   讀值完整而非部分降級。）

## 對後續 Phase 的影響

- Phase 2（免安裝版）可直接沿用目前的 MS Store Python 環境建置，`pyinstaller/app.spec`
  不需要額外處理 python.org 建置 venv 的分支邏輯。
- `--collect-all HardwareMonitor` 已足夠讓 PyInstaller 收集到所有子模組與
  package data，未觀察到需要額外手寫 `hook-HardwareMonitor.py` 的情況；
  若後續正式打包 GUI app 時仍遇到缺檔案，再視情況補 hook。
- 未驗證項目仍保留（留給 Phase 4 在乾淨環境驗收時確認）：實際硬體感測器
  數值是否正確、UAC 提權後的行為、以及 pywebview 視窗在凍結後的靜態資源
  路徑解析。
