"""各社のRSSを巡回して web/data/feeds.json を作る。標準ライブラリのみ。

使い方: python fetch_feeds.py
保存するのは タイトル・リンク・媒体・日時 だけ（記事本文は保存しない）。
"""
import hashlib
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "web" / "data" / "feeds.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"
PER_SOURCE_LIMIT = 40
JST = timezone(timedelta(hours=9))


def local(tag):
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def child_text(el, name):
    for c in el:
        if local(c.tag) == name and (c.text or "").strip():
            return c.text.strip()
    return ""


def parse_date(s):
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:  # 時刻帯なしは日本の媒体なので日本時間として扱う
        d = d.replace(tzinfo=JST)
    return d.astimezone(timezone.utc)


def parse_feed(data):
    root = ET.fromstring(data)
    items = []
    for el in root.iter():
        kind = local(el.tag)
        if kind not in ("item", "entry"):
            continue
        title = re.sub(r"\s+", " ", child_text(el, "title")).strip()
        link = child_text(el, "link")
        if not link:  # Atom は href 属性
            for c in el:
                if local(c.tag) == "link" and c.get("href"):
                    link = c.get("href")
                    break
        date = parse_date(
            child_text(el, "pubDate")
            or child_text(el, "date")
            or child_text(el, "published")
            or child_text(el, "updated")
        )
        if title and link:
            items.append((title, link, date))
    return items


def fetch(src):
    req = urllib.request.Request(src["url"], headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
        items = parse_feed(data)[:PER_SOURCE_LIMIT]
        if not items:
            return src, [], "記事が読み取れませんでした"
        return src, items, None
    except Exception as e:  # 1社の失敗で全体を止めない
        return src, [], f"{type(e).__name__}: {e}"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    cfg = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(fetch, cfg["sources"]))

    articles, status = [], []
    for src, items, err in results:
        status.append({"id": src["id"], "ok": err is None, "count": len(items), "error": err})
        for title, link, date in items:
            articles.append({
                "id": hashlib.sha1(link.encode()).hexdigest()[:12],
                "source": src["id"],
                "title": title,
                "link": link,
                "published": date.isoformat() if date else None,
            })

    articles.sort(key=lambda a: a["published"] or "", reverse=True)
    out = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "groups": cfg["groups"],
        "sources": [{k: s[k] for k in ("id", "name", "group")} | {"unofficial": s.get("unofficial", False)} for s in cfg["sources"]],
        "status": status,
        "articles": articles,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    ok = sum(s["ok"] for s in status)
    print(f"{ok}/{len(status)} 媒体 成功 / 記事 {len(articles)} 件")
    for s in status:
        if not s["ok"]:
            print(f"  失敗: {s['id']} — {s['error']}", file=sys.stderr)


if __name__ == "__main__":
    main()
