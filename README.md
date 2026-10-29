# ニュース収集アプリ（個人用）

各社のRSSを巡回して新着を一覧表示し、気になった記事をコメント付きで保存する。
`content/ニュースノート/`（ネタ帳）とは別物。

- 情報源の一覧: `sources.json`（媒体の追加・削除はここだけ）
- 取得: `python fetch_feeds.py` → `web/data/feeds.json`
- 手元で見る: `start.bat` をダブルクリック → http://localhost:8765
- 保存するのはタイトル・リンク・媒体・日時・自分のコメントのみ（記事本文は保存しない）
- 読売・産経・日経は外部サイト（wor.jp）経由＝非公式。止まることがある

## 公開先（スマホ・PC共通）
- 画面: https://nori-taka.github.io/news-app/ （GitHub Pages）
- リポジトリ: https://github.com/nori-taka/news-app （公開。コードと媒体一覧のみ。保存記事・コメントは含まれない）
- 自動巡回: `.github/workflows/deploy.yml` が30分ごとに各社を巡回して画面ごと公開（手動実行も可）
- 更新の反映: `git push`（この `projects/news-app/` フォルダが独立したgitリポジトリ）。pushすると自動で再公開される
- ログインのリダイレクト先: Supabase の Authentication → URL Configuration に `https://nori-taka.github.io/news-app/**` を登録済みであること

## 保存先（`web/config.js` で切り替え）
| モード | 条件 | 保存先 |
|---|---|---|
| 手元PC版（今） | `config.js` が空 | `local-data/saved.json`（このPCだけ。スマホとは共有されない） |
| クラウド版 | Supabaseの URL と anon key を入れる | Supabase（ログイン必須・本人の行だけ読み書き可。`supabase/schema.sql`） |

## 段階
1. ✅ 一覧表示（スマホ幅対応・絞り込み・更新ボタン）
2. 🔶 ピックアップ＋コメント保存・保存済みタブ・検索
   - ✅ 手元PC版（動作確認済み）
   - ✅ クラウド版（2026-10-13 動作確認: Supabaseにログイン→保存まで本人が確認。PCの localhost:8765 から）。Supabaseの地域はSingapore。ログインはメールのリンク（`hoshiub@gmail.com`）
   - ✅ スマホでログイン・保存・PCとの共有を本人が確認（2026-10-13）
3. 🔶 スマホからの閲覧と30分ごとの自動巡回は完了。✅ 朝夕のGmail送信も稼働（2026-10-26 Secrets登録・手動実行でメール着信を本人が確認）

## 朝夕のニュースメール（`send_digest.py`・`.github/workflows/digest.yml`）
- 朝7時・昼12時・夕18時ごろ（日本時間。GitHub の定時実行は30〜45分遅れるので、約40分前の 6:20／11:20／17:20 に起動。2026-10-29 に朝夕2回から変更）に、新聞・通信（朝日・毎日・読売・産経・日経・時事）の新着を媒体ごと5本まで（見出し＋リンク）送る。AIは使わず無料
- 対象は「前回の成功した実行以降」の記事（最大36時間）。定時実行が飛ばされても、次のメールに取りこぼし分が載る。前回が分からないときだけ、朝15・昼7・夕8時間の固定の幅（時刻で朝刊・昼刊・夕刊を判定）。朝日は3系統をまとめて重複を除く
- 取得できなかった媒体はメール末尾に出る。止まっていても他社は送る
- 送り先・送信元は GitHub の Secrets: `GMAIL_ADDRESS`／`GMAIL_APP_PASSWORD`／`MAIL_TO`（未登録の間は送らずに終わる）
- 確認: `python fetch_feeds.py` → `python send_digest.py --dry-run`。手動で送る: Actions →「朝夕のニュースメール」→ Run workflow
- 次の候補: メールだけに冒頭文を足す（各社の規約・robots.txt を確認してから）。アプリの公開データには他社の冒頭文を載せない

## クラウド化に必要なもの（次回、一緒に進める）
1. Supabase の無料アカウント → プロジェクト作成 → `supabase/schema.sql` を実行 → ログイン用メールの設定
2. GitHub の無料アカウント → このアプリ用のリポジトリ（スマホ配信は GitHub Pages）
3. Gmail の「アプリパスワード」（第3段階。**ノリさんが設定画面に直接入力。チャットには貼らない**）

## 秘密情報
- Gmailのアプリパスワード、Supabaseの service_role key は、このフォルダに置かない
- `web/config.js` に入れてよいのは anon key（公開前提のキー）だけ
- `local-data/` は個人のコメントが入るので、リポジトリには含めない（`.gitignore`）
