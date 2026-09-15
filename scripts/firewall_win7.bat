@echo off
REM ============================================================
REM  Windows 防火墙规则：仅开放 TCP 8080（RoboMaster Dashboard）
REM  不关闭系统防火墙。规则已存在则跳过。
REM ============================================================
setlocal
netsh advfirewall firewall show rule name="RoboMaster Dashboard" >nul 2>nul
if errorlevel 1 (
  netsh advfirewall firewall add rule name="RoboMaster Dashboard" dir=in action=allow protocol=TCP localport=8080
  echo [OK] 已添加防火墙规则: TCP 8080
) else (
  echo [OK] 防火墙规则已存在，跳过
)
netsh advfirewall firewall show rule name="RoboMaster Dashboard"
endlocal
