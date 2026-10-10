begin;
alter table public.study_sessions drop constraint if exists study_sessions_mode_check;
alter table public.study_sessions add constraint study_sessions_mode_check
    check (mode in ('en_vi', 'listening', 'vi_en', 'cloze'));
commit;
