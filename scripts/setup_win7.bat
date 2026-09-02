@echo off
REM ============================================================
REM  RoboMaster Dashboard - 希沃 Win7 一键安装/启动脚本
REM  用法：把整个项目放到 C:\RoboMasterDashboard 后，右键"以管理员身份运行"
REM  功能：检测 Python -> 装依赖 -> 记录 Python 路径 -> 防火墙 -> 开机自启 -> 启动
REM ============================================================
setlocal enabledelayedexpansion
cd /d C:\RoboMasterDashboard

echo ========================================
echo   RoboMaster Dashboard - Win7 Setup
echo ========================================
echo.

REM ---- 1. 检测 Python（Win7 上常见 C:\Python38）----
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY (
  if exist "C:\Python38\python.exe" set "PY=C:\Python38\python.exe"
)
if not defined PY (
  if exist "C:\Python39\python.exe" set "PY=C:\Python39\python.exe"
)
if not defined PY (
  echo [ERROR] 未找到 Python 3.8。请先安装 Python 3.8.x，并在安装时勾选 "Add python.exe to PATH"。
  echo         安装包: https://www.python.org/downloads/release/python-3810/
  pause
  exit /b 1
)
echo [1/5] Python: %PY%
"%PY%" --version

echo.
echo [2/5] 安装后端依赖 ...
"%PY%" -m pip install --disable-pip-version-check -r backend\requirements.txt
if errorlevel 1 (
  echo [WARN] 依赖安装失败，请检查网络。可稍后手动执行:
  echo        %PY% -m pip install -r backend\requirements.txt
)

echo.
echo [3/5] 记录 Python 路径到 config\python.cmd ...
if not exist config mkdir config
> config\python.cmd echo set PYTHON=%PY%
type config\python.cmd

echo.
echo [4/5] 防火墙规则（只放行 TCP 8080，不关防火墙）...
call scripts\firewall_win7.bat

echo.
echo [5/5] 开机自启（计划任务 ONSTART, SYSTEM 身份，无需密码）...
schtasks /query /tn "RoboMasterDashboard" >nul 2>nul
if errorlevel 1 (
  schtasks /create /tn "RoboMasterDashboard" /tr "C:\RoboMasterDashboard\scripts\start.bat" /sc onstart /ru SYSTEM /rl highest /f
  echo [OK] 已创建开机自启任务
) else (
  echo [OK] 自启任务已存在
)

echo.
echo 正在启动服务 ...
start "RoboMasterDashboard" /min call scripts\start.bat
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo   部署完成！
echo   本机访问:  http://localhost:8080
echo   局域网:    http://192.168.53.117:8080
echo   （若访问 192.168.53.117:8080 不通，检查防火墙/局域网）
echo ========================================
pause
