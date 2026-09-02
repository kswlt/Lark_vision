@echo off
cd /d C:\RoboMasterDashboard
set PYTHON=C:\Users\Administrator\AppData\Local\Programs\Python\Python38\python.exe
if not exist logs mkdir logs
echo [%date% %time%] starting >> logs\app.log
%PYTHON% backend\app.py >> logs\app.log 2>&1

