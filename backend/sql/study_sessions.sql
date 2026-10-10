begin;
alter table public.meanings add column if not exists short_answers text[] not null default '{}';
alter table public.learning_progress add column if not exists correct_count integer not null default 0 check (correct_count >= 0);

create table if not exists public.study_sessions (
    id uuid primary key default gen_random_uuid(),
    mode text not null check (mode in ('en_vi', 'listening', 'vi_en', 'cloze')),
    scope text not null check (scope in ('due_new', 'learned')),
    status text not null default 'active' check (status in ('active','completed','abandoned')),
    created_at timestamptz not null default now(),
    completed_at timestamptz
);
create table if not exists public.study_questions (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references public.study_sessions(id) on delete cascade,
    entry_id uuid not null references public.entries(id) on delete cascade,
    position integer not null,
    is_retry boolean not null default false,
    payload jsonb not null,
    submitted_answer text,
    correct boolean,
    feedback jsonb,
    answered_at timestamptz,
    unique(session_id, position)
);
create index if not exists study_questions_session_idx on public.study_questions(session_id, position);
create index if not exists study_questions_entry_idx on public.study_questions(entry_id);
create index if not exists study_sessions_active_idx on public.study_sessions(created_at desc) where status='active';
alter table public.study_sessions enable row level security;
alter table public.study_questions enable row level security;
revoke all on public.study_sessions, public.study_questions from public, anon, authenticated;
grant select, insert, update, delete on public.study_sessions, public.study_questions to service_role;
commit;
