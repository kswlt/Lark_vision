# ============================================================
# 远程自动部署脚本（在开发电脑运行）
# 前置条件：
#   1. 目标机器已安装 Win32-OpenSSH，且本机已配置 SSH Key 免密登录：
#        ssh-copy-id Administrator@<目标IP>   （或手动把公钥加入 authorized_keys）
#   2. 首次连接请先手动执行一次 ssh，接受目标主机指纹（本脚本不关闭主机指纹校验）
# 用法：
#   .\scripts\deploy.ps1 -Host 192.168.53.117 -User Administrator
#   .\scripts\deploy.ps1 -Host 192.168.53.117 -User Administrator -Key C:\Users\me\.ssh\rm_deploy_key
# 流程：
#   1. 前端 npm run build
#   2. 上传 dist 与 backend 到 <RemoteDir>
#   3. 远端安装依赖（如未装）
#   4. 通过 PID 文件优雅停止旧进程，再启动新进程（不会误杀系统其它 python）
#   5. 请求 /api/health 验证 HTTP 200
# 安全说明：脚本不使用明文密码、不使用 Invoke-Expression、不关闭主机指纹校验。
# ============================================================
param(
  [string]$Host = "192.168.53.117",
  [string]$User = "Administrator",
  [string]$Key = "",
  [string]$RemoteDir = "C:\RoboMasterDashboard"
)

$root = Split-Path -Parent $PSScriptRoot
$ErrorActionPreference = "Stop"

function Resolve-Ssh {
  if ($Key) {
    if (-not (Test-Path $Key)) { throw "SSH Key 不存在: $Key" }
    return "-i `"$Key`""
  }
  return ""
}

function Invoke-Remote {
  param([string]$Cmd)
  $sshArgs = Resolve-Ssh
  # BatchMode=yes：绝不交互输入密码（未配置免密时直接失败并给出提示）
  $result = ssh -o BatchMode=yes -o ConnectTimeout=10 $sshArgs "$User@$Host" $Cmd 2>&1
  if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] 远程命令失败: $Cmd"
    Write-Host "       请确认已配置 SSH Key 免密登录（ssh-copy-id $User@$Host），且主机指纹已接受。"
    throw "远程命令失败"
  }
  return $result
}

function Invoke-Upload {
  param([string]$Local, [string]$Remote)
  $sshArgs = Resolve-Ssh
  scp -o BatchMode=yes $sshArgs -r $Local "$User@$Host`:$Remote"
  if ($LASTEXITCODE -ne 0) { throw "上传失败: $Local" }
}

# 0. 检查远程可达
Write-Host "==> 检查 SSH 可达性"
$null = Invoke-Remote "ver"

# 1. 前端构建
Write-Host "==> npm run build"
Push-Location (Join-Path $root "frontend")
npm run build
if ($LASTEXITCODE -ne 0) { throw "前端构建失败" }
Pop-Location
if (Test-Path (Join-Path $root "dist")) { Remove-Item -Recurse -Force (Join-Path $root "dist") }
Copy-Item -Recurse (Join-Path $root "frontend\dist") (Join-Path $root "dist")

# 2. 确保远端目录
$null = Invoke-Remote "if not exist $RemoteDir mkdir $RemoteDir"

# 3. 上传
Write-Host "==> 上传 dist"
Invoke-Upload (Join-Path $root "dist") "$RemoteDir\dist"
Write-Host "==> 上传 backend"
Invoke-Upload (Join-Path $root "backend") "$RemoteDir\backend"

# 4. 远端安装依赖 + 优雅重启（PID 文件方案，不 taskkill 全部 python）
Write-Host "==> 远端安装依赖（如未装）"
$null = Invoke-Remote "cd /d $RemoteDir && python -m pip install -q -r backend\requirements.txt 2>nul || echo skip"
Write-Host "==> 优雅重启服务"
$null = Invoke-Remote "cd /d $RemoteDir && scripts\stop.bat & timeout /t 2 /nobreak >nul & cmd /c scripts\start.bat"

# 5. 健康检查
Start-Sleep -Seconds 5
$ok = $false
for ($i = 0; $i -lt 6; $i++) {
  try {
    $h = Invoke-RestMethod "http://$Host:8080/api/health" -TimeoutSec 5
    Write-Host ("[OK] health: " + ($h | ConvertTo-Json -Compress))
    $ok = $true
    break
  } catch {
    Start-Sleep -Seconds 3
  }
}
if (-not $ok) { Write-Host "[FAIL] 服务未就绪，请检查远端日志 $RemoteDir\logs\app.log" }
