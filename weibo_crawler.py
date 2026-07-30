# -*- coding: utf-8 -*-
"""
峰哥亡命天涯（UID 2397417584）微博增量爬虫
- 数据源：m.weibo.cn 移动端接口
- 增量去重：按微博数字 ID 判断，已存档的不再重复记录
- 输出：
    weibo_posts.jsonl   每行一条微博（机器可读，追加式）
    archive.md          按时间倒序的可读存档（每次全量重建）
- Cookie：从环境变量 WEIBO_COOKIE 读取（GitHub Actions Secret）
"""
import html
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

UID = "2397417584"
CONTAINER_ID = "107603" + UID
API_URL = (
    "https://m.weibo.cn/api/container/getIndex?containerid=" + CONTAINER_ID
)

BASE_DIR = Path(__file__).resolve().parent
JSONL_PATH = BASE_DIR / "weibo_posts.jsonl"
ARCHIVE_PATH = BASE_DIR / "archive.md"

MAX_PAGES = 3  # 每次最多翻 3 页，足够覆盖一小时内的发言量


def fetch_page(page: int) -> dict:
    """请求一页微博列表，返回解析后的 JSON。"""
    url = API_URL if page <= 1 else API_URL + "&page=%d" % page
    cookie = os.environ.get("WEIBO_COOKIE", "").strip()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/16.6 Mobile/15E148 Safari/604.1"
        ),
        "Referer": "https://m.weibo.cn/u/" + UID,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/plain, */*",
        "MWeibo-Pwa": "1",
    }
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    return json.loads(body)


_TAG_RE = re.compile(r"<[^>]+>")


def clean_text(raw: str) -> str:
    """把接口返回的 HTML 正文转成纯文本。"""
    text = _TAG_RE.sub("", raw or "")
    return html.unescape(text).strip()


def parse_time(created_at: str) -> str:
    """'Thu Jul 30 17:20:00 +0800 2026' -> '2026-07-30 17:20:00'"""
    try:
        dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return created_at or ""


def mblog_to_record(mblog: dict) -> dict:
    retweeted = mblog.get("retweeted_status")
    record = {
        "id": str(mblog.get("id", "")),
        "bid": mblog.get("bid", ""),
        "created_at": parse_time(mblog.get("created_at", "")),
        "text": clean_text(mblog.get("text", "")),
        "source": clean_text(mblog.get("source", "")),
        "reposts_count": mblog.get("reposts_count", 0),
        "comments_count": mblog.get("comments_count", 0),
        "attitudes_count": mblog.get("attitudes_count", 0),
        "url": "https://m.weibo.cn/detail/" + str(mblog.get("id", "")),
        "is_retweet": bool(retweeted),
    }
    if retweeted:
        user = (retweeted.get("user") or {}).get("screen_name", "")
        record["retweeted_user"] = user
        record["retweeted_text"] = clean_text(retweeted.get("text", ""))
    return record


def load_existing_ids() -> set:
    ids = set()
    if JSONL_PATH.exists():
        with JSONL_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ids.add(str(json.loads(line).get("id", "")))
                except json.JSONDecodeError:
                    continue
    return ids


def collect_new_posts(existing_ids: set) -> list:
    new_posts = []
    for page in range(1, MAX_PAGES + 1):
        try:
            data = fetch_page(page)
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
            print("[警告] 第 %d 页请求失败：%s" % (page, e), file=sys.stderr)
            break

        if data.get("ok") != 1:
            print("[警告] 接口返回异常（可能 Cookie 失效或被风控）：ok=%s msg=%s"
                  % (data.get("ok"), data.get("msg")), file=sys.stderr)
            break

        cards = ((data.get("data") or {}).get("cards")) or []
        page_new = 0
        for card in cards:
            mblog = card.get("mblog")
            if not mblog:
                continue
            mid = str(mblog.get("id", ""))
            if not mid or mid in existing_ids:
                continue
            existing_ids.add(mid)
            new_posts.append(mblog_to_record(mblog))
            page_new += 1

        # 一整页都是已存档的旧微博，说明增量部分已抓完
        if page_new == 0:
            break
        time.sleep(2)  # 翻页间隔，降低被风控概率

    return new_posts


def rebuild_archive():
    """用 JSONL 全量重建可读的 archive.md（时间倒序）。"""
    posts = []
    if JSONL_PATH.exists():
        with JSONL_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        posts.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    posts.sort(key=lambda p: p.get("created_at", ""), reverse=True)

    lines = [
        "# 峰哥亡命天涯 微博存档",
        "",
        "> 共 %d 条，按发布时间倒序。本文件由脚本自动生成，请勿手工编辑。" % len(posts),
        "",
    ]
    for p in posts:
        lines.append("## %s" % p.get("created_at", ""))
        lines.append("")
        lines.append(p.get("text", ""))
        if p.get("is_retweet"):
            lines.append("")
            lines.append("> 转发自 @%s：%s"
                         % (p.get("retweeted_user", ""), p.get("retweeted_text", "")))
        lines.append("")
        lines.append("转 %d · 评 %d · 赞 %d · [原文](%s)"
                     % (p.get("reposts_count", 0), p.get("comments_count", 0),
                        p.get("attitudes_count", 0), p.get("url", "")))
        lines.append("")
    ARCHIVE_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    existing_ids = load_existing_ids()
    print("已存档 %d 条" % len(existing_ids))

    new_posts = collect_new_posts(existing_ids)
    if not new_posts:
        print("没有新微博。")
        return

    # 按发布时间正序追加
    new_posts.sort(key=lambda p: p.get("created_at", ""))
    with JSONL_PATH.open("a", encoding="utf-8") as f:
        for p in new_posts:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    rebuild_archive()
    print("新增 %d 条，总计 %d 条。" % (len(new_posts), len(existing_ids)))


if __name__ == "__main__":
    main()
