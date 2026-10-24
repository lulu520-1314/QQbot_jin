# 一键在「开始菜单 → 小鲸服务」创建三个启动快捷方式
# 用法：右键本文件 → 使用 PowerShell 运行
#      或：powershell -ExecutionPolicy Bypass -File create-shortcuts.ps1

$ErrorActionPreference = "Stop"

# ===== 改成你自己的路径 =====
$Root      = "D:\software\QQBot"
$VoiceRoot = "D:\software\Voice"
$Python    = Join-Path $VoiceRoot "py310\python.exe"
# ============================

$startMenu = Join-Path ([Environment]::GetFolderPath("Programs")) "小鲸服务"
New-Item -ItemType Directory -Force -Path $startMenu | Out-Null

$ws = New-Object -ComObject WScript.Shell

function New-Lnk {
    param([string]$Name, [string]$Target, [string]$Arguments = "", [string]$WorkDir = "", [string]$Icon = "")
    $lnk = $ws.CreateShortcut((Join-Path $startMenu $Name))
    $lnk.TargetPath = $Target
    if ($Arguments) { $lnk.Arguments = $Arguments }
    if ($WorkDir)   { $lnk.WorkingDirectory = $WorkDir }
    if ($Icon)      { $lnk.IconLocation = $Icon }
    $lnk.Save()
    Write-Host "  已创建 $Name"
}

Write-Host "创建开始菜单快捷方式 → $startMenu"
New-Lnk -Name "启动QQ机器人.lnk" -Target (Join-Path $Root "launchers\启动QQ机器人.cmd") `
        -WorkDir $Root -Icon "C:\Windows\System32\shell32.dll,13"
New-Lnk -Name "启动RVC服务.lnk" -Target $Python `
        -Arguments ('"' + (Join-Path $VoiceRoot "cover\rvc_server.py") + '"') `
        -WorkDir (Join-Path $VoiceRoot "cover\rvc_pack\Retrieval-based-Voice-Conversion-WebUI-main") `
        -Icon "C:\Windows\System32\shell32.dll,139"
New-Lnk -Name "启动语音服务.lnk" -Target (Join-Path $Root "launchers\启动语音服务.cmd") `
        -WorkDir $VoiceRoot -Icon "C:\Windows\System32\shell32.dll,138"
New-Lnk -Name "切换RVC音色.lnk" -Target (Join-Path $VoiceRoot "切换RVC音色.cmd") `
        -WorkDir $VoiceRoot -Icon "C:\Windows\System32\shell32.dll,137"

Write-Host ""
Write-Host "完成。打开开始菜单 → 所有应用 → 小鲸服务 即可看到。"
Write-Host "想固定到开始屏幕：右键图标 → 固定到“开始”屏幕"
