@echo off
chcp 65001 >nul
rem ============================================================
rem  启动语音服务 GPT-SoVITS（9880）
rem ============================================================

set PYTHON=D:\software\Voice\py310\python.exe
set TTS_START=D:\software\Voice\start-tts.py

if not exist "%TTS_START%" (
    echo [错误] 找不到 %TTS_START%
    echo 请按 docs/04-语音TTS.md 准备 GPT-SoVITS 后修改本文件。
    pause
    exit /b 1
)

echo 正在启动 TTS 服务（加载模型约 60~90 秒）...
start "" "%PYTHON%" "%TTS_START%"
echo 启动后验证：curl http://127.0.0.1:9880/docs 能打开即成功
timeout /t 3 /nobreak >nul
