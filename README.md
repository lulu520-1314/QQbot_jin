# 小鲸 QQ Bot（DSH + NapCat + GPT-SoVITS + RVC）

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![GPU](https://img.shields.io/badge/GPU-不需要-green)

一个跑在 **DeepSeek Harness（DSH）** 上的拟人化 QQ 机器人：
会聊天、会撒娇、会发表情包、会发语音，**还会用指定音色唱歌（RVC 翻唱）**，
支持群聊 / 私聊 / 戳一戳 / QQ 空间，以及每日新闻派送。

> 本仓库是作者从零搭建、踩坑 60+ 次的完整记录。目标是：**你照着做，能得到同一套效果**。
> 每一处可自定义（人设、音色、情绪、曲库、功能）都有对应文档。

---

## ✨ 能做什么

| 能力 | 说明 |
|---|---|
| 💬 拟人聊天 | 群聊/私聊，多气泡、表情包、引用/@、戳一戳；三种性格（撒娇 / 傲娇 / 温暖大姐姐） |
| 🎤 语音 | 文字 → GPT-SoVITS → RVC → 语音条；6 种情绪；中英混合自动分段 |
| 🎵 唱歌 | 本地歌曲 → 分离 → RVC 换音色 → 自动选副歌 → 自动定调 → 结尾对齐整句 → 语音条 |
| 🎼 点歌命令 | `/点歌 歌名` 默认小鲸唱；`/点歌 原唱 歌名` 发原曲切片；都支持段落/时长/升降 key |
| 📰 新闻派送 | 每天 19:00 自动推送 5~8 条新闻到群/私聊 |
| 💭 QQ 空间 | 管理员可以让它发说说 |
| 🎲 小功能 | 今日气运、群活跃周报、长期记忆库、图片 OCR |
| 🛠 可扩展 | 加命令、加脚本、换人设、换音色、换曲库——文档里都写了怎么做 |

---

## 🧠 先搞懂这些名词（否则后面看不懂）

| 名词 | 一句话 | 详见 |
|---|---|---|
| **DSH** | 机器人的"大脑"（AI 宿主，负责对话和调工具） | [术语表](docs/00-术语表.md) |
| **NapCat** | 让程序能登录 QQ、收发消息的协议端 | [术语表](docs/00-术语表.md) |
| **OneBot / 反向 WS** | QQ 消息的标准格式；NapCat 主动连到 DSH 的方式 | [术语表](docs/00-术语表.md) |
| **GPT-SoVITS** | **TTS**：把文字读成指定音色的声音（说话） | [语音](docs/04-语音TTS.md) |
| **RVC** | 声音转换：把一段人声换成目标音色（**唱歌必须用**，也用于统一日常语音） | [唱歌](docs/05-唱歌翻唱.md) |
| **demucs / UVR5** | 把歌拆成"人声 + 伴奏"的两种工具 | [分离方案](docs/12-声音分离方案（demucs与UVR5）.md) |
| **.pth 音色模型** | 决定"像谁"的文件 | [音色模型](docs/13-音色模型仓库与来源.md) |
| **AGENTS.md** | 决定"性格"的文本文件 | [人格人设](docs/03-人格人设.md) |

> **GPT-SoVITS 和 RVC 不是二选一**：两者都在用——GPT-SoVITS 负责"把文字读出来"，RVC 负责"把声音换成目标音色"。

---

## 🚀 两种上手方式

### 方式 A：让 AI 帮你搭（推荐给不想折腾的人）

把这段发给 DSH / Claude Code / Cursor / 任何能执行命令的 AI：

```text
你是一个部署助手。请按 https://github.com/lulu520-1314/QQbot_jin 这个仓库，
在我这台 Windows 电脑上把"小鲸 QQ Bot"搭起来。
先通读 README 和 docs/，检查我已有的依赖，缺什么列清单；
按 docs/01→10 的顺序装环境、配插件、配人格、准备音色模型；
每步做完做一次验证（端口/脚本能不能跑），所有要改的绝对路径先问我确认。
```

完整 prompt 与验收清单见 [AI 一键搭建指南](docs/11-AI一键搭建指南.md)。

### 方式 B：自己照着做

```
1. 装环境        → docs/01
2. 配 DSH 插件   → docs/02
3. 放人格文件    → docs/03 + configs/AGENTS.example.md
4. 准备音色模型  → docs/13（默认：温柔少女16）
5. 启动服务      → launchers/
6. 测试          → QQ 里发 /help、/点歌 晴天
```

---

## 🗂 仓库结构

```
QQbot_jin/
├─ README.md
├─ LICENSE                       MIT
├─ docs/
│  ├─ 00-术语表.md                NapCat/RVC/GPT-SoVITS/UVR5/反向WS 都是啥
│  ├─ 01-环境准备.md              电脑要求、Python/Node/FFmpeg/NapCat、端口
│  ├─ 02-DSH插件与QQ接入.md       插件配置、OneBot、工作区、启动顺序
│  ├─ 03-人格人设.md              小鲸人设、怎么改性格、记忆系统
│  ├─ 04-语音TTS.md               参考音要求、6 种情绪、中英混合
│  ├─ 05-唱歌翻唱.md              分离→换声→自动定调/选段/整句、混音链
│  ├─ 06-音色模型与训练.md         换音色、RVC 训练全流程、GPT-SoVITS 微调
│  ├─ 07-命令与功能.md             全部命令、点歌、新闻、表情包
│  ├─ 08-问题与解决方案.md         60+ 个真实踩坑记录
│  ├─ 09-自定义与扩展.md           加功能、改曲库、改情绪参数
│  ├─ 10-常见问题FAQ.md            18 个高频问题
│  ├─ 11-AI一键搭建指南.md         把这段 prompt 丢给 AI
│  ├─ 12-声音分离方案（demucs与UVR5）.md
│  └─ 13-音色模型仓库与来源.md     含本项目默认模型下载地址
├─ configs/                      人格、插件配置、曲库、模型名 模板
├─ launchers/                    三个一键启动脚本 + 快捷方式生成器
├─ setup/                        install_deps.ps1 / check_env.ps1
├─ scripts/                      say.py / cover.py / songreq.py / rvc_server.py / news_push.py / build_dataset.py
└─ assets/
```

---

## ⚙️ 默认配置（与作者当前使用一致）

| 项 | 默认值 |
|---|---|
| 人设 | 小鲸（大肥鱼），三档性格，见 [人格人设](docs/03-人格人设.md) |
| 唱歌音色 | RVC `温柔少女16.pth`（[来源](docs/13-音色模型仓库与来源.md)） |
| 选段 | 自动副歌/高潮，约 25 秒，结尾对齐整句 |
| 音高 | 每首自动（测原唱音高 → 目标 290Hz，范围 -2~+6） |
| 人声/伴奏 | 同步变调；人声压缩防断气；EQ 压沙哑；双限幅防爆音 |
| 发送 | 默认语音条（要文件才发 mp3） |
| 语音情绪 | 默认 normal，可按情景切 sweet/gentle/sad/tsundere/excited |
| 曲库 | `曲库目录.txt`（一行一个文件夹，自己填） |

---

## 🔧 自定义速查

| 想改 | 改哪里 |
|---|---|
| 性格 / 说话风格 | `workspace/AGENTS.md` |
| 音色 | 换 `.pth` + 改 `rvc_model.txt` + 重启 RVC 服务 |
| 情绪档位参数 | `scripts/say.py` 的 `emo = {...}` |
| 唱歌音高/响度/压缩 | `scripts/cover.py` 混音链与 `290.0` 目标值 |
| 曲库 | `曲库目录.txt` |
| 加新命令 | 插件 `lib/commands.js`（见 docs/09） |
| 表情包 | `workspace/stickers/`（文件名即标签） |

---

## 📊 性能参考（纯 CPU）

| 操作 | 耗时 |
|---|---|
| 一句 15 字语音（TTS+RVC） | 30~40 秒 |
| 一首 25 秒翻唱 | 3~5 分钟 |
| RVC 服务启动（模型加载） | ~60 秒 |
| TTS 服务启动 | 60~90 秒 |

有 NVIDIA GPU 会快 10 倍以上，但不是必需。

---

## 🩺 遇到问题先看

1. [常见问题 FAQ](docs/10-常见问题FAQ.md)（18 个高频问题）
2. [问题与解决方案](docs/08-问题与解决方案.md)（60+ 真实报错与修法）
3. 跑一次 `setup/check_env.ps1` 自检环境

---

## 🎨 音色与训练的路线图

| 需求 | 方案 | 文档 |
|---|---|---|
| 只要好听，不要求像我 | **公开 RVC 模型**（默认路线） | [13](docs/13-音色模型仓库与来源.md) |
| 唱歌用我的声音 | **训练 RVC**（5~10 分钟素材 + 1 小时 GPU） | [06](docs/06-音色模型与训练.md) |
| 说话更像本人、更快 | **GPT-SoVITS 微调** | [06](docs/06-音色模型与训练.md) |
| 训练素材要更干净 | **UVR5** 或 `htdemucs_ft` | [12](docs/12-声音分离方案（demucs与UVR5）.md) |

---

## 🔒 隐私说明

本仓库**不包含**任何个人信息：QQ 号、token、服务器地址、音乐库路径、聊天记录都已换成占位符
（`<小号QQ>`、`<你的OneBotToken>`、`C:\Users\<你的用户名>` 等）。

你自己填进 `configs/` 与 `launchers/` 的真实配置，**不要提交回公开仓库**。

---

## 🤝 致谢 / 相关项目

- DeepSeek Harness
- [NapCatQQ](https://github.com/NapNeko/NapCatQQ)
- [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)
- [Retrieval-based-Voice-Conversion-WebUI](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI)
- [demucs](https://github.com/facebookresearch/demucs)
- [Ultimate Vocal Remover](https://github.com/Anjok07/ultimatevocalremovergui)
- 公开音色模型：[lowo/RVC-weights](https://huggingface.co/lowo/RVC-weights)

## 📄 License

代码采用 **MIT License**（见 [LICENSE](LICENSE)）。

不含在许可证范围内：音色模型、参考音频、歌曲、演唱录音。
使用他人（真人/明星/声优）声音模型，仅限个人学习娱乐，**不要公开传播或商用**。

---

如果这个项目帮到了你，点个 ⭐ Star 就好。
