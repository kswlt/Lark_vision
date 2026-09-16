# ============================================================
# SSH 隧道脚本：将本机 <LocalPort> 端口映射到远端主机的 Dashboard 端口。
# 适用场景：本机与目标机器不在同一网段，需经跳板机建立 SSH 隧道访问。
#
# 用法（必填 -Target 和 -Key）：
#   .\scripts\start_tunnel.ps1 -Target Administrator@192.168.1.100 -Key C:\Users\you\.ssh\id_ed25519
#   .\scripts\start_tunnel.ps1 -Target user@host -Key C:\path\to\key -LocalPort 8080 -RemotePort 8080
#
# 安全说明：
#   - 使用 SSH Key 认证（BatchMode=yes，不交互输密码）
#   - 首次连接会自动接受主机指纹（accept-new），之后校验指纹
#   - 断线/失败自动重连（15 秒间隔）
# ============================================================
param(
  [Parameter(Mandatory=$true)][string]$Target,
  [Parameter(Mandatory=$true)][string]$Key,
  [int]$LocalPort = 8080,
  [int]$RemotePort = 8080,
  [string]$RemoteBind = "127.0.0.1",
  [string]$LogDir = ""
)

if (-not (Test-Path $Key)) {
  Write-Host "[error] SSH Key 不存在: $Key" -ForegroundColor Red
  exit 1
}

$ErrorActionPreference = "SilentlyContinue"
if (-not $LogDir) { $LogDir = Join-Path (Split-Path -Parent $PSScriptRoot) "logs" }
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$log = Join-Path $LogDir "tunnel.log"
$err = Join-Path $LogDir "tunnel_err.log"

$ssh = "C:\Windows\System32\OpenSSH\ssh.exe"
if (-not (Test-Path $ssh)) { $ssh = "ssh" }

while ($true) {
  Add-Content -Path $log -Value ("[{0}] 尝试建立 SSH 隧道 {1}:{2} -> {3}:{4} ..." -f `
    (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $LocalPort, $RemoteBind, $Target, $RemotePort)
  $p = Start-Process -FilePath $ssh `
    -ArgumentList "-N", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new", `
      "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=3", `
      "-o", "ExitOnForwardFailure=yes", "-o", "ConnectTimeout=10", `
      "-i", $Key, "-L", "$LocalPort`:$RemoteBind`:$RemotePort", $Target `
    -WindowStyle Hidden -PassThru -RedirectStandardError $err
  if ($p) {
    Add-Content -Path $log -Value "隧道进程 PID=$($p.Id)，保持运行中（访问 http://localhost:$LocalPort）"
    $p.WaitForExit()
    Add-Content -Path $log -Value "隧道断开 (code=$($p.ExitCode))，15 秒后重连"
  } else {
    Add-Content -Path $log -Value "无法启动 ssh，15 秒后重试"
  }
  Start-Sleep -Seconds 15
}
