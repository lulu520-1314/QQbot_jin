# 04 · 语音（文字 → 你的声音）

## 1. 原理

```
文字 ──GPT-SoVITS(零样本克隆)──► 原始人声 ──RVC(音色转换)──► 目标音色 ──► 语音条
         用参考音当"语气样本"                    用本地模型当"音色"
```

- **GPT-SoVITS**：给出 `参考音 + 参考音文字`，就能用参考音的语气读任意文字（零样本，不用训练）
- **RVC**：把上一步的声音换成你选定的音色模型（唱歌同款）
- 两步可选：只 TTS（快、音色=参考音）或 TTS+RVC（更像模型音色，多 20 秒）

## 2. 准备参考音（决定"像不像你"）

| 要求 | 说明 |
|---|---|
| 内容 | **说话**素材（不要用唱歌的，唱腔会带到说话里） |
| 时长 | 8~15 秒最佳（太长反而糊） |
| 质量 | 安静环境、无伴奏、无回声、别笑场、别犹豫 |
| 格式 | 任意，脚本会自动转 32k 单声道 |
| 配套文字 | 必须提供参考音的**逐字文本**（`ref.txt`） |

作者最终用的是 8 秒闲聊片段（自然、有情绪），放在：

```
refs\ref.wav
refs\ref.txt
```

> 换参考音 = 换这两个文件，**不用改代码**。

## 3. 用法

```powershell
# 最简（日常语气，带 RVC 换音色）
D:\software\Voice\say.cmd --text "今天的作业写完了吗" --rvc --out out.wav

# 指定情绪
--emotion gentle      # 温柔深情（语速 0.95、音高 -2）适合"晚安""宝宝"
--emotion sweet       # 撒娇（1.08、+1）
--emotion tsundere    # 傲娇（1.25、+1）
--emotion sad         # 难过（0.92、-2）
--emotion excited     # 兴奋（1.32、+2）
--emotion normal      # 日常（1.15）

# 中英混合（默认 auto，自动分段，无需手动指定）
--text "今天的 meeting 有点 boring，but 没关系"
```

完整参数见 `scripts/say.py --help`。

## 4. 性能

| 场景 | 耗时（纯 CPU） |
|---|---|
| 一句 15 字，TTS only | 8~15 秒 |
| 一句 15 字，TTS + RVC | 30~40 秒 |
| 服务冷启动 | +60~90 秒（只第一次） |

> 想再快：**微调 GPT-SoVITS**（省掉 RVC 这一步），见 [音色模型与训练](06-音色模型与训练.md)。

## 5. 已解决的问题（详见 08 章）

| 问题 | 解决 |
|---|---|
| 开头一两个字不清楚 | 转 RVC 前**垫 300ms 静音**，转换后裁掉 |
| 第一句语速比后面快 | 不用 `cut5` 按句切，改 `cut0` 整段合成 |
| 声音发闷、不清晰 | 输出做 3kHz 提亮 + 峰值归一 |
| 英文/中英混合读错 | `--lang auto`，按语言分段合成再拼接 |
| 情绪永远一个调 | 6 种情绪预设（语速/提亮/音高一起变） |
| RVC 服务挂了语音失败 | say.py 检测到 9850 不通会**自动拉起**再重试 |

## 6. 自定义

- **改语速**：`--speed 1.3`（>1 快，<1 慢）
- **改清晰度**：`--presence 3.5`（3kHz 提亮 dB，越大越"亮"）
- **改音色**：切换 RVC 模型（`切换RVC音色.cmd`），语音和唱歌共用同一个模型
- **改情绪参数**：`scripts/say.py` 顶部 `emo = {...}` 字典，直接改数值


## 7. 语音转文字（STT）：让别人发的语音也能听懂

默认关闭是吃大亏的——别人发语音，小鲸只能看到 `[语音]`。开启后能理解内容。

实现（本仓库 `scripts/whisper_fw.py`）：

```bash
pip install faster-whisper opencc-python-reimplemented
python scripts/whisper_fw.py 输入.wav 输出.txt small
```

插件配置（`dsh-onebot` 条目）：

```yaml
sttEnabled: true
sttEngine: custom
sttCommand: 'D:\software\Voice\py310\python.exe'
sttArgs: [ 'D:\software\Voice\whisper_fw.py', '{file}', '{out}', 'small' ]
sttTimeoutMs: 90000
```

- CPU int8，10 秒语音约 3~8 秒
- 自动转简体（whisper 常输出繁体 → opencc t2s）
- 转写有错字属正常，人格里要写"别当原话复述"

## 8. 参数面板（params.json）

语音/唱歌的可调参数集中在 `D:\software\Voice\params.json`，脚本每次运行自动读取：

```json
{
  "voice": {
    "mode_speed": { "daily": 1.02, "tsundere": 1.12, "warm": 1.0 },
    "emotions": {
      "normal": { "speed": 1.02, "presence": 2.5, "pitch": 0 },
      "gentle": { "speed": 0.92, "presence": 2.0, "pitch": -2 }
    }
  },
  "cover": { "targetHz": 290.0, "pitchMin": -2, "pitchMax": 6, "protect": 0.35,
             "indexRate": 0.5, "vocalVol": 1.2, "instVol": 0.75, "loudnessI": -14.0 },
  "modelGain": { "温柔男模.pth": 1.08 }
}
```

- `modelGain`：按模型单独调音量（男声模型普遍偏轻）
- **增益必须等比缩放，不能 clip**，否则会爆音（真实踩坑）

