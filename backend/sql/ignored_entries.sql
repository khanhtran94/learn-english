begin;
-- Keep the original entry and its children intact; this table defines archive membership.
create table if not exists public.ignored_entries (
    entry_id uuid primary key references public.entries(id),
    normalized_text text not null,
    kind text not null check (kind in ('word', 'phrase')),
    ignored_at timestamptz not null default now(),
    unique(normalized_text, kind)
);
alter table public.ignored_entries enable row level security;
revoke all on public.ignored_entries from public, anon, authenticated;
grant select, insert, update, delete on public.ignored_entries to service_role;
commit;
