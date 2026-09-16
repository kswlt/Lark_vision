# ============================================================
# RM CONTROL — Windows 启动脚本
# 用法：.\scripts\start.ps1
# PID 写入 app.pid，stop.ps1 按 PID 精确停止（不误杀系统其它 python）。
# ============================================================
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$venvPy = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "[error] 未找到虚拟环境: $venvPy" -ForegroundColor Red
    Write-Host "请先运行: .\scripts\setup.ps1" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path "logs")) { New-Item -ItemType Directory -Path logs | Out-Null }

# 清旧 PID
if (Test-Path "app.pid") {
    $oldPid = Get-Content "app.pid" -ErrorAction SilentlyContinue
    if ($oldPid) {
        try { Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue } catch { }
    }
    Remove-Item "app.pid" -ErrorAction SilentlyContinue
}

$outLog = Join-Path $root "logs\console.log"
$errLog = Join-Path $root "logs\console_err.log"

Write-Host "== 启动 RM CONTROL ==" -ForegroundColor Cyan
$p = Start-Process -FilePath $venvPy `
    -ArgumentList "backend\app.py" `
    -WorkingDirectory $root `
    -WindowStyle Hidden `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog `
    -PassThru
if ($p) {
    Set-Content -Path "app.pid" -Value $p.Id
    Start-Sleep -Seconds 2
    Write-Host "[ok] Dashboard 已启动 PID=$($p.Id)  http://localhost:8080" -ForegroundColor Green
    Write-Host "日志: logs\console.log  /  logs\console_err.log"
} else {
    Write-Host "[error] 启动失败，请查看 logs\console_err.log" -ForegroundColor Red
    exit 1
}
