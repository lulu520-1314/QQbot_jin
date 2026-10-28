# 12 · 声音分离方案：demucs 与 UVR5（两种都行）

翻唱和训练素材都需要"人声 / 伴奏"分离。本项目提供两条路。

## 方案对比

| 项 | demucs（默认，已内置） | UVR5（Gui） |
|---|---|---|
| 形态 | 命令行，Python 包 | Windows 图形界面 |
| 安装 | `pip install demucs` | 下载整合包解压即用 |
| 速度（CPU，25 秒片段） | 30~60 秒 | 10~30 秒 |
| 质量 | 好（htdemucs）/ 很好（htdemucs_ft） | 好~很好（可选模型多） |
| 批量 | 脚本循环 | 原生支持 |
| 适合 | 全自动流水线 | 手工精修、做训练素材 |

> 作者日常：**成品翻唱用 demucs（自动化）**，**训练素材用 UVR5 或 htdemucs_ft（更干净）**。

---

## 一、demucs（本项目默认）

已集成在 `cover.py` 里，装好就能用：

```bash
pip install demucs==4.1.0
```

手动分离：

```bash
python -m demucs --two-stems=vocals -n htdemucs 你的歌.mp3
# 输出: separated/htdemucs/你的歌/vocals.wav  no_vocals.wav
```

想要更高音质（慢 4 倍）：

```bash
python -m demucs --two-stems=vocals -n htdemucs_ft 你的歌.mp3
```

---

## 二、UVR5（Ultimate Vocal Remover 5）

### 安装

1. 去 GitHub Releases 下载整合包（关键词：`Ultimate Vocal Remover 5`，作者 Anjok07）
2. 解压到任意目录（路径别带中文空格）
3. 双击 `Start Ultimate Vocal Remover.bat`

> 整合包已带 Python 环境，**不需要你另外装 Python**。

### 使用（图形界面）

1. `Input` 选择歌曲/文件夹，`Output` 选输出目录
2. `Select Process Method` → **MDX-Net**
3. `Select MDX Model` 建议：
   - `UVR-MDX-NET Inst HQ 3`（人声更干净）
   - `MDX23C-8KFFT-InstVoc_HQ`（质量最高，慢）
4. 勾选 `Vocals Only` / `Instrumental Only` 按需
5. 点 `Start Processing`

输出：

```
人声: xxx_(Vocals).wav
伴奏: xxx_(Instrumental).wav
```

### 用 UVR5 的结果跑翻唱（本项目已支持）

不需要再跑 demucs，直接把两条轨喂给 `cover.py`：

```powershell
python cover.py --song "原曲.mp3" ^
  --vocals "xxx_(Vocals).wav" --inst "xxx_(Instrumental).wav" ^
  --outdir out
```

- `--song` 仍要填（用于命名；不填 start 时也用它找副歌）
- **注意**：用了 `--vocals/--inst` 后，`--start` 是相对这两个文件的时间（0 = 分离文件的起点），不是原曲时间轴
- 省掉一次分离（快 30~60 秒）
- 训练素材尤其推荐这条：UVR5 分离更干净，模型音色更纯

### UVR5 命令行（进阶）

整合包里带 `uvr5` 的 CLI（不同版本入口不同，通常在 `python/` 下）：

```bash
python -m uvr5_cli --input 歌.mp3 --output out/ --model UVR-MDX-NET-Inst_HQ_3
```

具体参数以你下载的版本为准；**图形界面就够用了**。

---

## 三、训练素材怎么选分离器

| 素材来源 | 建议 |
|---|---|
| 自己清唱录音 | **不用分离**（最干净） |
| 自己跟伴奏录 | UVR5（Vocals Only） |
| 从歌里抠人声 | `htdemucs_ft` 或 UVR5 的 MDX23C |
| 网上找的伴奏/人声 | 质量参差，先听有没有残留再决定 |

> 判断标准：**放大听人声里有没有"嗡嗡"的乐器残留、有没有水声/金属声**。
> 有就换个模型再分一遍；分离不干净，训练出来的音色一定脏。

---

## 四、加速：分离缓存与模型选择

`cover.py` 已经内置两种加速：

```bash
# 1) 自动缓存（默认开启）：同一首歌同一片段第二次直接复用分离结果
#    缓存目录 workspace/voice/stems_cache/，删掉即清理

# 2) 换更快的分离模型（质量略降）
python cover.py --song 歌.mp3 --sep-model mdx_q --outdir out
```

\| 模型 | 速度 | 质量 |
|---|---|---|
| `htdemucs`（默认） | 中 | 好 |
| `mdx_q` | 快 | 中 |
| `mdx_extra_q` | 较快 | 中上 |
| `htdemucs_ft` | 慢 4 倍 | 最好 |

实测（作者机器，25 秒片段）：第一次 143 秒，命中缓存后 69 秒。

## 五、常见问题

| 现象 | 原因/解决 |
|---|---|
| 分离后人声发闷 | 模型选错，换 `Inst HQ 3` 或 `htdemucs_ft` |
| 人声里有鼓点 | 用 MDX23C 系列 |
| 分离很慢 | CPU 正常；有 GPU 会快很多 |
| UVR5 闪退 | 路径带中文/空格，或显卡驱动太旧 |
| 输出没声音 | 勾选了 `Vocals Only` 但实际选成了伴奏模型 |
