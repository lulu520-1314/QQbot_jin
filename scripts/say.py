#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Zero-shot TTS wrapper for GPT-SoVITS api_v2.py.

Usage:
    python say.py --text "浣犲ソ鍛€" --out D:\\software\\Voice\\out\\a.wav
    python say.py --text "..." --ref path.wav --prompt-text "鍙傝€冮煶棰戦噷璇寸殑璇?

Requires the GPT-SoVITS API server running on 127.0.0.1:9880
(start it with start-tts.cmd).
"""
import argparse
import json
import os
import subprocess
import sys
import time

import requests

API = os.environ.get("GSV_API", "http://127.0.0.1:9880")
DEFAULT_REF = os.environ.get("GSV_REF", r"D:\software\Voice\refs\ref.wav")
DEFAULT_PROMPT = os.environ.get("GSV_PROMPT", "")
PROMPT_FILE = r"D:\software\Voice\refs\ref.txt"
FFMPEG = os.environ.get("GSV_FFMPEG", r"D:\software\Voice\ffmpeg\package\ffmpeg.exe")


def load_prompt():
    if DEFAULT_PROMPT:
        return DEFAULT_PROMPT
    if os.path.exists(PROMPT_FILE):
        return open(PROMPT_FILE, encoding="utf-8-sig").read().strip()
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--out", default="")
    ap.add_argument("--ref", default=DEFAULT_REF)
    ap.add_argument("--prompt-text", default="")
    ap.add_argument("--lang", default="auto", choices=["auto", "zh", "en", "ja", "ko", "yue"])
    ap.add_argument("--prompt-lang", default="zh", help="参考音的语言（ref.txt 是什么语言就写什么）")
    ap.add_argument("--speed", type=float, default=None, help="语速倍数，1.0 原速；撒娇/傲娇建议 1.15~1.25")
    ap.add_argument("--mode", default="daily", choices=["daily", "tsundere", "warm"],
                    help="daily=撒娇+傲娇日常, tsundere=傲娇, warm=温暖大姐姐；决定默认语速")
    ap.add_argument("--no-loud", action="store_true", help="不做出站响度归一化")
    ap.add_argument("--presence", type=float, default=2.5, help="咬字清晰度：3kHz 以上提亮的增益 dB，0=关闭")
    ap.add_argument("--rvc", action="store_true", help="生成后用 RVC 换成专属音色（需 9850 服务）")
    ap.add_argument("--rvc-pitch", type=int, default=0)
    ap.add_argument("--rvc-index", type=float, default=0.1)
    ap.add_argument("--rvc-protect", type=float, default=0.4)
    ap.add_argument("--emotion", default="",
                    choices=["", "normal", "sweet", "gentle", "sad", "tsundere", "excited"],
                    help="情绪预设：normal=日常 sweet=撒娇 gentle=温柔深情 sad=难过 tsundere=傲娇 excited=兴奋")
    ap.add_argument("--split", default="cut0", choices=["cut0","cut5"], help="文本切分方式：cut0=不切（短句更稳），cut5=按句切（长文）")
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()

    mode_speed = {"daily": 1.02, "tsundere": 1.12, "warm": 1.0}
    speed = args.speed if args.speed is not None else mode_speed.get(args.mode, 1.02)
    # 情绪预设：语速 / 提亮 / RVC 音高（越低越沉稳深情）
    emo = {
        "": None,
        "normal": (1.02, 2.5, 0),
        "sweet": (1.0, 3.0, 1),
        "gentle": (0.92, 2.0, -2),
        "sad": (0.9, 1.5, -2),
        "tsundere": (1.12, 3.5, 1),
        "excited": (1.2, 3.0, 2),
    }
    # 面板可调参数（params.json），失败就用内置默认
    try:
        _p = json.load(open(r"D:\software\Voice\params.json", encoding="utf-8"))
        _v = _p.get("voice", {})
        for _k, _vv in (_v.get("emotions") or {}).items():
            if _k in emo and isinstance(_vv, dict):
                emo[_k] = (_vv.get("speed", emo[_k][0]), _vv.get("presence", emo[_k][1]), _vv.get("pitch", emo[_k][2]))
        for _k, _sp in (_v.get("mode_speed") or {}).items():
            if _k in mode_speed:
                mode_speed[_k] = _sp
    except Exception:
        pass
    if args.emotion:
        sp, pr, rp = emo[args.emotion]
        if args.speed is None:
            speed = sp
        args.presence = pr
        if args.rvc_pitch == 0:
            args.rvc_pitch = rp

    out = args.out or os.path.join(r"D:\software\Voice\out", "say-%d.wav" % int(time.time()))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if not os.path.exists(args.ref):
        print("ref audio missing: %s" % args.ref, file=sys.stderr)
        return 2

    # ---------- 语言：zh / en / auto（中英混合按段拆开分别合成） ----------
    import re as _re

    def split_lang(text):
        """把文本切成 (语言, 片段) 序列：中文段用 zh，英文/数字段用 en，标点跟上一段。"""
        parts = []
        for m in _re.finditer(r"[A-Za-z0-9][A-Za-z0-9 '’\-.,!?;:]*|[\u4e00-\u9fff]+|[^\u4e00-\u9fffA-Za-z0-9]+", text):
            s = m.group(0)
            if not s.strip():
                if parts:
                    parts[-1] = (parts[-1][0], parts[-1][1] + s)
                continue
            has_cjk = bool(_re.search(r"[\u4e00-\u9fff]", s))
            has_lat = bool(_re.search(r"[A-Za-z]", s))
            lang = "zh" if has_cjk and not has_lat else ("en" if has_lat and not has_cjk else "zh")
            if parts and parts[-1][0] == lang:
                parts[-1] = (lang, parts[-1][1] + s)
            else:
                parts.append((lang, s))
        return [(lg, tx) for lg, tx in parts
                if any(c.isalnum() or "\u4e00" <= c <= "\u9fff" for c in tx)]

    lang = args.lang
    if lang == "auto":
        pieces = split_lang(args.text) or [("zh", args.text)]
    else:
        pieces = [(lang, args.text)]

    def synth_seg(txt, text_lang, path):
        payload = {
            "text": txt,
            "text_lang": text_lang,
            "ref_audio_path": args.ref,
            "prompt_text": args.prompt_text or load_prompt(),
            "prompt_lang": args.prompt_lang,
            "text_split_method": args.split,
            "batch_size": 1,
            "media_type": "wav",
            "streaming_mode": False,
            "speed_factor": speed,
            "temperature": 0.9,
        }
        r = requests.post(API + "/tts", json=payload, timeout=args.timeout)
        if r.status_code != 200:
            raise RuntimeError("TTS HTTP %s: %s" % (r.status_code, r.text[:300]))
        with open(path, "wb") as f:
            f.write(r.content)

    t0 = time.time()
    seg_files = []
    try:
        for i, (lg, tx) in enumerate(pieces):
            p = out + ".seg%d.wav" % i
            synth_seg(tx, lg, p)
            seg_files.append(p)
    except Exception as exc:
        print("TTS failed: %s" % exc, file=sys.stderr)
        for p in seg_files:
            if os.path.exists(p):
                os.remove(p)
        return 3
    raw = out + ".raw.wav"
    if len(seg_files) == 1:
        os.replace(seg_files[0], raw)
    else:
        # 多段拼接，段间留 0.12 秒自然停顿
        cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error"]
        for p in seg_files:
            cmd += ["-i", p]
        n = len(seg_files)
        # 每段先统一成 32k 单声道并在尾部补 0.12 秒静音，再用 concat 拼接
        fixed = []
        for i, p in enumerate(seg_files):
            fp = out + ".fix%d.wav" % i
            subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", p,
                            "-ac", "1", "-ar", "32000",
                            "-af", "apad=pad_len=%d" % int(0.12 * 32000), fp], capture_output=True)
            if os.path.exists(fp):
                fixed.append(fp)
        if fixed:
            lst = out + ".list.txt"
            with open(lst, "w", encoding="utf-8") as f:
                for fp in fixed:
                    f.write("file '%s'\n" % fp.replace("\\", "/"))
            r = subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                                "-f", "concat", "-safe", "0", "-i", lst,
                                "-ac", "1", "-ar", "32000", raw], capture_output=True)
            if r.returncode != 0 or not os.path.exists(raw):
                print("拼接失败，退回第一段: %s" % (r.stderr or b"")[:200], file=sys.stderr)
                os.replace(fixed[0], raw)
            for fp in fixed + [lst]:
                if os.path.exists(fp) and fp != raw:
                    os.remove(fp)
        else:
            os.replace(seg_files[0], raw)
            if os.path.exists(p):
                os.remove(p)
    final = raw
    # 出站后处理：3kHz 提亮（咬字更清楚）+ 峰值归一到 0.9（模型输出普遍偏轻，
    # 听起来"有气无力"）。用 soundfile 直接缩放，确定性好过 loudnorm 单遍。
    if not args.no_loud:
        eq = out + ".eq.wav"
        ok = False
        if os.path.exists(FFMPEG):
            cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", raw,
                   "-af", "highshelf=f=3000:g=%s" % args.presence,
                   "-ac", "1", "-ar", "32000", eq]
            ok = subprocess.run(cmd, capture_output=True).returncode == 0 and os.path.exists(eq)
        src = eq if ok else raw
        try:
            import soundfile as sf
            import numpy as np
            data, sr = sf.read(src)
            peak = float(np.max(np.abs(data))) if data.size else 0.0
            if peak > 0.001:
                data = data * (0.9 / peak)
                sf.write(out, data, sr)
                final = out
        except Exception as e:
            print("post-process failed: %s" % e, file=sys.stderr)
        for tmp in (eq,):
            if os.path.exists(tmp) and tmp != out:
                os.remove(tmp)
    os.replace(final, out) if final != out else None
    if os.path.exists(raw) and raw != out:
        os.remove(raw)
    if args.rvc:
        import json as _json
        import subprocess as _sp
        import urllib.request as _ur

        # 开头垫 0.3 秒静音给 RVC 上下文，转换后再裁掉（治"首字不清"）
        pad_ms = 300
        padded = out.replace(".wav", ".pad.wav")
        _sp.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", out,
                 "-af", "adelay=%d|%d" % (pad_ms, pad_ms), padded], capture_output=True)
        src = padded if os.path.exists(padded) else out
        conv = out.replace(".wav", ".rvc.wav")
        payload = _json.dumps({"input": src, "output": conv, "pitch": args.rvc_pitch,
                               "protect": args.rvc_protect, "index_rate": args.rvc_index, "rms_mix_rate": 0.12,
                               "f0_method": "pm"}).encode("utf-8")
        req = _ur.Request("http://127.0.0.1:9850/rvc", data=payload,
                          headers={"Content-Type": "application/json"})
        def _post():
            return _json.loads(_ur.urlopen(req, timeout=300).read().decode("utf-8"))
        try:
            try:
                resp = _post()
            except Exception:
                # RVC 服务没开：自动拉起来再试一次
                import subprocess as _sp2
                _sp2.Popen([sys.executable, r"D:\software\Voice\cover\rvc_server.py"],
                           cwd=r"D:\software\Voice\cover\rvc_pack\Retrieval-based-Voice-Conversion-WebUI-main",
                           creationflags=0x00000008, stdout=_sp2.DEVNULL, stderr=_sp2.DEVNULL)
                for _ in range(40):
                    time.sleep(2)
                    try:
                        resp = _post()
                        break
                    except Exception:
                        continue
                else:
                    raise
            if resp.get("ok"):
                trimmed = out.replace(".wav", ".trim.wav")
                _sp.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", "0.3",
                         "-i", conv, "-af", "loudnorm=I=-15:TP=-1.5:LRA=9",
                         "-ac", "1", "-ar", "32000", trimmed], capture_output=True)
                os.replace(trimmed if os.path.exists(trimmed) else conv, out)
                for tmp in (padded, conv):
                    if os.path.exists(tmp) and tmp != out:
                        os.remove(tmp)
                print("rvc ok (padded+trimmed)", flush=True)
        except Exception as _e:
            print("rvc failed: %s" % _e, file=sys.stderr)
    print("%s\t%.1fs\t%.1fKB\tspeed=%.2f" % (out, time.time() - t0, os.path.getsize(out) / 1024.0, speed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
