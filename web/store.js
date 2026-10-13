// 保存済み記事の読み書き。画面側は window.store だけを使う（保存先の違いはここで吸収）。
//   store.mode            "local" | "cloud"
//   store.init()          起動時。cloud でログイン未了なら { needLogin: true } を返す
//   store.list()          保存済みの配列（新しい保存順）
//   store.save(item)      { id, title, link, source, published, comment } を保存（同じidは上書き）
//   store.remove(id)
(function () {
  const cfg = window.NEWS_CONFIG || {};

  // ---------- 手元PC版 ----------
  const local = {
    mode: "local",
    async init() { return {}; },
    async list() {
      const r = await fetch("/api/saved", { cache: "no-store" });
      if (!r.ok) throw new Error("保存データを読めませんでした");
      return (await r.json()).items.sort((a, b) => (b.saved_at || "").localeCompare(a.saved_at || ""));
    },
    async save(item) {
      const now = new Date().toISOString();
      const row = { ...item, saved_at: item.saved_at || now, updated_at: now };
      const r = await fetch("/api/saved/" + encodeURIComponent(item.id), {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(row),
      });
      if (!r.ok) throw new Error("保存に失敗しました");
      return row;
    },
    async remove(id) {
      const r = await fetch("/api/saved/" + encodeURIComponent(id), { method: "DELETE" });
      if (!r.ok) throw new Error("削除に失敗しました");
    },
  };

  // ---------- クラウド版（Supabase）----------
  // テーブル定義は supabase/schema.sql。本人しか読み書きできない（RLS）。
  let sb = null;
  const cloud = {
    mode: "cloud",
    async init() {
      const { createClient } = await import("https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/+esm");
      sb = createClient(cfg.supabaseUrl, cfg.supabaseAnonKey);
      const { data } = await sb.auth.getSession();
      return data.session ? {} : { needLogin: true };
    },
    async sendLoginLink(email) {
      const { error } = await sb.auth.signInWithOtp({
        email, options: { emailRedirectTo: location.origin + location.pathname, shouldCreateUser: false },
      });
      if (error) throw error;
    },
    async logout() { await sb.auth.signOut(); location.reload(); },
    async list() {
      const { data, error } = await sb.from("saved_articles").select("*").order("saved_at", { ascending: false });
      if (error) throw error;
      return data;
    },
    async save(item) {
      const now = new Date().toISOString();
      const { data: { user } } = await sb.auth.getUser();
      const row = { ...item, user_id: user.id, updated_at: now };
      if (!row.saved_at) row.saved_at = now;
      const { error } = await sb.from("saved_articles").upsert(row, { onConflict: "user_id,id" });
      if (error) throw error;
      return row;
    },
    async remove(id) {
      const { error } = await sb.from("saved_articles").delete().eq("id", id);
      if (error) throw error;
    },
  };

  window.store = cfg.supabaseUrl && cfg.supabaseAnonKey ? cloud : local;
})();
