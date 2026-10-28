# lulu-dsh-xiaojing-panel

小鲸控制台 —— DeepSeek Harness（DSH）的 QQ 机器人「小鲸」管理面板插件。

> 与 `dsh-onebot-qq` 并存：QQ 传输仍由它负责，本插件只提供**设置页控制台**与**定时任务/表情包收录**能力。

## 功能

- **人格人设**：直接编辑 `workspace/AGENTS.md`，保存后 QQ 里发 `/new` 生效
- **表情包**：分「收藏」（小鲸能发的）与「收录」（自动收藏待整理）两区，支持缩略图预览、搜索、多选、删除、重命名、移入收藏
- **音乐库**：编辑 `曲库目录.txt`，`/点歌` 与聊天点歌共用
- **音色模型**：下拉选择 RVC `.pth`，写入 `rvc_model.txt`
- **定时任务**：可视化增删任务（文本 / 脚本），到点通过 NapCat 发送
- **服务管理**：查看并启动/停止 NapCat(13200) / RVC(9850) / TTS(9880)
- **配置文件**：一键用系统编辑器打开人设、曲库、模型、任务、记忆库等

## 安装

在 DSH「添加插件」里输入包名：

```
lulu-dsh-xiaojing-panel
```

或在 profile 的 `cordis.patch.yml` 里注册：

```yaml
- insert:
    - id: lulu-dsh-xiaojing-panel
      name: 'lulu-dsh-xiaojing-panel'
```

## 默认配置（可在 patch 里覆盖）

| 配置项 | 默认值 |
|---|---|
| `host` / `port` | `127.0.0.1` / `9877`（占用自动顺延） |
| `workspaceDir` | `D:\software\QQBot\workspace` |
| `voiceDir` | `D:\software\Voice` |
| `musicDirsFile` | `D:\software\QQBot\曲库目录.txt` |
| `schedulesFile` | `D:\software\QQBot\schedules.json` |
| `rvcModelFile` | `D:\software\Voice\rvc_model.txt` |
| `napcatApi` | `http://127.0.0.1:13200` |
| `autoCollectMinutes` | `5` |

## 说明

- 面板走本机 HTTP（`http://127.0.0.1:9877`），不引入额外协议依赖
- 插件对宿主无破坏性操作：所有异常内部捕获，端口占用自动换端口
- 定时任务格式见面板内「定时任务 → 高级 JSON」

## License

MIT
