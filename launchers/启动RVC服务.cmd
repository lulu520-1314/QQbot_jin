@echo off
chcp 65001 >nul
rem ============================================================
rem  启动 RVC 音色转换服务（9850）
rem  模型由 D:\software\Voice\rvc_model.txt 决定
rem ============================================================

set PYTHON=D:\software\Voice\py310\python.exe
set RVC_SERVER=D:\software\Voice\cover\rvc_server.py
set WORKDIR=D:\software\Voice\cover\rvc_pack\Retrieval-based-Voice-Conversion-WebUI-main

if not exist "%PYTHON%" (
    echo [错误] 找不到 Python：%PYTHON%
    echo 请编辑本文件改成你自己的路径。
    pause
    exit /b 1
)

echo 正在启动 RVC 服务（加载模型约 60 秒）...
start "" /D "%WORKDIR%" "%PYTHON%" "%RVC_SERVER%"
echo 启动后验证：http://127.0.0.1:9850 应返回 {"ok": true, "service": "rvc"}
timeout /t 3 /nobreak >nul
