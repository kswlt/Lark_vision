@echo off
setlocal
cd /d C:\RoboMasterDashboard

REM Read python path recorded at install time
if exist config\python.cmd call config\python.cmd
if not defined PYTHON set PYTHON=python

set PORT=8080
set HOST=0.0.0.0

if not exist logs mkdir logs
REM NOTE: batch redirect goes to console.log, keeping app.log free for the app's RotatingFileHandler (Windows file-lock conflict)
echo [%date% %time%] Starting RoboMaster Dashboard (dataSource via .env) >> logs\console.log
%PYTHON% backend\app.py >> logs\console.log 2>&1
endlocal
