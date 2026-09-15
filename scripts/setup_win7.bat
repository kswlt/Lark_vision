@echo off
REM ============================================================
REM  RoboMaster Dashboard - Windows 7 / Legacy 一键安装/启动脚本
REM  用法：把项目放到任意目录（建议 C:\RoboMasterDashboard），
REM        右键以"管理员身份运行"本脚本。
REM  功能：检测 Python -> 安装依赖 -> 记录 Python 路径 -> 防火墙 ->
REM        注册计划任务（开机自启）-> 启动
REM ============================================================
setlocal enabledelayedexpansion
cd /d %~dp0..

set "ROOT=%CD%"

echo ========================================
echo   RoboMaster Dashboard - Win7 Setup
echo ========================================
echo.

REM ---- 1. 检测 Python（Win7 常见路径优先）----
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY (
  if exist "C:\Python38\python.exe" set "PY=C:\Python38\python.exe"
)
if not defined PY (
  if exist "C:\Python39\python.exe" set "PY=C:\Python39\python.exe"
)
if not defined PY (
  echo [ERROR] 未找到 Python 3.8/3.9。请先安装 Python 3.8.x，安装时勾选 "Add python.exe to PATH"。
  echo         下载: https://www.python.org/downloads/release/python-3810/
  pause
  exit /b 1
)
echo [1/5] Python: %PY%
"%PY%" --version

echo.
echo [2/5] 安装核心依赖 ...
"%PY%" -m pip install --disable-pip-version-check -r backend\requirements.txt
if errorlevel 1 (
  echo [WARN] 依赖安装失败（可能网络问题）。可稍后手动执行:
  echo        %PY% -m pip install -r backend\requirements.txt
)

echo.
echo [3/5] 记录 Python 路径到 config\python.cmd ...
if not exist config mkdir config
> config\python.cmd echo set PYTHON=%PY%
type config\python.cmd

echo.
echo [4/5] 防火墙规则（仅开放 TCP 8080，不关闭系统防火墙）...
call scripts\firewall_win7.bat

echo.
echo [5/5] 注册开机自启计划任务（ONSTART, SYSTEM 权限）...
schtasks /query /tn "RoboMasterDashboard" >nul 2>nul
if errorlevel 1 (
  schtasks /create /tn "RoboMasterDashboard" /tr "%ROOT%\scripts\start.bat" /sc onstart /ru SYSTEM /rl highest /f
  echo [OK] 已创建计划任务
) else (
  echo [OK] 计划任务已存在
)

echo.
echo 正在启动 ...
call scripts\start.bat
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo   安装完成！
echo   本机访问:   http://localhost:8080
echo   局域网访问: http://<本机IP>:8080 （需确保防火墙/路由器放行）
echo ========================================
pause
endlocal
