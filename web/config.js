// 保存先の切り替え。空のままなら「手元PC版」（serve.py の local-data/saved.json に保存）。
// クラウド版にするときだけ、SupabaseのProject URLと anon public key を入れる。
// ※ anon key は公開前提のキー（画面に埋め込んでよい）。service_role key は絶対にここへ入れない。
window.NEWS_CONFIG = {
  supabaseUrl: "https://vslpbqmpvuiuqwdilkyj.supabase.co",
  supabaseAnonKey: "sb_publishable_slVgQR5BUXSAI9E03_IteQ_9BIk8Ps7",
};
