#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""点歌 / 切片工具：从本地曲库里找歌，按段落、时长、升降 key 切片，
输出 mp3（文件）或 wav（语音条）。

用法（一般由 /点歌 命令自动调用）：
    python songreq.py plan "晴天 副歌 30秒 升2key"
    python songreq.py cut --file <path> --start 45 --dur 30 --key 2 --format mp3 --out <path>
    python songreq.py search 晴天
"""
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
import argparse
import json
import os
import re
import subprocess
import time

LIB_FILE = r"D:\software\QQBot\曲库目录.txt"


def _load_dirs():
    """曲库目录：优先读 曲库目录.txt（每行一个文件夹），没配置就用默认 Music。"""
    dirs = []
    if os.path.exists(LIB_FILE):
        try:
            with open(LIB_FILE, encoding="utf-8") as f:
                for line in f:
                    d = line.strip().strip('"').strip("'")
                    if d and not d.startswith("#") and os.path.isdir(d):
                        dirs.append(d)
        except Exception:
            pass
    return dirs or [r"C:\Users\<你的用户名>\Music"]


MUSIC_DIRS = _load_dirs()
FFMPEG = r"D:\software\Voice\ffmpeg\package\ffmpeg.exe"
OUT_DIR = r"D:\software\QQBot\media\songs"
EXTS = (".mp3", ".flac", ".m4a", ".wav", ".ogg", ".aac")
DEFAULT_DUR = 25
MAX_DUR_VOICE = 59          # 语音条上限（秒）
MAX_DUR_FILE = 180          # 文件形式最多切 3 分钟


def norm(s):
    return re.sub(r"[\s\-_()（）\[\]【】·,，.。'\"“”]", "", str(s)).lower()


def get_duration(path):
    try:
        r = subprocess.run([FFMPEG, "-hide_banner", "-i", path, "-f", "null", "-"],
                           capture_output=True, text=True, encoding="utf-8", errors="ignore")
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", r.stderr or "")
        if not m:
            return 0.0
        h, mnt, sec = int(m.group(1)), int(m.group(2)), float(m.group(3))
        return h * 3600 + mnt * 60 + sec
    except Exception:
        return 0.0


def library():
    files = []
    for d in MUSIC_DIRS:
        if not os.path.isdir(d):
            continue
        for root, _dirs, names in os.walk(d):
            for n in names:
                if n.lower().endswith(EXTS):
                    files.append(os.path.join(root, n))
    return files



def find_hook(path, dur=25.0):
    """找全曲里最像副歌/高潮的片段起点：取「持续响度最高」的 dur 秒窗口（排除开头前 15% 和结尾 8%）。"""
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
        # 平滑 + 滑动窗口均值（用累积和加速）
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


def find_song(raw):
    """从整句里挑出最像歌名的部分，返回 (path, 剩余要求文本)。"""
    files = library()
    tokens = [t for t in re.split(r"\s+", raw.strip()) if t]
    best = None
    best_len = 0
    for take in range(min(4, len(tokens)), 0, -1):
        cand = " ".join(tokens[:take])
        nc = norm(cand)
        if not nc:
            continue
        for p in files:
            stem = os.path.splitext(os.path.basename(p))[0]
            ns = norm(stem)
            if ns == nc:
                score = 1000 + len(nc)
            elif ns.startswith(nc) or ns.endswith(nc):
                score = 500 + len(nc)
            elif nc in ns:
                score = 100 + len(nc)
            else:
                continue
            stem_l = os.path.basename(p).lower()
            if ("live" in stem_l or "演唱会" in stem_l) and "live" not in raw.lower() and "演唱会" not in raw:
                score -= 400
            if score > best_len:
                best_len = score
                best = (p, " ".join(tokens[take:]))
        if best is not None:
            break
    return best if best else (None, raw)


def parse_requirements(text, song_len):
    info = {"dur": DEFAULT_DUR, "key": 0, "format": "wav", "anchor": None, "lyric": "", "note": []}

    m = re.search(r"(\d+)\s*(分钟|分(?!钟)|min)", text, re.I)
    if m:
        info["dur"] = int(m.group(1)) * 60
    m = re.search(r"(\d+)\s*(秒|s\b|sec)", text, re.I)
    if m:
        info["dur"] = int(m.group(1))

    if "副歌" in text:
        info["anchor"] = 0.55
    elif re.search(r"(结尾|最后|末尾).{0,6}主歌|主歌.{0,6}(结尾|最后)", text):
        info["anchor"] = 0.72
    elif re.search(r"(开头|第一段|开始).{0,6}主歌|主歌.{0,6}(开头|第一段)", text):
        info["anchor"] = 0.12
    elif "主歌" in text:
        info["anchor"] = 0.12
    seg = re.search(r"第\s*(\d+)\s*段", text)
    if seg:
        n = int(seg.group(1))
        info["anchor"] = [0.08, 0.26, 0.44, 0.60, 0.74][min(n - 1, 4)]

    m = re.search(r"(升|降)\s*(\d+)?\s*(个)?\s*(key|调|度)", text, re.I)
    if m:
        base = int(m.group(2) or 2)
        info["key"] = base if m.group(1) == "升" else -base
    m = re.search(r"([+-]\s*\d+)\s*(key|调|度)", text, re.I)
    if m:
        info["key"] = int(m.group(1).replace(" ", ""))

    if re.search(r"语音条|语音|voice", text, re.I):
        info["format"] = "wav"
    if re.search(r"mp3|文件|附件", text, re.I):
        info["format"] = "mp3"

    q = re.search(r"[「『\"“]([^」』\"”]{2,30})[」』\"”]", text)
    if q:
        info["lyric"] = q.group(1)

    if info["format"] == "wav":
        info["dur"] = min(info["dur"], MAX_DUR_VOICE)
    else:
        info["dur"] = min(info["dur"], MAX_DUR_FILE)

    if info["anchor"] is None:
        info["start"] = 0.0
        return info
    if song_len > 0:
        info["start"] = max(0.0, round(song_len * info["anchor"], 1))
        if info["start"] + info["dur"] > song_len:
            info["start"] = max(0.0, round(song_len - info["dur"], 1))
    else:
        info["start"] = 0.0
    return info


def cmd_plan(raw):
    mode = "cover"          # 默认：小鲸唱（RVC）
    if "原唱" in raw:
        mode = "original"
        raw = raw.replace("原唱", " ")
    raw = re.sub(r"^/?(点歌|唱歌|点唱)\s*", "", raw)
    # 去掉"唱/来/点/放/给我/整一首"这类动词，别当成歌名
    raw = re.sub(r"^\s*(唱|来|点|放|整|搞|给我|我要听|想听)\s*(一|两)?\s*(首|段|个)?\s*", "", raw)
    path, rest = find_song(raw)
    if not path:
        # 给几个相近的歌名提示，别只说"没找到"
        import difflib
        titles = []
        for f in library():
            stem = os.path.splitext(os.path.basename(f))[0]
            title = re.split(r"\s*[-–—]\s*", stem)[0].strip()   # "晴天 - 周杰伦" → "晴天"
            titles.append(title)
        q = raw.strip()
        scored = sorted(((difflib.SequenceMatcher(None, q, x).ratio(), x) for x in set(titles)),
                        reverse=True)
        sug = [x for r, x in scored[:3] if r >= 0.45]
        if not sug and len(q) >= 2:
            sug = [x for x in titles if q in x][:3]   # 名字被搜得更长的情况
        print(json.dumps({"ok": False, "error": "曲库里没找到这首歌", "raw": raw,
                          "suggest": sug}, ensure_ascii=False))
        return 0
    length = get_duration(path)
    info = parse_requirements(rest, length)
    if info["anchor"] is None:
        hook = find_hook(path, info["dur"])
        info["start"] = hook
    title = os.path.splitext(os.path.basename(path))[0]
    print(json.dumps({
        "ok": True, "file": path, "title": title,
        "length": round(length, 1), "rest": rest,
        "start": info["start"], "dur": info["dur"], "key": info["key"],
        "format": info["format"], "lyric": info["lyric"], "mode": mode,
    }, ensure_ascii=False))
    return 0


def cmd_search(kw):
    nk = norm(kw)
    hits = [p for p in library() if nk in norm(os.path.basename(p))]
    for p in hits[:15]:
        print("%.1fs  %s" % (get_duration(p), os.path.basename(p)))
    print("共 %d 个匹配" % len(hits))
    return 0


def cmd_cut(args):
    os.makedirs(os.path.dirname(args.out) or OUT_DIR, exist_ok=True)
    vf = []
    if args.key:
        # 变调不变速：改采样率再拉回时长
        ratio = 2 ** (args.key / 12.0)
        vf.append("asetrate=44100*%f,aresample=44100,atempo=%f" % (ratio, 1.0 / ratio))
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
           "-ss", str(args.start), "-t", str(args.dur), "-i", args.file]
    if vf:
        cmd += ["-af", ",".join(vf)]
    if args.format == "mp3":
        cmd += ["-vn", "-ac", "2", "-ar", "44100", "-b:a", "192k", args.out]
    else:
        cmd += ["-vn", "-ac", "1", "-ar", "32000", args.out]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.returncode != 0 or not os.path.exists(args.out):
        print("切片失败: " + (r.stderr or "")[:300], file=sys.stderr)
        return 1
    print(args.out)
    return 0



COVER = r"D:\software\Voice\cover\cover.py"
COVER_OUT = r"D:\software\QQBot\workspace\voice\cover_out"
BASE_PITCH = 3          # 默认音高


def cmd_sing(args):
    outdir = os.path.join(COVER_OUT, "work_" + str(int(time.time())))
    os.makedirs(outdir, exist_ok=True)
    pitch = BASE_PITCH + args.key
    pitch = max(-3, min(9, pitch))
    start = max(0.0, args.start)
    dur = max(15.0, min(55.0, args.dur))
    cmd = [sys.executable, COVER, "--song", args.file, "--start", str(start),
           "--dur", str(dur), "--intro-max", "8", "--pitch", str(pitch),
           "--outdir", outdir]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.returncode != 0:
        print("唱失败: " + ((r.stderr or r.stdout or "")[:300]), file=sys.stderr)
        return 1
    mp3 = None
    for root, _d, files in os.walk(outdir):
        for n in files:
            if n.endswith(".mp3"):
                mp3 = os.path.join(root, n)
    if not mp3:
        print("唱失败: 没有输出文件", file=sys.stderr)
        return 1
    if args.format == "mp3":
        os.replace(mp3, args.out) if os.path.dirname(mp3) == os.path.dirname(args.out) else __import__("shutil").copyfile(mp3, args.out)
    else:
        r2 = subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", mp3,
                             "-ac", "1", "-ar", "32000",
                             "-af", "loudnorm=I=-15:TP=-1.5:LRA=9", args.out],
                            capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if r2.returncode != 0:
            print("转语音失败: " + (r2.stderr or "")[:300], file=sys.stderr)
            return 1
    __import__("shutil").rmtree(outdir, ignore_errors=True)
    print(args.out)
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("raw")
    s = sub.add_parser("search")
    s.add_argument("keyword")
    c = sub.add_parser("cut")
    c.add_argument("--file", required=True)
    c.add_argument("--start", type=float, default=0)
    c.add_argument("--dur", type=float, default=DEFAULT_DUR)
    c.add_argument("--key", type=int, default=0)
    c.add_argument("--format", choices=["mp3", "wav"], default="mp3")
    c.add_argument("--out", required=True)
    g = sub.add_parser("sing")
    g.add_argument("--file", required=True)
    g.add_argument("--start", type=float, default=0)
    g.add_argument("--dur", type=float, default=DEFAULT_DUR)
    g.add_argument("--key", type=int, default=0)
    g.add_argument("--format", choices=["mp3", "wav"], default="mp3")
    g.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.cmd == "plan":
        return cmd_plan(args.raw)
    if args.cmd == "search":
        return cmd_search(args.keyword)
    if args.cmd == "sing":
        return cmd_sing(args)
    return cmd_cut(args)


if __name__ == "__main__":
    sys.exit(main())
