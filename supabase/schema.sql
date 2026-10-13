-- クラウド版（第2段階の最終形）用のテーブル。Supabase の SQL Editor に貼って Run する。
-- 本人（ログイン中のユーザー）の行しか読み書きできないようにする（RLS）。

create table if not exists public.saved_articles (
  user_id    uuid not null default auth.uid() references auth.users(id) on delete cascade,
  id         text not null,           -- 記事リンクから作ったID（同じ記事は上書き）
  title      text not null,
  link       text not null,
  source     text,                    -- 媒体名
  published  timestamptz,
  comment    text not null default '',
  saved_at   timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, id)
);

alter table public.saved_articles enable row level security;

create policy "own rows: select" on public.saved_articles
  for select using (auth.uid() = user_id);
create policy "own rows: insert" on public.saved_articles
  for insert with check (auth.uid() = user_id);
create policy "own rows: update" on public.saved_articles
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own rows: delete" on public.saved_articles
  for delete using (auth.uid() = user_id);
