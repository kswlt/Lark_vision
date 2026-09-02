# ============================================================
# 生成本地部署包（transport-agnostic）
# 输出：C:\RoboMasterDashboard_deploy.zip
# 拷贝到希沃后：解压到 C:\RoboMasterDashboard，右键运行 scripts\setup_win7.bat
# ============================================================
param(
  [string]$OutZip = "C:\RoboMasterDashboard_deploy.zip"
)

$ErrorActionPreference = "Stop"

# 计算项目根目录（兼容 $PSScriptRoot 为空的情形）
if ($PSScriptRoot) {
  $root = Split-Path -Parent $PSScriptRoot
} else {
  $root = (Get-Location).Path
}
Write-Host ("项目根目录: " + $root)

$stage = Join-Path $env:TEMP "rm_deploy_stage"
if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
New-Item -ItemType Directory -Force -Path $stage | Out-Null

function Copy-ProjectDir {
  param([string]$name)
  $src = Join-Path $root $name
  if (Test-Path $src) {
    $dst = Join-Path $stage $name
    New-Item -ItemType Directory -Force -Path $dst | Out-Null
    Copy-Item -Path (Join-Path $src "*") -Destination $dst -Recurse -Force
    # 剔除本地开发产物
    foreach ($drop in @(".venv", "node_modules", "__pycache__")) {
      Get-ChildItem $dst -Recurse -Directory -Filter $drop -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
    Get-ChildItem $dst -Recurse -File -Include "*.pyc", "*.pyo" -ErrorAction SilentlyContinue |
      Remove-Item -Force -ErrorAction SilentlyContinue
  } else {
    Write-Warning "缺少目录: $name（跳过）"
  }
}

function Copy-ProjectFile {
  param([string]$rel)
  $src = Join-Path $root $rel
  if (Test-Path $src) { Copy-Item $src (Join-Path $stage (Split-Path $rel -Leaf)) -Force }
}

# 前端构建
$front = Join-Path $root "frontend"
if (Test-Path (Join-Path $front "package.json")) {
  Write-Host "==> npm run build"
  Push-Location $front
  npm run build
  if ($LASTEXITCODE -ne 0) { Write-Error "前端构建失败"; exit 1 }
  Pop-Location
  if (Test-Path (Join-Path $root "dist")) { Remove-Item -Recurse -Force (Join-Path $root "dist") }
  Copy-Item -Recurse (Join-Path $front "dist") (Join-Path $root "dist")
} else {
  Write-Warning "未找到 frontend/package.json，跳过前端构建（将使用现有 dist/）"
}

# 组装
Copy-ProjectDir "backend"
Copy-ProjectDir "dist"
Copy-ProjectDir "scripts"
Copy-ProjectDir "config"
Copy-ProjectFile "README.md"
Copy-ProjectFile "backend\.env.example"

# 压缩
if (Test-Path $OutZip) { Remove-Item -Force $OutZip }
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $OutZip -Force

# 检查是否残留 .venv
$bad = Get-ChildItem (Join-Path $stage "backend") -Recurse -Directory -Filter ".venv" -ErrorAction SilentlyContinue
if ($bad) { Write-Warning "警告：部署包仍含 .venv，请检查！" }

Remove-Item -Recurse -Force $stage
Write-Host ""
Write-Host ("部署包已生成: " + $OutZip)
Write-Host "部署到希沃："
Write-Host "  1) 解压到 C:\RoboMasterDashboard"
Write-Host "  2) 把 backend\.env.example 复制为 backend\.env 并填写飞书配置（如需真实数据）"
Write-Host "  3) 右键管理员运行 scripts\setup_win7.bat"
