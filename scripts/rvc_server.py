#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""RVC 常驻转换服务（CPU）：模型只加载一次，之后每句 15~25 秒。

启动： D:\\software\\Voice\\py310\\python.exe D:\\software\\Voice\\cover\\rvc_server.py
接口： POST http://127.0.0.1:9850/rvc
      {"input": "...wav", "output": "...wav", "pitch": 0, "protect": 0.5, "index_rate": 0.3}
      {"text": "..."} 之外的字段都可省略。
"""
import json
import os
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO = r"D:\software\Voice\cover\rvc_pack\Retrieval-based-Voice-Conversion-WebUI-main"
_MODEL_FILE = r"D:\software\Voice\rvc_model.txt"
if os.environ.get("RVC_MODEL"):
    MODEL = os.environ["RVC_MODEL"]
elif os.path.exists(_MODEL_FILE):
    MODEL = open(_MODEL_FILE, encoding="utf-8").read().strip() or "yujie.pth"
else:
    MODEL = "yujie.pth"
_IDX2 = os.path.join(REPO, "assets", "weights", MODEL.replace(".pth", ".index"))
INDEX = _IDX2 if os.path.exists(_IDX2) else ""
PORT = 9850

os.chdir(REPO)
sys.argv = ["rvc"]
sys.path.insert(0, REPO)
os.environ["RVC_CUDA_GRAPH"] = "0"
os.environ["weight_root"] = os.path.join(REPO, "assets", "weights")
os.environ["rmvpe_root"] = os.path.join(REPO, "assets", "rmvpe")
os.environ["index_root"] = os.path.join(REPO, "logs", "xiaojing")
os.environ["PATH"] = r"D:\software\Voice\ffmpeg\package;" + os.environ.get("PATH", "")

_lock = threading.Lock()
_vc = None



def _model_gain(model_name):
    """按模型配置音量增益（params.json -> modelGain）。"""
    try:
        d = json.load(open(os.path.join(os.path.dirname(__file__), "..", "..", "params.json"), encoding="utf-8"))
    except Exception:
        try:
            d = json.load(open(r"D:\software\Voice\params.json", encoding="utf-8"))
        except Exception:
            d = {}
    g = (d.get("modelGain") or {}).get(model_name)
    try:
        return float(g) if g else 1.0
    except Exception:
        return 1.0


_VC_CACHE = {}


def get_vc_for(model_name):
    """按模型名加载/缓存 VC 实例（试听多音色用，切换约 20~40 秒/次）。"""
    if model_name in _VC_CACHE:
        return _VC_CACHE[model_name]
    from configs.config import Config
    from infer.vc.modules import VC
    import infer.vc.utils as _vcu
    import infer.vc.modules as _vcm
    _vcu.get_index_path_from_model = lambda *a, **k: ""
    _vcm.get_index_path_from_model = _vcu.get_index_path_from_model
    cfg = Config()
    cfg.rvc_weights = os.path.join(REPO, "assets", "weights")
    cfg.python_cmd = sys.executable
    vc = VC(cfg)
    vc.get_vc(model_name)
    _VC_CACHE[model_name] = vc
    return vc


def get_vc():
    global _vc
    if _vc is None:
        from configs.config import Config
        from infer.vc.modules import VC

        # monkeypatch: 跳过自动索引解析（我们显式传 index）
        import infer.vc.utils as _vcu
        import infer.vc.modules as _vcm
        _vcu.get_index_path_from_model = lambda *a, **k: ""
        _vcm.get_index_path_from_model = _vcu.get_index_path_from_model
        cfg = Config()
        cfg.rvc_weights = os.path.join(REPO, 'assets', 'weights')
        cfg.python_cmd = sys.executable
        vc = VC(cfg)
        vc.get_vc(MODEL)
        _vc = vc
    return _vc


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send(200, {"ok": True, "service": "rvc", "port": PORT})

    def do_POST(self):
        if self.path != "/rvc":
            self._send(404, {"ok": False, "error": "not found"})
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
            inp = req.get("input", "")
            out = req.get("output", "")
            if not inp or not out or not os.path.exists(inp):
                self._send(400, {"ok": False, "error": "input missing"})
                return
            vc = get_vc_for(req.get("model") or MODEL) if req.get("model") else get_vc()
            with _lock:
                status, result = vc.vc_single(
                    0,
                    inp,
                    int(req.get("pitch", 0)),
                    req.get("f0_method", "rmvpe"),
                    INDEX if req.get("use_index", True) else "",
                    float(req.get("index_rate", 0.3)),
                    int(req.get("resample_sr", 0)),
                    float(req.get("rms_mix_rate", 0.15)),
                    float(req.get("protect", 0.5)),
                )
            # vc_single 成功时返回 (status, (sr, audio_array))；不同版本文案不一，看类型
            if isinstance(result, (tuple, list)) and len(result) == 2 and not isinstance(result[0], str):
                import soundfile as sf
                import numpy as _np
                sr_out, audio = result
                used_model = req.get("model") or MODEL
                g = _model_gain(used_model)
                if g != 1.0:
                    audio = _np.asarray(audio, dtype=_np.float32) * g
                    peak = float(_np.max(_np.abs(audio))) if audio.size else 0.0
                    if peak > 0.95:      # 等比缩放，绝不削波（削波会爆音）
                        audio = audio * (0.95 / peak)
                sf.write(out, audio, int(sr_out))
                self._send(200, {"ok": True, "output": out})
                return
            if status in ("Success", "成功"):
                self._send(200, {"ok": True, "output": str(result)})
                return
            self._send(500, {"ok": False, "error": str(result)[:300]})
        except Exception as exc:
            traceback.print_exc()
            self._send(500, {"ok": False, "error": str(exc)})


def main():
    print("loading RVC model %s ..." % MODEL, flush=True)
    get_vc()
    print("RVC ready on http://127.0.0.1:%d" % PORT, flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
