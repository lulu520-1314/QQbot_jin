@echo off
chcp 65001 >nul
rem ============================================================
rem  启动 QQ 机器人（NapCat + QQ）
rem  用法：把下面的路径改成你自己的，然后双击本文件
rem ============================================================

set NAPCAT_LAUNCHER=D:\software\QQBot\run-napcat-log.bat

if not exist "%NAPCAT_LAUNCHER%" (
    echo [错误] 找不到 NapCat 启动器：
    echo    %NAPCAT_LAUNCHER%
    echo 请编辑本文件，把 NAPCAT_LAUNCHER 改成你自己的路径。
    pause
    exit /b 1
)

echo 正在启动 QQ + NapCat...
start "" "%NAPCAT_LAUNCHER%"
echo 已启动。稍等 10~20 秒，确认 QQ 登录的是【小号】。
echo 验证 NapCat 是否在线：curl http://127.0.0.1:13200/get_login_info
timeout /t 5 /nobreak >nul
