# ============================================================
# RM CONTROL — Windows 一键初始化（首次部署）
# 用法：在项目根目录 PowerShell 中执行
#   .\scripts\setup.ps1
# 幂等：已存在 .venv / .env / team.yaml 不会被覆盖。
# ============================================================
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "== RM CONTROL setup (Windows) ==" -ForegroundColor Cyan

# ---------- 1. Python ----------
$pythonCmd = $null
foreach ($c in @("python", "py", "python3")) {
    try {
        $v = & $c --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $pythonCmd = $c
            Write-Host "[ok] Python found: $v ($c)"
            break
        }
    } catch { }
}
if (-not $pythonCmd) {
    Write-Host "[error] 未找到 python。请安装 Python 3.11+（https://www.python.org/downloads/）" -ForegroundColor Red
    exit 1
}

# ---------- 2. .venv ----------
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[..] 创建虚拟环境 .venv ..."
    & $pythonCmd -m venv .venv
    if ($LASTEXITCODE -ne 0) { Write-Host "[error] venv 创建失败" -ForegroundColor Red; exit 1 }
}
$venvPy = Join-Path $root ".venv\Scripts\python.exe"
Write-Host "[ok] 使用虚拟环境: $venvPy"

# ---------- 3. backend 依赖 ----------
Write-Host "[..] 安装 backend/requirements.txt ..."
& $venvPy -m pip install --upgrade pip
& $venvPy -m pip install -r backend\requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Host "[error] backend 依赖安装失败" -ForegroundColor Red; exit 1 }

# ---------- 4. Node ----------
$nodeCmd = $null
foreach ($c in @("node", "nodejs")) {
    try {
        $v = & $c --version 2>&1
        if ($LASTEXITCODE -eq 0) { $nodeCmd = $c; Write-Host "[ok] Node found: v$v"; break }
    } catch { }
}
if (-not $nodeCmd) {
    Write-Host "[error] 未找到 node。请安装 Node.js LTS（https://nodejs.org/）" -ForegroundColor Red
    exit 1
}

# ---------- 5. frontend 依赖 + build ----------
Push-Location frontend
Write-Host "[..] 安装 frontend 依赖 (npm ci --legacy-peer-deps) ..."
npm ci --legacy-peer-deps
if ($LASTEXITCODE -ne 0) { Write-Host "[error] frontend 依赖安装失败" -ForegroundColor Red; Pop-Location; exit 1 }
Write-Host "[..] 构建 frontend (npm run build) ..."
npm run build
if ($LASTEXITCODE -ne 0) { Write-Host "[error] frontend build 失败" -ForegroundColor Red; Pop-Location; exit 1 }
Pop-Location

# ---------- 6. 配置文件 ----------
if (-not (Test-Path "backend\.env")) {
    Copy-Item "backend\.env.example" "backend\.env"
    Write-Host "[ok] 已创建 backend\.env（首次部署默认 DATA_SOURCE=mock, CAMERA_ENABLED=false）" -ForegroundColor Green
} else {
    Write-Host "[skip] backend\.env 已存在，未覆盖"
}
if (-not (Test-Path "backend\config\team.yaml")) {
    Copy-Item "backend\config\team.example.yaml" "backend\config\team.yaml"
    Write-Host "[ok] 已创建 backend\config\team.yaml" -ForegroundColor Green
} else {
    Write-Host "[skip] backend\config\team.yaml 已存在，未覆盖"
}

# ---------- 7. 目录 ----------
foreach ($d in @("logs", "data")) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d | Out-Null }
}

Write-Host ""
Write-Host "== Setup 完成 ==" -ForegroundColor Green
Write-Host "启动:  .\scripts\start.ps1"
Write-Host "停止:  .\scripts\stop.ps1"
Write-Host "访问:  http://localhost:8080"
Write-Host "配置:  编辑 backend\.env 切换 DATA_SOURCE=feishu + 填入飞书凭证"
