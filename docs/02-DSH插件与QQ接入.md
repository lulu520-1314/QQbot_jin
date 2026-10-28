# 02 · DSH 插件与 QQ 接入

机器人 = **DSH（大脑）+ dsh-onebot-qq（QQ 适配插件）+ NapCat（QQ 协议端）**。
DSH 负责对话、人设、工具调用；插件负责把 QQ 消息送进 DSH、把回复发回 QQ。

## 1. 安装插件

作者用的是 **dsh-onebot-qq 0.9.3**（插件市场搜 `onebot` 或 `qq`）。

插件装在：

```
%USERPROFILE%\.dsh\profiles\desktop\node_modules\dsh-onebot-qq\
```

## 2. 配置文件

DSH 的插件由 `%USERPROFILE%\.dsh\profiles\desktop\cordis.patch.yml` 加载。
模板见 [`../configs/cordis.patch.example.yml`](../configs/cordis.patch.example.yml)。

关键项（**全部要改成你自己的**）：

```yaml
- id: dsh-onebot
  config:
    mode: reverse            # NapCat 主动连 DSH（推荐）
    port: 8643               # 与 NapCat 的 ws url 一致
    token: "<你的OneBotToken>"
    botQQ: "<小号QQ>"
    admin: "<管理员QQ>"        # 只有这个人能用管理命令
    requireMention: false    # 群里不 @ 也回复
    rateLimitPerMinute: 15
    newMessagePolicy: steer
    dmPolicy: allowlist
    workspacePath: "D:\\software\\QQBot\\workspace"
```

> **不要把填好的配置提交到公开仓库！** 仓库里只放 `*.example.yml`。

## 3. NapCat 配置要点

1. 用**小号**登录 QQ NT，NapCat 也登录同一个小号
2. 反向 WebSocket 指向 `ws://127.0.0.1:8643`，token 与插件一致
3. HTTP API 端口改到 **13200**（避开 Windows 保留端口段 2985~3084）
4. 开消息上报（至少 `message`、`notice` 两类，戳一戳在 `notice` 里）

验证 NapCat 是否正常：

```powershell
curl http://127.0.0.1:13200/get_login_info
```

返回 JSON 里有小号 QQ 号即成功。

## 4. 工作区

`workspacePath` 指向的目录就是机器人的"家"：

```
workspace\
├─ AGENTS.md          # 人格/规则（核心，见 03 章）
├─ stickers\          # 表情包（文件名即标签）
├─ voice\             # 语音/翻唱产物
└─ 记忆库.md           # /记住 的记忆
```

DSH 每次会话启动时会读取 `AGENTS.md`，所以**改完人格要 /new 或重启 DSH 才生效**。

## 5. 插件自带命令（改过的部分）

本项目对插件做了定制（源码在 `%USERPROFILE%\.dsh\profiles\desktop\node_modules\dsh-onebot-qq\lib\`）：

| 文件 | 改动 |
|---|---|
| `lib/commands.js` | `/help` 固定两条气泡；点歌支持「小鲸唱/原唱」双模式；去掉 `/ver` |
| `lib/outbound.js` | 多气泡按换行拆；新增 `noSplit` 选项；过滤模型自带的注释行 |
| `lib/connection.js` | 增加 `notice` 事件分发（戳一戳） |
| `lib/index.js` | 戳一戳回复；非管理员命令门的顺序修正 |
| `lib/prompt.js` | 平台提示（纯文本、专业模式前缀等） |

> 这些是**本地修改**，插件升级会被覆盖，升级后需要重新打补丁（见 `docs/09`）。

## 6. 启动顺序

```
1. 启 NapCat（QQ 登录）
2. 启 RVC 服务（rvc_server.py，模型加载约 60 秒）
3. 启 TTS 服务（start-tts.py，GPT-SoVITS 加载约 60~90 秒）
4. 启 DSH
5. 在 QQ 里发 /help 测试
```

服务挂了怎么办：`say.py --rvc` 和 `cover.py` 都会**自动拉起** RVC 服务；TTS 服务需要手动起（或做开机自启）。
