# 免安裝版與安裝版的自動化煙霧測試。
#
# 用法（在專案根目錄、且以系統管理員身分開啟的 PowerShell 執行；需先跑過
# build_scripts\build.ps1 產生 dist\ 底下兩個 exe）：
#   powershell -File build_scripts\smoke_test.ps1
#
# 為什麼一定要用管理員權限跑：PCHealthCheck.exe 內嵌了 --uac-admin
# manifest（讀硬體感測器本來就需要系統管理員權限，見 docs/setup.md），
# 非管理員權限直接執行會觸發 UAC 提權對話框，在無人值守的自動化腳本裡會
# 卡住等不到使用者按「是」；改成整支腳本本身就以管理員身分執行，子行程
# 繼承已提權的權杖，就不會再跳提權對話框。
#
# 設計給乾淨環境（例如 Windows Sandbox）執行，驗證兩個產出真的能在使用者
# 機器上動起來，而不是只信任建置階段沒報錯——所有判斷都用回傳碼/檔案系統
# /登錄檔的實際狀態，不需要人工盯著畫面看。
$ErrorActionPreference = "Stop"

$IsAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $IsAdmin) {
    Write-Host "請以系統管理員身分重新開啟 PowerShell 後再執行本腳本（見腳本開頭註解說明原因）。"
    exit 1
}

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PortableExe = Join-Path $ProjectRoot "dist\PCHealthCheck.exe"
$SetupExe = Join-Path $ProjectRoot "dist\PCHealthCheckSetup.exe"

$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\PCHealthCheck"
$ShortcutDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$UninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\PCHealthCheck"

if (-not (Test-Path $PortableExe)) {
    throw "找不到 $PortableExe，請先執行 build_scripts\build.ps1"
}
if (-not (Test-Path $SetupExe)) {
    throw "找不到 $SetupExe，請先執行 build_scripts\build.ps1"
}

# 測試前先清乾淨，讓腳本可以重複執行（例如上次跑到一半失敗留下殘留）。
if (Test-Path $InstallDir) { Remove-Item -Recurse -Force $InstallDir -ErrorAction SilentlyContinue }
if (Test-Path $UninstallKey) { Remove-Item -Recurse -Force $UninstallKey -ErrorAction SilentlyContinue }

$script:Failures = @()

function Test-Step {
    param([string]$Name, [scriptblock]$Check)
    Write-Host "[TEST] $Name"
    try {
        if (& $Check) {
            Write-Host "  PASS"
        } else {
            Write-Host "  FAIL"
            $script:Failures += $Name
        }
    } catch {
        Write-Host "  FAIL (exception: $($_.Exception.Message))"
        $script:Failures += $Name
    }
}

function Get-RecentShortcutCount {
    Get-ChildItem $ShortcutDir -Filter "*.lnk" -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -gt (Get-Date).AddMinutes(-5) } |
        Measure-Object | Select-Object -ExpandProperty Count
}

# --- 免安裝版 ---

Test-Step "portable exe --selftest 回傳 0" {
    & $PortableExe --selftest | Out-Null
    $LASTEXITCODE -eq 0
}

Test-Step "portable exe 能開啟且視窗有回應" {
    $proc = Start-Process -FilePath $PortableExe -PassThru
    Start-Sleep -Seconds 5
    $ok = $false
    try {
        $p = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
        $ok = ($null -ne $p) -and $p.Responding
    } finally {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    $ok
}

# --- 安裝版：安裝 ---

Test-Step "installer -y 安裝後檔案/捷徑/登錄機碼都存在" {
    & $SetupExe -y | Out-Null
    $exeOk = Test-Path (Join-Path $InstallDir "PCHealthCheck.exe")
    $uninstOk = Test-Path (Join-Path $InstallDir "Uninstall.exe")
    $shortcutOk = (Get-RecentShortcutCount) -gt 0
    $regOk = Test-Path $UninstallKey
    $exeOk -and $uninstOk -and $shortcutOk -and $regOk
}

# --- 安裝版：解除安裝 ---

Test-Step "Uninstall.exe --uninstall -y 移除捷徑/登錄機碼/主體" {
    $uninstallerExe = Join-Path $InstallDir "Uninstall.exe"
    & $uninstallerExe --uninstall -y | Out-Null
    $exeGone = -not (Test-Path (Join-Path $InstallDir "PCHealthCheck.exe"))
    $shortcutGone = (Get-RecentShortcutCount) -eq 0
    $regGone = -not (Test-Path $UninstallKey)
    $exeGone -and $shortcutGone -and $regGone
}

# 已知殘留（見 installer.py 的 uninstall() 說明）：Uninstall.exe 本身與安裝
# 目錄不會被自動刪除，這裡順手清掉，不影響上面測試結果的判定。
if (Test-Path $InstallDir) { Remove-Item -Recurse -Force $InstallDir -ErrorAction SilentlyContinue }

if ($script:Failures.Count -eq 0) {
    Write-Host "`n全部煙霧測試通過。"
    exit 0
} else {
    Write-Host "`n以下測試失敗："
    $script:Failures | ForEach-Object { Write-Host "  - $_" }
    exit 1
}
