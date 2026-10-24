#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""训练素材预处理：把长录音切成 3~12 秒片段并归一化，输出到 dataset/.

用法：
    python build_dataset.py --input "我的清唱.m4a" --out dataset --min 3 --max 12

处理逻辑：
1. 读入音频（任意格式，ffmpeg 解码）
2. 按静音切成句子（librosa.effects.split）
3. 太短的丢掉、太长的再切
4. 峰值归一到 0.9，统一 48k 单声道（RVC v2 训练用）
5. 输出 dataset/0001.wav ...

之后把这些 wav 放进 RVC WebUI 的 dataset/<实验名>/ 即可开始训练。
"""
import argparse
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FFMPEG = r"D:\software\Voice\ffmpeg\package\ffmpeg.exe"


def decode(src: str, dst: str):
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                    "-i", src, "-ac", "1", "-ar", "48000", dst], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="原始录音/歌曲人声")
    ap.add_argument("--out", default="dataset", help="输出目录")
    ap.add_argument("--min", type=float, default=3.0, help="最短片段秒数")
    ap.add_argument("--max", type=float, default=12.0, help="最长片段秒数")
    ap.add_argument("--top-db", type=float, default=30.0, help="静音阈值（dB）")
    ap.add_argument("--sr", type=int, default=48000, help="输出采样率")
    args = ap.parse_args()

    import librosa
    import numpy as np
    import soundfile as sf

    os.makedirs(args.out, exist_ok=True)
    tmp = os.path.join(args.out, "_full.wav")
    decode(args.input, tmp)

    y, sr = librosa.load(tmp, sr=args.sr, mono=True)
    print("总时长 %.1f 秒" % (len(y) / sr))

    # 按静音切句
    intervals = librosa.effects.split(y, top_db=args.top_db)
    min_len = int(args.min * sr)
    max_len = int(args.max * sr)

    pieces = []
    for s, e in intervals:
        seg = y[s:e]
        if len(seg) < min_len * 0.6:
            continue
        # 太长的再按 max 切
        for i in range(0, len(seg), max_len):
            part = seg[i:i + max_len]
            if len(part) >= min_len * 0.8:
                pieces.append(part)

    if not pieces:
        print("没切出片段：录音可能太短或静音阈值不对")
        return 1

    n = 0
    for part in pieces:
        peak = float(np.max(np.abs(part)))
        if peak < 1e-4:
            continue
        sf.write(os.path.join(args.out, "%04d.wav" % n), part * (0.9 / peak), sr)
        n += 1

    os.remove(tmp)
    total = sum(len(p) for p in pieces) / sr
    print("完成：%d 段，共 %.1f 秒（平均 %.1f 秒/段）" % (n, total, total / max(n, 1)))
    print("下一步：把 %s 里的 wav 放进 RVC WebUI 的 dataset/<实验名>/" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
