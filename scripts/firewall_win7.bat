@echo off
REM Win7 防火墙：只放行 TCP 8080（局域网），不关闭整个防火墙。
REM 检查是否已有同名规则，避免重复添加。
setlocal
netsh advfirewall firewall show rule name="RoboMaster Dashboard" >nul 2>nul
if errorlevel 1 (
  netsh advfirewall firewall add rule name="RoboMaster Dashboard" dir=in action=allow protocol=TCP localport=8080
  echo [OK] 已添加防火墙规则：TCP 8080 入站放行
) else (
  echo [OK] 防火墙规则已存在，跳过
)
netsh advfirewall firewall show rule name="RoboMaster Dashboard"
endlocal
