# 小鲸 QQ Bot（DeepSeek Harness + NapCat + RVC/GPT-SoVITS）

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

一个跑在 **DeepSeek Harness（DSH）** 上的拟人化 QQ 机器人：会聊天、会撒娇、会发表情包、会发语音，**还会用指定音色唱歌（RVC 翻唱）**，支持群聊 / 私聊 / 戳一戳 / QQ 空间，以及每日新闻派送。

> 本文档记录了从零搭建、踩坑、调优的全过程，目标是让你照着做能得到**同一套效果**；
> 所有可自定义的地方（人设、音色、功能、曲库、情绪）在对应章节都有说明。

---

## 目录

| 文档 | 内容 |
|---|---|
| [环境准备](docs/01-环境准备.md) | 电脑要求、Python、Node、DSH、NapCat、ffmpeg、端口 |
| [DSH 插件与 QQ 接入](docs/02-DSH插件与QQ接入.md) | 插件配置、OneBot 反向 WS、管理员、工作区 |
| [人格人设](docs/03-人格人设.md) | 默认人设「小鲸」、怎么改性格、记忆系统 |
| [语音 TTS](docs/04-语音TTS.md) | GPT-SoVITS 零样本克隆、情绪预设、中英混合 |
| [唱歌翻唱](docs/05-唱歌翻唱.md) | 分离 → RVC 换声 → 自动定调/选段/整句 |
| [音色模型与训练](docs/06-音色模型与训练.md) | 换音色、RVC 训练全流程、GPT-SoVITS 微调、UVR5 |
| [命令与功能](docs/07-命令与功能.md) | 命令表、点歌、表情包、空间说说、新闻推送 |
| [问题与解决方案](docs/08-问题与解决方案.md) | 开发中遇到的**每一个问题**和修法 |
| [自定义与扩展](docs/09-自定义与扩展.md) | 加功能、改曲库、换人设、改情绪参数 |
| [启动器](launchers/) | 三个一键启动脚本 + 开始菜单快捷方式生成器 |
| [配置模板](configs/) | 人格、插件配置、曲库目录等模板 |
| [脚本](scripts/) | say.py / cover.py / songreq.py / rvc_server.py / news_push.py |

---

## 核心特性

- **拟人聊天**：群聊/私聊，多气泡、表情包、引用/@、戳一戳、三种性格模式（日常撒娇 / 傲娇 / 温暖大姐姐）
- **语音**：文字 → GPT-SoVITS 零样本 TTS → RVC 换声 → QQ 语音条，带 6 种情绪预设，中英混合自动分段
- **唱歌（翻唱）**：任意本地歌曲 → 分离人声伴奏 → RVC 换成目标音色 → 自动选副歌、自动定调、结尾对齐整句 → 语音条
- **点歌命令**：`/点歌 歌名` 默认「小鲸唱」，加「原唱」则发原曲切片；两种都支持段落/时长/升降 key/语音条
- **其他**：每日新闻派送、QQ 空间说说、运势抽签、群活跃周报、长期记忆库、/help 分组卡片

## 技术架构

```
QQ 客户端 (NapCat)  ←反向WS→  DSH 插件 (dsh-onebot-qq)  ←→  DeepSeek Harness (人格/工具)
                                      │
                                      ├─ TTS 服务 :9880 (GPT-SoVITS, 常驻)
                                      ├─ RVC 服务 :9850 (音色转换, 常驻)
                                      └─ 脚本: cover.py / songreq.py / say.py / news_push.py
```

- QQ 侧：**NapCat + QQ NT**，OneBot v11 反向 WebSocket（默认 8643）
- 大脑：**DSH** + `dsh-onebot-qq` 插件，人格写在 `workspace/AGENTS.md`
- 声音：**GPT-SoVITS**（文字→人声）+ **RVC**（音色转换），都是本地/云端 CPU 可跑

## 一键启动与快捷方式

仓库 `launchers/` 里是作者自用的三个启动器（`启动QQ机器人.cmd` / `启动RVC服务.cmd` / `启动语音服务.cmd`）。
**它们不是可执行程序**，只是把启动命令写好的批处理，用之前必须把里面的路径改成你自己的。

想一键生成开始菜单快捷方式：

```powershell
# 先改 create-shortcuts.ps1 顶部的 $Root / $VoiceRoot / $Python
powershell -ExecutionPolicy Bypass -File launchers\create-shortcuts.ps1
```

生成后：开始菜单 → 所有应用 → **小鲸服务** → 三个图标；右键可"固定到开始屏幕"。

## 五分钟跑起来（概览，细节见各文档）

1. 装好 DSH、NapCat（QQ 小号）、Python 3.10+、Node.js、ffmpeg
2. 把 `configs/cordis.patch.example.yml` 改名并按注释填 QQ 号/端口/token
3. 把 `configs/AGENTS.example.md` 复制成 `workspace/AGENTS.md`（默认人设）
4. 下载 RVC 模型（见 [音色模型](docs/06-音色模型与训练.md)）放进 RVC 工程
5. 启动 `rvc_server.py`、`start-tts.py`，再启动 DSH 与 QQ
6. 在 QQ 里发 `/help`、`/点歌 晴天` 验证

## 默认配置（和作者当前使用的一致）

| 项 | 默认值 |
|---|---|
| 人设 | 小鲸（大肥鱼），三档性格，详见 [人格人设](docs/03-人格人设.md) |
| 唱歌音色 | RVC 模型 `温柔少女16.pth`（可换） |
| 唱歌选段 | 自动副歌/高潮，约 25 秒，结尾对齐整句 |
| 音高 | 每首自动（测原唱音高 → 目标 290Hz，范围 -2~+6） |
| 发送方式 | 语音条（要文件才发 mp3） |
| 语音情绪 | 默认 normal，可按情景切 sweet/gentle/sad/tsundere/excited |

## 隐私说明

本仓库**不包含**任何个人信息：QQ 号、token、服务器地址、音乐库路径、聊天记录都已替换为占位符。
你自己填进 `configs/` 的配置请**不要**提交回公开仓库。

## License

本项目代码采用 **MIT License**（见 [LICENSE](LICENSE)）。

**不含在本许可证范围内**的东西：

- 音色模型（RVC `.pth` / GPT-SoVITS 权重）——请使用**你有权使用**的模型
- 参考音频、歌曲、演唱录音——版权归各自权利人
- 使用他人（真人/明星/声优）声音模型，仅限个人学习娱乐，**不要公开传播或商用**

---

如果这个项目帮到了你，点个 ⭐ Star 就好。

