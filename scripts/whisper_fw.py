#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""faster-whisper 转写 CLI：给 dsh-onebot 插件的 STT custom 引擎用。

用法（插件 sttCommand/sttArgs 模板）：
    python whisper_fw.py <输入音频> <输出txt路径> [模型名]

特点：
- CPU int8，速度快（10 秒语音约 2~4 秒）
- 首次运行会下载模型到 HF 缓存（可用 HF_ENDPOINT=https://hf-mirror.com）
- 失败时退出码非 0，插件会降级成 [语音] 占位
"""
import os
import sys

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: whisper_fw.py <audio> <out.txt> [model]", file=sys.stderr)
        return 2
    audio, out = sys.argv[1], sys.argv[2]
    model_name = sys.argv[3] if len(sys.argv) > 3 else "small"

    from faster_whisper import WhisperModel

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        audio, language="zh", vad_filter=True, beam_size=5,
        initial_prompt="以下是普通话的句子，请用简体中文输出。",
        condition_on_previous_text=False)
    text = "".join(seg.text for seg in segments).strip()
    try:  # whisper 有时输出繁体，统一转简体
        from opencc import OpenCC
        text = OpenCC("t2s").convert(text)
    except Exception:
        pass

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
