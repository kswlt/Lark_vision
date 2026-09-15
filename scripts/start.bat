@echo off
REM ============================================================
REM  RoboMaster Dashboard 启动脚本
REM  通过 PowerShell 启动 app.py 并把 PID 写入 app.pid，
REM  供 stop.bat / deploy.ps1 按 PID 精确停止（不误杀系统其它 python）。
REM ============================================================
setlocal
cd /d %~dp0..

REM Read python path recorded at install time
if exist config\python.cmd call config\python.cmd
if not defined PYTHON set PYTHON=python

set PORT=8080
set HOST=0.0.0.0

if not exist logs mkdir logs
echo [%date% %time%] Starting RoboMaster Dashboard (dataSource via backend\.env) >> logs\console.log

REM 若旧 PID 文件残留且进程仍在，先清理
if exist app.pid (
  for /f %%p in (app.pid) do (
    tasklist /fi "PID eq %%p" 2>nul | find "%%p" >nul 2>nul && taskkill /f /pid %%p >nul 2>nul
  )
  del app.pid >nul 2>nul
)

REM 启动进程并记录 PID
powershell -NoProfile -Command "$p = Start-Process -FilePath '%PYTHON%' -ArgumentList 'backend\app.py' -WorkingDirectory '%CD%' -WindowStyle Hidden -RedirectStandardOutput ('%CD%\logs\console.log') -RedirectStandardError ('%CD%\logs\console_err.log') -PassThru; if ($p) { Set-Content -Path ('%CD%\app.pid') -Value ($p.Id) }" >nul 2>nul

timeout /t 2 /nobreak >nul
if exist app.pid (
  for /f %%p in (app.pid) do echo [OK] Dashboard 已启动 PID=%%p  http://localhost:8080
) else (
  echo [WARN] 未检测到 PID 文件，请查看 logs\console_err.log
)
endlocal
