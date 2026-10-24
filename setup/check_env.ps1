# 环境自检：检查 Python 依赖、ffmpeg、服务端口是否就绪
# 用法：powershell -ExecutionPolicy Bypass -File check_env.ps1

$ErrorActionPreference = "Continue"

Write-Host "===== 1. 外部软件 ====="
foreach ($cmd in @("git", "node", "ffmpeg")) {
    $p = (Get-Command $cmd -ErrorAction SilentlyContinue)
    if ($p) { Write-Host ("[OK]   {0} -> {1}" -f $cmd, $p.Source) }
    else    { Write-Host ("[缺失] {0}" -f $cmd) -ForegroundColor Yellow }
}

Write-Host ""
Write-Host "===== 2. Python 依赖 ====="
$py = "D:\software\Voice\py310\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "[缺失] $py" -ForegroundColor Yellow
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    if ($py) { Write-Host "        改用系统 python: $py" }
}
if ($py) {
    $code = @"
import importlib, sys
mods = {
  'numpy':'numpy', 'scipy':'scipy', 'librosa':'librosa', 'soundfile':'soundfile',
  'torch':'torch', 'faiss':'faiss', 'parselmouth':'parselmouth',
  'transformers':'transformers', 'demucs':'demucs', 'requests':'requests',
}
ok, missing = [], []
for name, m in mods.items():
    try:
        mod = importlib.import_module(m)
        ver = getattr(mod, '__version__', '?')
        ok.append('%s==%s' % (name, ver))
    except Exception:
        missing.append(name)
print('OK:      ' + ', '.join(ok))
print('MISSING: ' + (', '.join(missing) if missing else '(none)'))
print('python:', sys.version.split()[0])
"@
    $code | & $py -
}

Write-Host ""
Write-Host "===== 3. 服务端口 ====="
$ports = @{ "8643" = "DSH 插件 WS"; "13200" = "NapCat HTTP"; "9850" = "RVC 服务"; "9880" = "TTS 服务" }
foreach ($port in $ports.Keys) {
    $open = $false
    try {
        $c = New-Object Net.Sockets.TcpClient
        $t = $c.ConnectAsync("127.0.0.1", [int]$port)
        if ($t.Wait(600)) { $open = $true }
        $c.Close()
    } catch { }
    $tag = if ($open) { "[OK]  " } else { "[未启动]" }
    Write-Host ("{0} {1,-12} {2}" -f $tag, $port, $ports[$port])
}

Write-Host ""
Write-Host "===== 4. 关键文件 ====="
$files = @(
    "D:\software\Voice\refs\ref.wav",
    "D:\software\Voice\refs\ref.txt",
    "D:\software\Voice\rvc_model.txt",
    "D:\software\QQBot\曲库目录.txt",
    "D:\software\QQBot\workspace\AGENTS.md"
)
foreach ($f in $files) {
    if (Test-Path $f) { Write-Host ("[OK]   {0}" -f $f) }
    else              { Write-Host ("[缺失] {0}" -f $f) -ForegroundColor Yellow }
}

Write-Host ""
Write-Host "自检结束。缺东西按 docs/01 与 docs/06 补齐。"
