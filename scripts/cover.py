#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""小鲸翻唱流水线：原曲 → 分离人声 → 换成小鲸音色 → 混回伴奏。

用法示例：
    D:\\software\\Voice\\py310\\python.exe cover.py --song "C:\\...\\一路向北.mp3" --start 60 --dur 30
    ... --no-mix        # 只要换声后的人声（清唱）
    ... --keep          # 保留中间文件

输出：D:\\software\\Voice\\cover\\out\\<曲名>_<开始秒>_cover.mp3
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys

ROOT = r"D:\software\Voice"
PY_MAIN = os.path.join(ROOT, "py310", "python.exe")
PY_VENV = os.path.join(ROOT, "cover", "venv", "Scripts", "python.exe")
FFMPEG = os.path.join(ROOT, "ffmpeg", "package", "ffmpeg.exe")
SEEDVC = os.path.join(ROOT, "cover", "seed-vc-main")

DIT_CKPT = os.path.join(
    ROOT, "cover", "checkpoints",
    "models--Plachta--Seed-VC", "snapshots")
CONFIG_YML = os.path.join(SEEDVC, "configs", "presets",
                          "config_dit_mel_seed_uvit_whisper_base_f0_44k.yml")
TARGET_VOICE = os.path.join(ROOT, "refs", "ref.wav")


def run(cmd, desc):
    print("[cover] %s" % desc, flush=True)
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if p.returncode != 0:
        print(p.stdout[-2000:] if p.stdout else "", file=sys.stderr)
        print(p.stderr[-3000:] if p.stderr else "", file=sys.stderr)
        raise SystemExit("步骤失败：%s" % desc)
    return p.stdout


def find_dit_checkpoint():
    hits = glob.glob(os.path.join(DIT_CKPT, "*", "DiT_seed_v2_uvit_whisper_base_f0_44k_*.pth"))
    if not hits:
        raise SystemExit("找不到 Seed-VC 模型，请先运行 dl_models.py")
    return hits[0]



def find_hook(path, dur):
    """全曲最像副歌/高潮的起点（持续响度最高的 dur 秒窗口，排除开头/结尾）。"""
    try:
        import numpy as np
        import librosa
        y, sr = librosa.load(path, sr=22050, mono=True)
        hop = 512
        rms = librosa.feature.rms(y=y, hop_length=hop)[0]
        fps = sr / float(hop)
        win = max(4, int(dur * fps))
        if len(rms) <= win:
            return 0.0
        k = np.ones(max(1, int(fps * 2))) / max(1, int(fps * 2))
        smooth = np.convolve(rms, k, mode="same")
        cs = np.cumsum(np.insert(smooth, 0, 0.0))
        sums = cs[win:] - cs[:-win]
        n = len(sums)
        lo = int(n * 0.15)
        hi = max(lo + 1, int(n * 0.92))
        idx = lo + int(np.argmax(sums[lo:hi]))
        return round(idx / fps, 1)
    except Exception:
        return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--song", required=True, help="原曲文件（mp3/wav/m4a/flac）")
    ap.add_argument("--start", type=float, default=None, help="从第几秒开始截（含前奏，保留必要衔接）")
    ap.add_argument("--dur", type=float, default=25, help="截多长（秒）：30~60，可更长；按歌曲结构定（前奏+主歌+副歌）")
    
    ap.add_argument("--index-rate", type=float, default=0.5)
    ap.add_argument("--f0-method", default="rmvpe", choices=["pm","rmvpe"])
    ap.add_argument("--intro-max", type=float, default=8.0, help="前奏最长多少秒（原曲前奏更长会自动跳过开头）")
    ap.add_argument("--pitch", type=int, default=None, help="音高偏移半音：男声→女声约 +12，同性别 0")
    ap.add_argument("--no-mix", action="store_true", help="不做混音，只出换声后人声（清唱）")
    ap.add_argument("--keep", action="store_true", help="保留中间文件")
    ap.add_argument("--outdir", default=os.path.join(ROOT, "cover", "out"))
    args = ap.parse_args()

    if args.start is None:
        args.start = find_hook(args.song, args.dur)
        print("[cover] 未指定片段 → 自动选高潮/副歌起点 %.1fs" % args.start, flush=True)
    song = os.path.abspath(args.song)
    if not os.path.exists(song):
        raise SystemExit("找不到歌曲：%s" % song)
    os.makedirs(args.outdir, exist_ok=True)
    name = os.path.splitext(os.path.basename(song))[0]
    WORK_ROOT = os.environ.get("QIWORK", r"D:\software\QQBot\workspace\voice\work")
    os.makedirs(WORK_ROOT, exist_ok=True)
    work = os.path.join(WORK_ROOT, "%s_%d" % (name, int(args.start)))
    os.makedirs(work, exist_ok=True)

    clip = os.path.join(work, "clip.wav")
    run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
         "-ss", str(args.start), "-t", str(args.dur + 6), "-i", song,
         "-ac", "2", "-ar", "44100", clip], "截取片段 %.0f~%.0fs" % (args.start, args.start + args.dur))

    sep_root = os.path.join(work, "sep")
    run([PY_MAIN, "-m", "demucs", "--two-stems=vocals", "-n", "htdemucs",
         "--out", sep_root, clip], "分离人声/伴奏（CPU 约 1~2 分钟）")
    vocals = os.path.join(sep_root, "htdemucs", "clip", "vocals.wav")
    inst = os.path.join(sep_root, "htdemucs", "clip", "no_vocals.wav")
    if not os.path.exists(vocals):
        raise SystemExit("分离失败，找不到 vocals.wav")

    # 前奏限长：检测人声进入时间，超过 intro_max 就把两条轨一起前移（跳过部分原前奏）
    import numpy as np
    import soundfile as sf

    v, vsr = sf.read(vocals)
    if v.ndim > 1:
        v = v.mean(1)
    win = int(0.25 * vsr)
    vocal_start = 0.0
    for i in range(0, len(v) - win, win):
        if float(np.sqrt(np.mean(v[i:i + win] ** 2))) > 0.02:
            vocal_start = i / float(vsr)
            break
    # 自动定调：测源人声中位音高，按「目标 290Hz」反推升/降半音数
    if args.pitch is None:
        try:
            import librosa
            y32, sr32 = librosa.load(vocals, sr=22050, mono=True, duration=40)
            f0 = librosa.yin(y32, fmin=70, fmax=800, sr=sr32)
            f0 = f0[np.isfinite(f0)]
            med = float(np.median(f0))
            args.pitch = int(round(12.0 * np.log2(290.0 / max(med, 60.0))))
            args.pitch = max(-2, min(6, args.pitch))
            print("[cover] 源人声中位 %.0fHz → 目标 290Hz → 音高 %+d" % (med, args.pitch), flush=True)
        except Exception as exc:
            args.pitch = 3
            print("[cover] 自动定调失败(%s)，用 +3" % exc, flush=True)
    shift = max(0.0, vocal_start - args.intro_max)
    if shift > 0.05:
        print("[cover] 人声在 %.1fs 才进入，前奏过长，整体前移 %.1fs" % (vocal_start, shift), flush=True)
        for path in (vocals, inst):
            data, sr0 = sf.read(path)
            keep = data[int(shift * sr0):]
            sf.write(path, keep, sr0)
        args.dur = max(10.0, args.dur - shift)

    # 结尾对齐整句：在目标时长附近找人声停顿，把尾巴延到这句唱完（最多多 5 秒）
    try:
        v2, sr2 = sf.read(vocals)
        if v2.ndim > 1:
            v2 = v2.mean(1)
        hop = int(0.05 * sr2)
        n = len(v2) // hop
        rms = np.array([np.sqrt(np.mean(v2[i * hop:(i + 1) * hop] ** 2)) for i in range(n)])
        thr = max(0.008, float(np.median(rms[rms > 0.005])) * 0.35) if np.any(rms > 0.005) else 0.01
        voiced = rms > thr
        target = int(args.dur / 0.05)
        target = min(target, n - 1)
        gap = int(0.15 / 0.05)          # 150ms 静音算换气
        end_f = None
        # 从目标点往后找第一个 >=150ms 的静音，代表这句唱完
        i = target
        while i < min(n - gap, target + int(5.0 / 0.05)):
            if not voiced[i:i + gap].any():
                end_f = i
                break
            i += 1
        if end_f is not None:
            end_t = end_f * 0.05
            if end_t > args.dur + 0.05:
                print("[cover] 结尾延长 %.1fs 到整句唱完" % (end_t - args.dur), flush=True)
            if end_t < args.dur - 0.05:
                print("[cover] 结尾收短 %.1fs 到整句边界" % (args.dur - end_t), flush=True)
            args.dur = max(8.0, end_t)
            for path in (vocals, inst):
                data, sr0 = sf.read(path)
                sf.write(path, data[:int(args.dur * sr0)], sr0)
    except Exception as exc:
        print("[cover] 整句对齐跳过: %s" % exc, flush=True)

    svc_out = os.path.join(work, "rvc_converted.wav")
    # 用常驻 RVC 服务（9850）换成专属音色；服务没开就先试着启动
    import json as _json
    import urllib.request as _ur

    payload = _json.dumps({
        "input": vocals,
        "output": svc_out,
        "pitch": args.pitch,
        "protect": 0.35,
        "index_rate": args.index_rate,
        "rms_mix_rate": 0.2,
        "f0_method": args.f0_method,
    }).encode("utf-8")
    print("[cover] 换成小鲸音色（RVC，CPU 约 1~3 分钟）", flush=True)
    try:
        req = _ur.Request("http://127.0.0.1:9850/rvc", data=payload,
                          headers={"Content-Type": "application/json"})
        resp = _json.loads(_ur.urlopen(req, timeout=1800).read().decode("utf-8"))
    except Exception as exc:
        # 服务没开：自动拉起再试一次
        print("[cover] RVC 服务未响应，自动启动中（约 60 秒）...", flush=True)
        try:
            subprocess.Popen([PY_MAIN, os.path.join(ROOT, "cover", "rvc_server.py")],
                             cwd=r"D:\software\Voice\cover\rvc_pack\Retrieval-based-Voice-Conversion-WebUI-main",
                             creationflags=0x00000008, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import time as _t
            for _ in range(45):
                _t.sleep(2)
                try:
                    resp = _json.loads(_ur.urlopen(req, timeout=600).read().decode("utf-8"))
                    break
                except Exception:
                    resp = None
            if not resp:
                raise SystemExit("RVC 服务自动启动失败：%s" % exc)
        except SystemExit:
            raise
        except Exception as exc2:
            raise SystemExit("RVC 服务不可用（9850）：%s" % exc2)
    if not resp.get("ok") or not os.path.exists(svc_out):
        raise SystemExit("RVC 转换失败：%s" % resp.get("error"))
    conv = svc_out

    if args.no_mix:
        dst = os.path.join(args.outdir, "%s_%d_清唱.wav" % (name, int(args.start)))
        shutil.copyfile(conv, dst)
    else:
        dst = os.path.join(args.outdir, "%s_%d_cover.mp3" % (name, int(args.start)))
        # 伴奏必须和降调后的人声同调：按同样的半音数变调（保持速度）
        inst_shifted = inst
        if args.pitch != 0:
            ratio = 2.0 ** (args.pitch / 12.0)
            inst_shifted = os.path.join(work, "inst_shifted.wav")
            run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", inst,
                 "-af", "asetrate=%d*%.6f,aresample=%d,atempo=%.6f" % (44100, ratio, 44100, 1.0 / ratio),
                 inst_shifted], "伴奏同步变调 %+d 半音" % args.pitch)
        run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
             "-i", conv, "-i", inst_shifted,
             "-filter_complex",
             "[0:a]equalizer=f=6500:width_type=o:width=1.5:g=-5,equalizer=f=9000:width_type=o:width=1.5:g=-3,acompressor=threshold=-18dB:ratio=2.0:attack=8:release=200,volume=1.2,alimiter=limit=0.88[vo];[1:a]volume=0.75,alimiter=limit=0.88[inst];[vo][inst]amix=inputs=2:duration=shortest,highshelf=f=3000:g=0.8,loudnorm=I=-14:TP=-2.5:LRA=9,alimiter=limit=0.94:level=false",
             "-ac", "1", "-ar", "32000", "-b:a", "128k", dst], "混音输出")

    print("[cover] 完成：%s" % dst, flush=True)
    if not args.keep:
        shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
