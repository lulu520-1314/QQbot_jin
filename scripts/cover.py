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



# ---------- 面板可调参数（params.json） ----------
def _load_cover_params():
    base = {"targetHz": 290.0, "pitchMin": -2, "pitchMax": 6, "protect": 0.35,
            "indexRate": 0.5, "vocalVol": 1.2, "instVol": 0.75, "loudnessI": -14.0}
    try:
        import json as _j
        d = _j.load(open(r"D:\software\Voice\params.json", encoding="utf-8"))
        base.update(d.get("cover") or {})
    except Exception:
        pass
    return base


COVER_PARAMS = _load_cover_params()


def _rvc_call(inp, outp, pitch, index_rate=0.5, protect=0.35):
    import json as _j
    import urllib.request as _u
    payload = _j.dumps({"input": inp, "output": outp, "pitch": int(pitch),
                        "protect": protect, "index_rate": index_rate,
                        "rms_mix_rate": 0.2, "f0_method": "rmvpe"}).encode("utf-8")
    req = _u.Request("http://127.0.0.1:9850/rvc", data=payload,
                     headers={"Content-Type": "application/json"})
    r = _j.loads(_u.urlopen(req, timeout=1800).read().decode("utf-8"))
    if not r.get("ok") or not os.path.exists(outp):
        raise SystemExit("RVC 失败：%s" % r.get("error"))
    return outp


def multi_key_process(vocals, inst, work, target=290.0, cap=6):
    """按段落分别定调：主歌用低 key、副歌用高 key，伴奏分段跟着变，再拼回整段。"""
    import numpy as np
    import soundfile as sf
    import librosa

    v, sr = sf.read(vocals)
    mono = v.mean(1) if v.ndim > 1 else v
    hop = int(0.05 * sr)
    n = len(mono) // hop
    rms = np.array([np.sqrt(np.mean(mono[i * hop:(i + 1) * hop] ** 2)) for i in range(n)])
    voiced = rms > max(0.008, float(np.median(rms[rms > 0.005])) * 0.35)
    gap = int(0.7 / 0.05)
    bounds = [0.0]
    i = int(2.0 / 0.05)
    while i < n - gap:
        if not voiced[i:i + gap].any():
            bounds.append(i * 0.05)
            i += gap
        else:
            i += 1
    bounds.append(len(mono) / float(sr))
    secs = [(bounds[k], bounds[k + 1]) for k in range(len(bounds) - 1)]
    merged = []
    for s0, e0 in secs:
        if merged and (e0 - s0) < 6.0:
            merged[-1] = (merged[-1][0], e0)
        else:
            merged.append((s0, e0))
    if len(merged) < 2:
        return None

    pitches, parts_v, parts_i = [], [], []
    for k, (s0, e0) in enumerate(merged):
        seg = mono[int(s0 * sr):int(e0 * sr)]
        try:
            f0, _, _ = librosa.pyin(seg, fmin=80, fmax=500, sr=sr)
            f0 = f0[np.isfinite(f0)]
            med = float(np.median(f0)) if f0.size else 0.0
        except Exception:
            med = 0.0
        pit = int(round(12.0 * np.log2(target / med))) if med > 60 else 0
        pit = max(-3, min(cap, pit))
        pitches.append(pit)
        print("[cover] 第 %d 段 %.1f~%.1fs 中位 %.0fHz → 音高 %+d" % (k + 1, s0, e0, med, pit), flush=True)

        vs = os.path.join(work, "mv%d.wav" % k)
        run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", str(s0), "-t", str(e0 - s0),
             "-i", vocals, "-ac", "1", "-ar", "32000", vs], "切人声段 %d" % (k + 1))
        vc = os.path.join(work, "mvc%d.wav" % k)
        _rvc_call(vs, vc, pit)
        parts_v.append((s0, vc))

        isg = os.path.join(work, "mi%d.wav" % k)
        ratio = 2.0 ** (pit / 12.0)
        run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", str(s0), "-t", str(e0 - s0),
             "-i", inst, "-af", "asetrate=44100*%.6f,aresample=44100,atempo=%.6f" % (ratio, 1.0 / ratio),
             isg], "切伴奏段并变调 %+d" % pit)
        parts_i.append((s0, isg))

    def build(parts, name):
        out = os.path.join(work, name)
        cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error"]
        for _, pth in parts:
            cmd += ["-i", pth]
        filt = ""
        for idx, (s0, _) in enumerate(parts):
            filt += "[%d:a]adelay=%d|%d[v%d];" % (idx, int(s0 * 1000), int(s0 * 1000), idx)
        for idx in range(len(parts)):
            filt += "[v%d]" % idx
        filt += "amix=inputs=%d:duration=longest,volume=%d[out]" % (len(parts), len(parts))
        cmd += ["-filter_complex", filt, "-map", "[out]", "-ac", "1", "-ar", "32000", out]
        run(cmd, "拼接分段结果")
        return out

    return build(parts_v, "vocals_multi.wav"), build(parts_i, "inst_multi.wav")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--song", required=True, help="原曲文件（mp3/wav/m4a/flac）")
    ap.add_argument("--start", type=float, default=None, help="从第几秒开始截（含前奏，保留必要衔接）")
    ap.add_argument("--dur", type=float, default=None, help="截多长（秒），不填默认 35（一整段副歌），结尾会自动对齐整句")
    
    ap.add_argument("--index-rate", type=float, default=0.5)
    ap.add_argument("--f0-method", default="rmvpe", choices=["pm","rmvpe"])
    ap.add_argument("--intro-max", type=float, default=8.0, help="前奏最长多少秒（原曲前奏更长会自动跳过开头）")
    ap.add_argument("--pitch", type=int, default=None, help="音高偏移半音：男声→女声约 +12，同性别 0")
    ap.add_argument("--sep-model", default="htdemucs", choices=["htdemucs", "htdemucs_ft", "mdx_q", "mdx_extra_q"], help="分离模型：htdemucs 默认；mdx_q 更快；htdemucs_ft 更干净但慢 4 倍")
    ap.add_argument("--vocals", default="", help="已分离好的人声（如 UVR5 输出）；配合 --inst 使用可跳过 demucs。注意：此时 --start 是相对这两个文件的时间")
    ap.add_argument("--inst", default="", help="已分离好的伴奏")
    ap.add_argument("--multi-key", action=argparse.BooleanOptionalAction, default=True, help="分段定调：主歌/副歌各用合适的 key（默认开）")
    ap.add_argument("--no-mix", action="store_true", help="不做混音，只出换声后人声（清唱）")
    ap.add_argument("--keep", action="store_true", help="保留中间文件")
    ap.add_argument("--outdir", default=os.path.join(ROOT, "cover", "out"))
    args = ap.parse_args()

    if args.dur is None:
        args.dur = 35.0        # 默认按"一整段副歌"给 35 秒，结尾再自动对齐整句
    if args.start is None:
        args.start = find_hook(args.vocals or args.song, 25)
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
    if args.vocals and args.inst:
        # 已经用 UVR5 / 其他工具分离好：直接切这两条轨，跳过 demucs（省 1 分钟）
        vocals = os.path.join(work, "vocals.wav")
        inst = os.path.join(work, "inst.wav")
        for src, dst in ((args.vocals, vocals), (args.inst, inst)):
            run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                 "-ss", str(args.start), "-t", str(args.dur + 6), "-i", src,
                 "-ac", "2", "-ar", "44100", dst], "切分现成分离轨")
    else:
        # 分离结果缓存：同一首歌同一片段第二次起直接复用（省 30~60 秒）
        import hashlib
        cache_root = os.environ.get("QISTEMS", r"D:\software\QQBot\workspace\voice\stems_cache")
        key = hashlib.md5(("%s|%d|%d|%s" % (os.path.abspath(song), int(args.start), int(args.dur), args.sep_model)).encode("utf-8")).hexdigest()[:16]
        cache_dir = os.path.join(cache_root, key)
        c_voc = os.path.join(cache_dir, "vocals.wav")
        c_inst = os.path.join(cache_dir, "no_vocals.wav")
        if os.path.exists(c_voc) and os.path.exists(c_inst):
            print("[cover] 命中分离缓存，跳过 demucs", flush=True)
            vocals = os.path.join(work, "vocals.wav")
            inst = os.path.join(work, "inst.wav")
            import shutil as _sh2
            _sh2.copyfile(c_voc, vocals)
            _sh2.copyfile(c_inst, inst)
        else:
            run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                 "-ss", str(args.start), "-t", str(args.dur + 6), "-i", song,
                 "-ac", "2", "-ar", "44100", clip], "截取片段 %.0f~%.0fs" % (args.start, args.start + args.dur))
            sep_root = os.path.join(work, "sep")
            model_tag = args.sep_model
            run([PY_MAIN, "-m", "demucs", "--two-stems=vocals", "-n", model_tag,
                 "--out", sep_root, clip], "分离人声/伴奏（模型 %s，CPU 约 1~2 分钟）" % model_tag)
            vocals = os.path.join(sep_root, model_tag, "clip", "vocals.wav")
            inst = os.path.join(sep_root, model_tag, "clip", "no_vocals.wav")
            if os.path.exists(vocals) and os.path.exists(inst):
                try:
                    import shutil as _sh
                    os.makedirs(cache_dir, exist_ok=True)
                    _sh.copyfile(vocals, c_voc)
                    _sh.copyfile(inst, c_inst)
                    print("[cover] 分离结果已缓存", flush=True)
                except Exception:
                    pass
    if not os.path.exists(vocals):
        raise SystemExit("分离失败，找不到人声轨")

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
            y32, sr32 = librosa.load(vocals, sr=22050, mono=True)
            # 取最响的 20 秒窗口（通常是副歌）来定调，避免主歌把调拉低
            hop_l = 512
            rms_l = librosa.feature.rms(y=y32, hop_length=hop_l)[0]
            fps_l = sr32 / float(hop_l)
            w_l = max(4, int(20 * fps_l))
            if len(rms_l) > w_l:
                cs_l = np.cumsum(np.insert(rms_l, 0, 0.0))
                sums_l = cs_l[w_l:] - cs_l[:-w_l]
                s_idx = int(np.argmax(sums_l))
                seg_l = y32[int(s_idx / fps_l * sr32):int((s_idx + w_l) / fps_l * sr32)]
            else:
                seg_l = y32
            f0, vflag, _ = librosa.pyin(seg_l, fmin=80, fmax=500, sr=sr32, frame_length=2048)
            voiced = f0[np.isfinite(f0) & (vflag == True)]
            f0 = voiced if voiced.size >= 30 else librosa.yin(y32, fmin=80, fmax=500, sr=sr32)
            f0 = f0[np.isfinite(f0)]
            med = float(np.median(f0))
            args.pitch = int(round(12.0 * np.log2(float(COVER_PARAMS["targetHz"]) / max(med, 60.0))))
            args.pitch = max(int(COVER_PARAMS["pitchMin"]), min(int(COVER_PARAMS["pitchMax"]), args.pitch))
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
        gap = int(0.60 / 0.05)          # 600ms 静音算"这一整段唱完了"
        end_f = None
        # 从目标点往后找第一个 >=150ms 的静音，代表这句唱完
        i = target
        while i < min(n - gap, target + int(15.0 / 0.05)):
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

    conv = None
    inst_use = inst
    if args.multi_key:
        try:
            res = multi_key_process(vocals, inst, work)
            if res:
                conv, inst_use = res
                print("[cover] 分段定调完成（主歌/副歌各自 key）", flush=True)
        except SystemExit:
            raise
        except Exception as exc:
            print("[cover] 分段定调失败，退回整段统一调: %s" % exc, flush=True)

    svc_out = os.path.join(work, "rvc_converted.wav")
    # 用常驻 RVC 服务（9850）换成专属音色；服务没开就先试着启动
    import json as _json
    import urllib.request as _ur

    if conv is not None:
        print("[cover] 已用分段结果，跳过整段转换", flush=True)
    payload = _json.dumps({
        "input": vocals,
        "output": svc_out,
        "pitch": args.pitch,
        "protect": float(COVER_PARAMS["protect"]),
        "index_rate": args.index_rate,
        "rms_mix_rate": 0.2,
        "f0_method": args.f0_method,
    }).encode("utf-8")
    print("[cover] 换成小鲸音色（RVC，CPU 约 1~3 分钟）", flush=True)
    resp = None
    try:
        if conv is None:
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
    if conv is None:
        if not resp or not resp.get("ok") or not os.path.exists(svc_out):
            raise SystemExit("RVC 转换失败：%s" % (resp or {}).get("error"))
        conv = svc_out

    if args.no_mix:
        dst = os.path.join(args.outdir, "%s_%d_清唱.wav" % (name, int(args.start)))
        shutil.copyfile(conv, dst)
    else:
        dst = os.path.join(args.outdir, "%s_%d_cover.mp3" % (name, int(args.start)))
        # 伴奏必须和降调后的人声同调：按同样的半音数变调（保持速度）
        inst_shifted = inst_use
        if conv is svc_out or svc_out is None:
            pass
        if args.pitch != 0 and inst_shifted is inst:
            ratio = 2.0 ** (args.pitch / 12.0)
            inst_shifted = os.path.join(work, "inst_shifted.wav")
            run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", inst,
                 "-af", "asetrate=%d*%.6f,aresample=%d,atempo=%.6f" % (44100, ratio, 44100, 1.0 / ratio),
                 inst_shifted], "伴奏同步变调 %+d 半音" % args.pitch)
        run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
             "-i", conv, "-i", inst_shifted,
             "-filter_complex",
             "[0:a]equalizer=f=6500:width_type=o:width=1.5:g=-5,equalizer=f=9000:width_type=o:width=1.5:g=-3,acompressor=threshold=-18dB:ratio=2.0:attack=8:release=200,volume=%.2f,alimiter=limit=0.88[vo];[1:a]volume=%.2f,alimiter=limit=0.88[inst];[vo][inst]amix=inputs=2:duration=shortest,highshelf=f=3000:g=0.8,loudnorm=I=%.1f:TP=-2.5:LRA=9,alimiter=limit=0.94:level=false" % (float(COVER_PARAMS["vocalVol"]), float(COVER_PARAMS["instVol"]), float(COVER_PARAMS["loudnessI"])),
             "-ac", "1", "-ar", "32000", "-b:a", "128k", dst], "混音输出")

    print("[cover] 完成：%s" % dst, flush=True)
    if not args.keep:
        shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
