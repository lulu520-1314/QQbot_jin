# 一键安装 Python 依赖（音频/RVC 环境）
# 用法：powershell -ExecutionPolicy Bypass -File install_deps.ps1
# 说明：只装 Python 包，不装系统软件（Python/Node/FFmpeg 请自行安装）

$ErrorActionPreference = "Stop"

# ===== 改成你自己的 Python =====
$py = "D:\software\Voice\py310\python.exe"
# ==============================

if (-not (Test-Path $py)) {
    Write-Host "[错误] 找不到 Python: $py" -ForegroundColor Red
    Write-Host "请修改本文件顶部的 $py 为你的 Python 路径"
    exit 1
}

Write-Host "使用 Python: $py"
& $py -m pip install --upgrade pip

$mirror = "https://pypi.tuna.tsinghua.edu.cn/simple"

Write-Host "`n[1/4] 基础音频依赖..."
& $py -m pip install -i $mirror numpy==1.26.4 scipy librosa==0.10.2 soundfile requests

Write-Host "`n[2/4] 分离 / 音频处理..."
& $py -m pip install -i $mirror demucs==4.1.0 faiss-cpu praat-parselmouth

Write-Host "`n[3/4] torch（CPU 版；有 CUDA 请去官网选对应命令）..."
& $py -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

Write-Host "`n[4/4] transformers（RVC 环境锁 4.49）..."
& $py -m pip install -i $mirror transformers==4.49.0

Write-Host "`n完成。运行 setup/check_env.ps1 自检。"
Write-Host "注意：GPT-SoVITS 需要单独环境（transformers>=4.51），不要装进这个环境。"
