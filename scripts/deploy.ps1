# ============================================================
# 远程自动部署脚本（在开发电脑运行）
# 前置条件：开发电脑能 ssh/scp 到 192.168.53.117（Win32-OpenSSH）
# 用法：
#   .\scripts\deploy.ps1 -Host 192.168.53.117 -User Administrator -Password xxx
# 流程：
#   1. 前端 npm run build
#   2. 上传 dist 与 backend/scripts 到 C:\RoboMasterDashboard
#   3. 远程重启 Waitress
#   4. 请求 /api/health 验证 HTTP 200
# ============================================================
param(
  [string]$Host = "192.168.53.117",
  [string]$User = "Administrator",
  [string]$Password = "",
  [string]$RemoteDir = "C:\RoboMasterDashboard"
)

$root = Split-Path -Parent $PSScriptRoot
$ErrorActionPreference = "Stop"

function Invoke-Remote {
  param([string]$Cmd)
  if ($Password) {
    # 用 plink（PuTTY）免交互传密码；若没有 plink，退回 ssh（需已配置免密）
    $plink = Get-Command plink -ErrorAction SilentlyContinue
    if ($plink) {
      $script = "echo y | plink -ssh $User@$Host -pw $Password `"$Cmd`""
      Invoke-Expression $script
      return
    }
  }
  ssh -o StrictHostKeyChecking=no "$User@$Host" $Cmd
  if ($LASTEXITCODE -ne 0) { throw "远程命令失败: $Cmd" }
}

function Invoke-Upload {
  param([string]$Local, [string]$Remote)
  if ($Password -and (Get-Command pscp -ErrorAction SilentlyContinue)) {
    Invoke-Expression "pscp -pw $Password -r $Local $User@$Host`:$Remote"
  } else {
    scp -r $Local "$User@$Host`:$Remote"
    if ($LASTEXITCODE -ne 0) { throw "上传失败: $Local" }
  }
}

# 0. 检查远程可达
Write-Host "==> 检查 SSH 可达性"
ssh -o BatchMode=yes -o ConnectTimeout=8 "$User@$Host" "ver" 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "[FAIL] SSH 不可用。请先解决远程访问（安装 Win32-OpenSSH 或提供密码），"
  Write-Host "       或改用离线部署：运行 .\scripts\build_bundle.ps1 生成部署包，U盘拷贝到希沃执行 setup_win7.bat。"
  exit 1
}

# 1. 前端构建
Write-Host "==> npm run build"
Push-Location (Join-Path $root "frontend")
npm run build
if ($LASTEXITCODE -ne 0) { throw "前端构建失败" }
Pop-Location
if (Test-Path (Join-Path $root "dist")) { Remove-Item -Recurse -Force (Join-Path $root "dist") }
Copy-Item -Recurse (Join-Path $root "frontend\dist") (Join-Path $root "dist")

# 2. 确保远端目录
Invoke-Remote "if not exist $RemoteDir mkdir $RemoteDir"

# 3. 上传
Write-Host "==> 上传 dist"
Invoke-Upload (Join-Path $root "dist") "$RemoteDir\dist"
Write-Host "==> 上传 backend"
Invoke-Upload (Join-Path $root "backend") "$RemoteDir\backend"
Write-Host "==> 上传 scripts"
Invoke-Upload (Join-Path $root "scripts") "$RemoteDir\scripts"

# 4. 远端安装依赖 + 重启
Write-Host "==> 远端安装依赖（如未装）"
Invoke-Remote "cd /d $RemoteDir && python -m pip install -q -r backend\requirements.txt 2>nul || echo skip"
Write-Host "==> 重启服务"
Invoke-Remote "taskkill /f /im python.exe >nul 2>nul & timeout /t 2 /nobreak >nul & start /min `"RoboMasterDashboard`" $RemoteDir\scripts\start.bat"

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
if (-not $ok) { Write-Host "[FAIL] 服务未就绪，请检查远端日志 C:\RoboMasterDashboard\logs\app.log" }
