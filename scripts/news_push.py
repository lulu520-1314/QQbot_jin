#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""每晚 19:00 给小鲸派送新闻：固定两条消息，多领域混合。

第一条：【新闻派送~】
第二条：5~8 条新闻，每条「序号. [领域] 标题 —— 一句人话说明」下一行给链接

做法：从中新网各频道 RSS + IT之家 + 界面新闻抓当天新闻，
再按标题关键词归类到「政治 / 国际 / 军事 / 科技 / 娱乐 / 体育 / 社会」，
每个领域挑一条，保证领域够杂，不会整条消息全是科技或全是娱乐。

直接走 NapCat OneBot HTTP（默认 127.0.0.1:13200），不依赖 DSH 是否开着。

用法：#在终端中运行先写D:\software\Voice\py310\python.exe
    python news_push.py            # 正常派送（群 + 私聊白名单）
    python news_push.py --dry      # 只打印不发送
    python news_push.py --to-me    # 只发给管理员私聊（试跑用）
"""
import argparse
import datetime
import html
import json
import random
import re
import sys
import urllib.request

CONFIG = r"D:\software\QQBot\news_config.json"


def load_config():
    """读 news_config.json；不存在就用默认值。改这个文件即可开关/调条数，不用动计划任务。"""
    default = {"enabled": True, "count": 6}
    try:
        with open(CONFIG, encoding="utf-8-sig") as f:
            data = json.load(f)
        if isinstance(data, dict):
            default.update({k: v for k, v in data.items() if k in ("enabled", "count")})
    except FileNotFoundError:
        pass
    except Exception as e:
        print("配置读取失败，用默认值: %s" % e, file=sys.stderr)
    return default


API = "http://127.0.0.1:13200"
GROUPS = ["994166352", "639205924"]                                 # 群号
PRIVATE = ["1768174141", "1853057875", "3117642787", "3760677030"]  # 私聊 QQ 号
COUNT = 7              # 派送条数（5~8）
MIN_CATEGORIES = 5     # 至少覆盖几个领域
HEADER = "【新闻派送~】"

FEEDS = [
    "https://www.chinanews.com.cn/rss/scroll-news.xml",
    "https://www.chinanews.com.cn/rss/china.xml",
    "https://www.chinanews.com.cn/rss/world.xml",
    "https://www.chinanews.com.cn/rss/society.xml",
    "https://www.chinanews.com.cn/rss/sports.xml",
    "https://www.chinanews.com.cn/rss/culture.xml",
    "https://www.ithome.com/rss/",
    "https://a.jiemian.com/index.php?m=article&a=rss",
]

# 归类关键词（命中越靠前的领域优先）
CATEGORY_RULES = [
    ("军事", r"军演|军舰|航母|导弹|战机|部队|国防|士兵|军官|空军|陆军|海军|火箭军|阅兵|演习|武器|弹药|雷达|驱逐舰|护卫舰|军事"),
    ("娱乐", r"电影|票房|剧集|电视剧|综艺|明星|演员|歌手|演唱会|恋情|离婚|结婚|导演|影帝|影后|节目|选秀|网红|塌房|粉丝"),
    ("体育", r"球|赛季|联赛|奥运|冠军|夺冠|比分|运动员|教练|球队|比赛|世锦赛|世界杯|亚运会|CBA|NBA|国足|足球|篮球|乒乓球|羽毛球"),
    ("科技", r"AI|人工智能|芯片|手机|苹果|华为|小米|模型|机器人|航天|卫星|火箭|技术|算法|算力|数据中心|大模型|开源|发布|数码|电脑|显卡|操作系统"),
    ("政治", r"主席|总理|总书记|人大|政协|会议|国务院|政策|法规|条例|政府|外交部|部长|省委|市委|通知|部署|调研|座谈"),
    ("国际", r"美国|俄罗斯|乌克兰|以色列|伊朗|欧盟|联合国|北约|日本|韩国|朝鲜|印度|英国|法国|德国|外交|峰会|停火|冲突|大使"),
]

# 描述里的电头/时间前缀
DESC_PREFIX = re.compile(
    r"^(人民网[^。]{0,20}电|据[^，。]{2,12}(报道|消息)|新华社[^。]{0,20}电|"
    r"中新网[^。]{0,20}电|中新社[^。]{0,20}电|本报[^。]{0,20}电|【?原标题[:：]?】?)\s*"
)
NOISE = re.compile(r"(图集|高清图|视频|直播|专题|海报|组图|滚动|图/文|图片)$")
LINK_DATE = re.compile(r"/(20\d{2})[/-]?(\d{2})[-/]?(\d{2})?/")


def clean_text(raw):
    s = html.unescape(re.sub(r"<[^>]+>", "", html.unescape(raw or "")))
    return re.sub(r"\s+", " ", s).strip()


def classify(title):
    for name, pattern in CATEGORY_RULES:
        if re.search(pattern, title, re.I):
            return name
    return "社会"


def link_is_fresh(link, days=3):
    m = LINK_DATE.search(link)
    if not m:
        return True
    today = datetime.date.today()
    try:
        y = int(m.group(1))
        mo = int(m.group(2) or 1)
        d = int(m.group(3) or 1)
        return (today - datetime.date(y, mo, d)).days <= days
    except Exception:
        return True


def fetch_feed(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    except Exception as e:
        print("fetch failed: %s (%s)" % (url, e), file=sys.stderr)
        return []
    out = []
    for raw in re.findall(r"<item>(.*?)</item>", data, re.S):
        title = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", raw, re.S)
        link = re.search(r"<link>(.*?)</link>", raw, re.S)
        desc = re.search(r"<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>", raw, re.S)
        if not title or not link:
            continue
        t = clean_text(title.group(1))
        l = link.group(1).strip()
        d = clean_text(desc.group(1)) if desc else ""
        if not t or not l or len(t) < 8 or NOISE.search(t):
            continue
        if not link_is_fresh(l):
            continue
        if len(t) > 40:
            t = t[:38] + "…"
        d = DESC_PREFIX.sub("", d)
        if len(d) > 44:
            d = d[:42] + "…"
        if d and d.startswith(t[:10]):
            d = ""
        out.append({"title": t, "link": l, "desc": d, "cat": classify(t)})
    return out


def fetch_items(want=None):
    limit = int(want or limit)
    pool = []
    seen_links = set()
    for url in FEEDS:
        for it in fetch_feed(url):
            if it["link"] in seen_links:
                continue
            seen_links.add(it["link"])
            pool.append(it)

    by_cat = {}
    for it in pool:
        by_cat.setdefault(it["cat"], []).append(it)
    for items in by_cat.values():
        random.shuffle(items)

    picked = []
    cats = list(by_cat.keys())
    random.shuffle(cats)
    for cat in cats:                     # 每个领域先各拿一条
        if len(picked) >= limit:
            break
        picked.append(by_cat[cat].pop())
    for cat in cats:                     # 不够就补
        while len(picked) < limit and by_cat.get(cat):
            picked.append(by_cat[cat].pop())
    random.shuffle(picked)
    picked = picked[:limit]
    if len({p["cat"] for p in picked}) < MIN_CATEGORIES:
        print("警告：领域只有 %d 个" % len({p["cat"] for p in picked}), file=sys.stderr)
    return picked


def build_messages(items):
    if not items:
        return None
    lines = []
    for i, it in enumerate(items, 1):
        head = "%d. [%s] %s" % (i, it["cat"], it["title"])
        if it["desc"]:
            head += " —— " + it["desc"]
        lines.append(head + "\n" + it["link"])
    return [HEADER, "\n\n".join(lines)]


def call(action, params):
    req = urllib.request.Request(
        API + "/" + action,
        data=json.dumps(params, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


def send(msgs, dry=False, to_me=False):
    groups = [] if to_me else GROUPS
    privates = [PRIVATE[0]] if to_me else PRIVATE
    for m in msgs:
        if dry:
            print("-----")
            print(m)
            continue
        for g in groups:
            try:
                call("send_group_msg", {"group_id": int(g), "message": [{"type": "text", "data": {"text": m}}]})
            except Exception as e:
                print("send group %s failed: %s" % (g, e), file=sys.stderr)
        for u in privates:
            try:
                call("send_private_msg", {"user_id": int(u), "message": [{"type": "text", "data": {"text": m}}]})
            except Exception as e:
                print("send private %s failed: %s" % (u, e), file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--to-me", dest="to_me", action="store_true")
    args = ap.parse_args()
    cfg = load_config()
    if cfg.get("enabled", True) is False and not args.to_me and not args.dry:
        print("新闻派送已在 news_config.json 里关闭（enabled=false），本次跳过", file=sys.stderr)
        return 0
    items = fetch_items(cfg.get("count", COUNT))
    msgs = build_messages(items)
    if msgs is None:
        print("没抓到新闻，今晚不派送", file=sys.stderr)
        return 1
    send(msgs, dry=args.dry, to_me=args.to_me)
    cats = sorted({i["cat"] for i in items})
    print("派送完成：%d 条新闻，领域：%s" % (len(items), "、".join(cats)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
