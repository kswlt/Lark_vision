# -*- coding: utf-8 -*-
# SSH 闅ч亾锛氬皢鏈満 8080 鏄犲皠鍒板笇娌?192.168.53.117) 鐨?8080
# 閫氶亾缁?192.168.1.156锛圓DAM 缃戠粶宸叉湁鐨?SSH 杞彂锛夊埌杈惧笇娌冦€?# 鐢佃剳杩?ADAM_5G WiFi 鍚庯紝娴忚鍣ㄨ闂?http://localhost:8080 鍗充负甯屾矁浠〃鐩樸€?# 鏂紑/澶辫触鑷姩閲嶈繛锛?5 绉掗棿闅旓級銆?$ErrorActionPreference = "SilentlyContinue"
$ssh = "C:\Windows\System32\OpenSSH\ssh.exe"
if (-not (Test-Path $ssh)) { $ssh = "ssh" }
$key = "C:\Users\Admin\.ssh\rm_deploy_key"
$log = "C:\Users\Admin\Desktop\椋炰功鍙鍖朶RoboMasterDashboard\logs\tunnel.log"
$err = "C:\Users\Admin\Desktop\椋炰功鍙鍖朶RoboMasterDashboard\logs\tunnel_err.log"

while ($true) {
  Add-Content -Path $log -Value ("[{0}] 灏濊瘯寤虹珛 SSH 闅ч亾 ..." -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
  $p = Start-Process -FilePath $ssh `
    -ArgumentList "-N", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no", `
      "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=3", `
      "-o", "ExitOnForwardFailure=yes", "-o", "ConnectTimeout=10", `
      "-i", $key, "-L", "8080:127.0.0.1:8080", "Administrator@192.168.1.156" `
    -WindowStyle Hidden -PassThru -RedirectStandardError $err
  if ($p) {
    Add-Content -Path $log -Value "闅ч亾杩涚▼ PID=$($p.Id)锛屼繚鎸佽繍琛屼腑"
    $p.WaitForExit()
    Add-Content -Path $log -Value "闅ч亾鏂紑 (code=$($p.ExitCode))锛?5 绉掑悗閲嶈繛"
  } else {
    Add-Content -Path $log -Value "鏃犳硶鍚姩 ssh锛?5 绉掑悗閲嶈瘯"
  }
  Start-Sleep -Seconds 15
}

