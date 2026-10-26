"""新聞・通信の新着をメールで送る。先に fetch_feeds.py で web/data/feeds.json を作っておく。

必要な環境変数（GitHub の Settings → Secrets に登録する。このフォルダには書かない）:
  GMAIL_ADDRESS       送信に使うGmailアドレス
  GMAIL_APP_PASSWORD  そのGmailのアプリパスワード（16桁）
  MAIL_TO             送り先（省略時は GMAIL_ADDRESS と同じ）

  python send_digest.py --dry-run   送らずに件名と本文だけ表示
"""
import argparse
import json
import os
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path

FEEDS = Path(__file__).parent / "web" / "data" / "feeds.json"
JST = timezone(timedelta(hours=9))
PER_COMPANY = 5

# 送る媒体（表示順）。sources.json の id の先頭が prefix に一致したものを同じ社として扱う
COMPANIES = [
    ("asahi", "朝日新聞"),
    ("mainichi", "毎日新聞"),
    ("yomiuri", "読売新聞"),
    ("sankei", "産経新聞"),
    ("nikkei", "日本経済新聞"),
    ("jiji", "時事通信"),
]


def company_of(source_id):
    for prefix, name in COMPANIES:
        if source_id == prefix or source_id.startswith(prefix + "-"):
            return name
    return None


def norm_link(link):
    """http/https と ?ref=rss の違いだけの重複（朝日の複数系統など）を同じ記事として扱う"""
    link = link.replace("http://", "https://", 1)
    for tail in ("?ref=rss", "&ref=rss"):
        link = link.replace(tail, "")
    return link


def build(feeds, now):
    morning = now.hour < 12
    # 朝は前日夕方のメール以降（約15時間）、夕方は朝のメール以降（約9時間）。少し余裕を持たせる
    since = now - timedelta(hours=16 if morning else 10)

    by_company = {name: {} for _, name in COMPANIES}  # name -> {link: (dt, title)}
    for a in feeds["articles"]:
        name = company_of(a["source"])
        if not name:
            continue
        dt = datetime.fromisoformat(a["published"]).astimezone(JST) if a["published"] else None
        if dt is not None and dt < since:
            continue
        by_company[name].setdefault(norm_link(a["link"]), (dt, a["title"]))

    failed = []
    for s in feeds["status"]:
        name = company_of(s["id"])
        if name and not s["ok"] and name not in failed:
            failed.append(name)

    total = sum(len(v) for v in by_company.values())
    lines = []
    for _, name in COMPANIES:
        items = sorted(by_company[name].items(), key=lambda kv: kv[1][0] or datetime.min.replace(tzinfo=JST), reverse=True)
        if name in failed and not items:
            continue  # 取れなかった社は末尾の注記にまとめる
        if not items:
            lines += [f"■ {name}", "  新着なし", ""]
            continue
        shown = items[:PER_COMPANY]
        head = f"{len(shown)}件" if len(items) <= PER_COMPANY else f"新着{len(items)}件のうち{len(shown)}件"
        lines.append(f"■ {name}（{head}）")
        for link, (dt, title) in shown:
            lines.append(f"・{title}" + (f"  {dt:%H:%M}" if dt else ""))
            lines.append(f"  {link}")
        lines.append("")
    lines.append("※ 取得できなかった媒体: " + ("、".join(failed) if failed else "なし"))

    subject = f"ニュース{'朝刊' if morning else '夕刊'} {now:%m/%d %H:%M}（新着{total}件）"
    return subject, "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    feeds = json.loads(FEEDS.read_text(encoding="utf-8"))
    subject, body = build(feeds, datetime.now(JST))
    if a.dry_run:
        print("件名:", subject, "\n")
        print(body)
        return

    user = os.environ.get("GMAIL_ADDRESS", "").strip()
    pw = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    to = os.environ.get("MAIL_TO", "").strip() or user
    if not (user and pw):
        print("メールの設定（GMAIL_ADDRESS / GMAIL_APP_PASSWORD）が未登録のため送りません。")
        return

    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, user, to
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as s:
        s.login(user, pw)
        s.send_message(msg)
    print("メールを送りました。")


if __name__ == "__main__":
    main()
