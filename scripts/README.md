# scripts · 脚本说明

这些是作者实际在用的脚本，已**脱敏**（路径/QQ号/token 全部替换为占位符）。
用之前先做一件事：把文件顶部的路径常量改成你自己的。

## 各脚本作用

| 文件 | 作用 | 关键配置（文件顶部/前部） |
|---|---|---|
| `say.py` | 文字 → TTS → RVC → 语音 wav | `ROOT`、`PY_MAIN`、`FFMPEG`、`API`(9880)、`REF` |
| `start-tts.py` | 启动 GPT-SoVITS api_v2 | GPT-SoVITS 安装路径、模型路径、端口 |
| `cover.py` | 翻唱流水线（分离→RVC→混音） | `ROOT`、`PY_MAIN`、`FFMPEG`、`WORK_ROOT` |
| `rvc_server.py` | RVC 常驻服务（9850） | `REPO`、模型目录、`PORT` |
| `songreq.py` | 点歌：找歌/切片/自动副歌 | `LIB_FILE`(曲库目录.txt)、`FFMPEG`、`OUT_DIR`、`COVER`(cover.py) |
| `news_push.py` | 每晚新闻派送 | `GROUPS`、`PRIVATE`、`RSS_LIST`、NapCat API |

## 统一要改的常量

```python
ROOT    = r"D:\software\Voice"        # 你的音频工坊目录
PY_MAIN = os.path.join(ROOT, "py310", "python.exe")   # 你的 Python
FFMPEG  = r"D:\software\Voice\ffmpeg\package\ffmpeg.exe"
API     = "http://127.0.0.1:9880"      # GPT-SoVITS
NAPCAT  = "http://127.0.0.1:13200"     # NapCat HTTP
```

## 使用顺序

1. 先确保 TTS 服务（9880）能跑：`python start-tts.py`
2. 再确保 RVC 服务（9850）能跑：`python rvc_server.py`
3. 测试语音：`python say.py --text "测试一下" --rvc --out test.wav`
4. 测试翻唱：`python cover.py --song <你的歌.mp3> --outdir out`
5. 测试点歌：`python songreq.py plan "晴天"`

## 依赖

```bash
pip install requests soundfile librosa==0.10.2 numpy==1.26.4 demucs==4.1.0
# RVC 相关见 docs/01 与 RVC 工程自身的 requirements
```
