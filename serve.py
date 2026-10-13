"""手元PC用の簡易サーバー。web/ を配信し、POST /api/refresh で最新を取得する。

使い方: python serve.py   → http://localhost:8765
（クラウド版では、この /api/refresh 相当をサーバー側の機能に置き換える）
"""
import functools
import json
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
PORT = 8765
lock = threading.Lock()


SAVED = ROOT / "local-data" / "saved.json"  # 手元PC試用版の保存先（クラウド版ではSupabaseに置き換え）


def read_saved():
    try:
        return json.loads(SAVED.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def write_saved(d):
    SAVED.parent.mkdir(exist_ok=True)
    tmp = SAVED.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(SAVED)


class Handler(SimpleHTTPRequestHandler):
    def reply_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/saved":
            with lock:
                self.reply_json({"items": list(read_saved().values())})
            return
        super().do_GET()

    def do_PUT(self):
        if not self.path.startswith("/api/saved/"):
            self.send_error(404)
            return
        item_id = self.path.rsplit("/", 1)[-1]
        item = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        with lock:
            d = read_saved()
            item["id"] = item_id
            d[item_id] = item
            write_saved(d)
        self.reply_json({"ok": True})

    def do_DELETE(self):
        if not self.path.startswith("/api/saved/"):
            self.send_error(404)
            return
        item_id = self.path.rsplit("/", 1)[-1]
        with lock:
            d = read_saved()
            d.pop(item_id, None)
            write_saved(d)
        self.reply_json({"ok": True})

    def do_POST(self):
        if self.path != "/api/refresh":
            self.send_error(404)
            return
        with lock:
            r = subprocess.run([sys.executable, str(ROOT / "fetch_feeds.py")],
                               capture_output=True, text=True, encoding="utf-8")
        body = (r.stdout + r.stderr).encode("utf-8")
        self.send_response(200 if r.returncode == 0 else 500)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    handler = functools.partial(Handler, directory=str(ROOT / "web"))
    print(f"http://localhost:{PORT} で起動しました（止めるには Ctrl+C）")
    ThreadingHTTPServer(("127.0.0.1", PORT), handler).serve_forever()
