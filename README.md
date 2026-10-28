# 小鲸 QQ Bot（DSH + NapCat + GPT-SoVITS + RVC）

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![GPU](https://img.shields.io/badge/GPU-不需要-green)
![npm](https://img.shields.io/badge/npm-lulu--dsh--xiaojing--panel-cb3837)

一个跑在 **DeepSeek Harness（DSH）** 上的拟人化 QQ 机器人：
会聊天、会撒娇、会发表情包、会发语音、**会用指定音色唱歌（RVC 翻唱）**，
支持群聊 / 私聊 / 戳一戳 / QQ 空间 / 每日新闻，并自带一个**可视化管理面板插件**。

> 本仓库记录了从零搭建、踩坑 70+ 次的完整过程。目标是：**照着做能得到同一套效果**。

---

## ✨ 能做什么

| 能力 | 说明 |
|---|---|
| 💬 拟人聊天 | 群聊/私聊，多气泡、表情包、引用/@、戳一戳；三种性格（撒娇 / 傲娇 / 温暖大姐姐） |
| 🎤 语音 | 文字 → GPT-SoVITS → RVC → 语音条；6 种情绪；中英混合自动分段；**开头不吞字** |
| 🎧 听得懂语音 | 别人发语音 → faster-whisper 转文字（自动简体）→ 正常接话 |
| 🎵 唱歌 | 本地歌曲 → 分离 → RVC 换音色 → **自动找副歌** → **自动定调** → **结尾对齐整句** → 语音条 |
| 🎼 点歌命令 | `/点歌 歌名` 默认小鲸唱；`/点歌 原唱 歌名` 发原曲切片；都支持段落/时长/升降 key |
| 🖼 长文转图 | 回复超过阈值自动渲染成图片卡片（防截断/刷屏），控制台可开关 |
| 🧩 合并转发 | 聊天记录合成一条转发消息，不刷屏 |
| 🎛 控制台插件 | 自研 DSH 插件：人设/语料/表情包/曲库/音色/定时任务/服务启停全在一个面板 |
| 📰 新闻派送 | 每天 19:00 自动推送 5~8 条新闻 |
| 🎲 小功能 | 今日气运、群活跃周报、长期记忆、图片 OCR |

---

## 🧠 先搞懂这些名词

| 名词 | 一句话 | 详见 |
|---|---|---|
| **DSH** | 机器人的"大脑"（AI 宿主，负责对话和调工具） | [术语表](docs/00-术语表.md) |
| **NapCat** | 让程序能登录 QQ、收发消息的协议端 | [术语表](docs/00-术语表.md) |
| **OneBot / 反向 WS** | QQ 消息的标准格式；NapCat 主动连 DSH 的方式 | [术语表](docs/00-术语表.md) |
| **GPT-SoVITS** | **TTS**：把文字读成指定音色的声音（说话） | [语音](docs/04-语音TTS.md) |
| **RVC** | 声音转换：把一段人声换成目标音色（**唱歌必须用**） | [唱歌](docs/05-唱歌翻唱.md) |
| **demucs / UVR5** | 把歌拆成"人声 + 伴奏"的两种工具 | [分离方案](docs/12-声音分离方案（demucs与UVR5）.md) |
| **.pth 音色模型** | 决定"像谁"的文件 | [音色模型](docs/13-音色模型仓库与来源.md) |
| **AGENTS.md** | 决定"性格"的文本文件 | [人格人设](docs/03-人格人设.md) |

> **GPT-SoVITS 和 RVC 不是二选一**：前者负责"把文字读出来"，后者负责"把声音换成目标音色"，两者都在用。

---

## 🎛 小鲸控制台插件（本项目自研）

装它：

```
DSH → 插件 → 添加插件 → 输入包名：lulu-dsh-xiaojing-panel
```

npm 地址：https://www.npmjs.com/package/lulu-dsh-xiaojing-panel

装好后：**设置 → 小鲸控制台**，十个标签页：

| 标签 | 能干什么 |
|---|---|
| 人格人设 | 直接编辑 `AGENTS.md`（`/new` 生效） |
| 表情包 | 收藏/收录两区，可折叠、搜索、多选、看大图、重命名、批量加前缀、移入收藏 |
| 音乐库 | 编辑 `曲库目录.txt` |
| 音色模型 | 下拉切换 `.pth` |
| 定时任务 | 增删任务（文本/脚本）、测试发送、复制 |
| 服务管理 | NapCat / RVC / TTS 状态 + 启停（自动清理重复进程） |
| 语料库 | 新建/编辑/删除语料文件 |
| 语音/唱歌参数 | 情绪语速/清晰度/高低、唱歌音高/音量/响度，带人话说明 + 恢复默认 |
| 长文转图 | 开关、阈值、页脚、字体 |
| 配置文件 | 一键打开各类配置 |

源码在本仓库 `plugin/lulu-dsh-xiaojing-panel/`，详见 [控制台插件文档](docs/14-小鲸控制台插件.md)。

---

## 🚀 两种上手方式

### 方式 A：让 AI 帮你搭

把这段发给 DSH / Claude Code / Cursor / 任何能执行命令的 AI：

```text
你是一个部署助手。请按 https://github.com/lulu520-1314/QQbot_jin 这个仓库，
在我这台 Windows 电脑上把"小鲸 QQ Bot"搭起来。
先通读 README 和 docs/，检查我已有的依赖，缺什么列清单；
按 docs/01→14 的顺序装环境、配插件、配人格、准备音色模型；
每步做完做一次验证（端口/脚本能不能跑），所有要改的绝对路径先问我确认。
```

完整 prompt 与验收清单见 [AI 一键搭建指南](docs/11-AI一键搭建指南.md)。

### 方式 B：自己照着做

```
1. 装环境        → docs/01
2. 配 DSH 插件   → docs/02
3. 放人格文件    → docs/03 + configs/AGENTS.example.md
4. 装控制台插件  → docs/14（npm 包名 lulu-dsh-xiaojing-panel）
5. 准备音色模型  → docs/13
6. 启动服务      → launchers/
7. 测试          → QQ 里发 /help、/点歌 晴天
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
│  ├─ 04-语音TTS.md               参考音、6 种情绪、中英混合、STT、params.json
│  ├─ 05-唱歌翻唱.md              分离→换声→自动定调/选段/整句、混音链、故障排查
│  ├─ 06-音色模型与训练.md         音色库、换模型、RVC 训练、GPT-SoVITS 微调、UVR5
│  ├─ 07-命令与功能.md             命令表、点歌、长文转图、合并转发、新闻
│  ├─ 08-问题与解决方案.md         70+ 个真实踩坑记录
│  ├─ 09-自定义与扩展.md           加功能、改曲库、改参数
│  ├─ 10-常见问题FAQ.md            高频问题
│  ├─ 11-AI一键搭建指南.md         把 prompt 丢给 AI
│  ├─ 12-声音分离方案（demucs与UVR5）.md
│  ├─ 13-音色模型仓库与来源.md     默认模型下载地址、模型库
│  └─ 14-小鲸控制台插件.md         自研面板插件（架构/API/稳定性设计）
├─ plugin/lulu-dsh-xiaojing-panel/  控制台插件源码（已发布 npm）
├─ configs/                      人格、插件配置、曲库、模型名、params、定时任务 模板
├─ launchers/                    三个一键启动脚本 + 快捷方式生成器
├─ setup/                        install_deps.ps1 / check_env.ps1
├─ scripts/                      say / cover / songreq / rvc_server / whisper_fw / news_push / build_dataset / audition_models
└─ assets/
```

---

## ⚙️ 默认配置（与作者当前一致）

| 项 | 默认值 |
|---|---|
| 人设 | 小鲸（大肥鱼），三档性格 |
| 唱歌音色 | RVC `布甜.pth`（可在控制台切换；备选 11 个见 docs/06） |
| 选段 | 自动副歌/高潮，约 25 秒，结尾对齐整句 |
| 音高 | 每首自动（pyin 测原唱 → 目标 290Hz，clamp -2~+6） |
| 混音 | 人声压缩防断气、EQ 压沙哑、双限幅防爆音、人声 1.2 / 伴奏 0.75 |
| 语音情绪 | 默认 normal，可切 sweet/gentle/sad/tsundere/excited |
| 语音转写 | 开启（faster-whisper small，中文自动转简体） |
| 长文转图 | 开启，阈值 200 字，页脚「小鲸」，微软雅黑 |
| 参数文件 | `D:\software\Voice\params.json`（控制台可调） |

---

## 🔧 自定义速查

| 想改 | 改哪里 |
|---|---|
| 性格 / 说话风格 | `workspace/AGENTS.md`（控制台可编辑） |
| 音色 | 控制台 → 音色模型 → 选 → 服务管理重启 RVC |
| 语音/唱歌参数 | 控制台 → 语音/唱歌参数（或 `params.json`） |
| 曲库 | 控制台 → 音乐库（写 `曲库目录.txt`） |
| 语料库 | 控制台 → 语料库 |
| 定时任务 | 控制台 → 定时任务（文本/脚本，可测试发送） |
| 长文转图 | 控制台 → 长文转图 |
| 加新命令 | 插件 `lib/commands.js`（见 docs/09） |

---

## 📊 性能参考（纯 CPU）

| 操作 | 耗时 |
|---|---|
| 一句 15 字语音（TTS+RVC） | 30~40 秒 |
| 语音转文字（10 秒语音） | 3~8 秒 |
| 一首 25 秒翻唱 | 3~5 分钟（命中分离缓存约 1 分钟） |
| RVC / TTS 服务启动 | 60~90 秒 |

有 NVIDIA GPU 会快 10 倍以上，但不是必需。

---

## 🩺 遇到问题先看

1. [常见问题 FAQ](docs/10-常见问题FAQ.md)
2. [问题与解决方案](docs/08-问题与解决方案.md)（70+ 真实报错与修法）
3. 跑一次 `setup/check_env.ps1` 自检环境

---

## 🔒 隐私说明

本仓库**不包含**任何个人信息：QQ 号、token、服务器地址、音乐库路径、聊天记录都已换成占位符
（`<小号QQ>`、`<你的OneBotToken>`、`C:\Users\<你的用户名>` 等）。
你自己填进 `configs/` 与 `launchers/` 的真实配置，**不要提交回公开仓库**。

---

## 🤝 致谢

- DeepSeek Harness
- [NapCatQQ](https://github.com/NapNeko/NapCatQQ)
- [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)
- [Retrieval-based-Voice-Conversion-WebUI](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI)
- [demucs](https://github.com/facebookresearch/demucs)
- [Ultimate Vocal Remover](https://github.com/Anjok07/ultimatevocalremovergui)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- 公开音色模型：[lowo/RVC-weights](https://huggingface.co/lowo/RVC-weights)

## 📄 License

代码采用 **MIT License**（见 [LICENSE](LICENSE)）。

不含在许可证范围内：音色模型、参考音频、歌曲、演唱录音。
使用他人（真人/明星/声优）声音模型，仅限个人学习娱乐，**不要公开传播或商用**。

---

如果这个项目帮到了你，点个 ⭐ Star 就好。
