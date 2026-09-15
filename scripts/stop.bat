@echo off
REM ============================================================
REM  RoboMaster Dashboard 停止脚本（按 PID 精确停止）
REM  优先使用 app.pid 记录的 PID；无 PID 文件时按 8080 端口定位进程。
REM  不会 taskkill /f /im python.exe 误杀系统其它进程。
REM ============================================================
setlocal
cd /d %~dp0..

if exist app.pid (
  for /f %%p in (app.pid) do (
    taskkill /f /pid %%p >nul 2>nul
    echo [OK] 已停止 PID=%%p
  )
  del app.pid >nul 2>nul
  endlocal
  exit /b 0
)

REM fallback: 按端口定位 PID（仅杀监听 8080 的进程）
set "FOUND="
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /r ":8080 .*LISTENING"') do (
  taskkill /f /pid %%a >nul 2>nul
  echo [OK] 已停止 PID=%%a
  set "FOUND=1"
)
if not defined FOUND echo [WARN] 未找到运行中的 Dashboard 进程。
endlocal
