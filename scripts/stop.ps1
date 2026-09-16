# ============================================================
# RM CONTROL — Windows 停止脚本（按 PID 精确停止）
# 优先 app.pid；无 PID 文件时按 8080 端口定位监听进程。
# 不会 taskkill /f /im python.exe 误杀系统其它 python。
# ============================================================
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (Test-Path "app.pid") {
    $pid_ = Get-Content "app.pid" -ErrorAction SilentlyContinue
    if ($pid_) {
        try {
            Stop-Process -Id $pid_ -Force -ErrorAction Stop
            Write-Host "[ok] 已停止 PID=$pid_" -ForegroundColor Green
        } catch {
            Write-Host "[warn] 停止 PID=$pid_ 失败（可能已退出）" -ForegroundColor Yellow
        }
    }
    Remove-Item "app.pid" -ErrorAction SilentlyContinue
    exit 0
}

# fallback: 按 8080 端口定位
$found = $false
try {
    $conns = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        try {
            Stop-Process -Id $c.OwningProcess -Force -ErrorAction Stop
            Write-Host "[ok] 已停止 PID=$($c.OwningProcess)（监听 8080）" -ForegroundColor Green
            $found = $true
        } catch { }
    }
} catch { }
if (-not $found) { Write-Host "[warn] 未找到运行中的 Dashboard 进程" -ForegroundColor Yellow }
