@echo off
echo Stopping RoboMaster Dashboard ...
taskkill /f /im python.exe /fi "WINDOWTITLE eq RoboMasterDashboard*" >nul 2>nul
REM 按端口停止（Win7 使用 netstat 定位 PID）
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /r ":8080 .*LISTENING"') do (
  taskkill /f /pid %%a >nul 2>nul
)
echo Done.
