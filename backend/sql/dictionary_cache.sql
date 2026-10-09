-- Optional: run in your Supabase SQL editor before enabling the backend cache.
create table if not exists public.dictionary_cache (
    cache_key text primary key,
    entry jsonb not null,
    expires_at timestamptz not null
);
alter table public.dictionary_cache enable row level security;
revoke all on public.dictionary_cache from anon, authenticated;
grant select, insert, update, delete on public.dictionary_cache to service_role;
