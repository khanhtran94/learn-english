"""Read the personal vocabulary library from Supabase; never call Gemini here."""
import os
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from supabase import create_client
from app.database import database_cursor

load_dotenv(Path(__file__).resolve().parents[1] / '.env', encoding='utf-8-sig')
router = APIRouter(prefix='/entries', tags=['library'])


class SavedMeaning(BaseModel):
    id: UUID
    part_of_speech: str
    meaning_vi: str
    examples: list[dict[str, str]] = Field(default_factory=list)
    sort_order: int


class SavedPronunciation(BaseModel):
    id: UUID
    ipa: str | None = None
    accent: str
    voice: str
    audio_status: str


class SavedProgress(BaseModel):
    status: str
    review_step: int
    interval_days: int
    next_review_at: datetime | None = None
    last_review_at: datetime | None = None
    correct_count: int = 0
    review_count: int
    lapse_count: int


class SavedEntry(BaseModel):
    id: UUID
    normalized_text: str
    kind: Literal['word', 'phrase']
    frequency: int
    lookup_status: str
    first_seen_at: datetime
    last_seen_at: datetime
    meanings: list[SavedMeaning] = Field(default_factory=list)
    pronunciations: list[SavedPronunciation] = Field(default_factory=list)
    learning_progress: SavedProgress | None = None


class LibraryPage(BaseModel):
    items: list[SavedEntry]
    total: int
    page: int
    page_size: int
    with_meanings: int
    without_meanings: int


# Correlated aggregates keep entries visible even when child tables have no rows.
ENTRY_SQL = """
select e.id, e.normalized_text, e.kind, e.frequency, e.lookup_status,
       e.first_seen_at, e.last_seen_at,
       coalesce((
           select jsonb_agg(jsonb_build_object(
               'id', m.id, 'part_of_speech', m.part_of_speech,
               'meaning_vi', m.meaning_vi, 'examples', m.examples,
               'sort_order', m.sort_order
           ) order by m.sort_order)
           from public.meanings m where m.entry_id = e.id
       ), '[]'::jsonb) as meanings,
       coalesce((
           select jsonb_agg(jsonb_build_object(
               'id', p.id, 'ipa', p.ipa, 'accent', p.accent,
               'voice', p.voice, 'audio_status', p.audio_status
           ) order by p.accent, p.voice)
           from public.pronunciations p where p.entry_id = e.id
       ), '[]'::jsonb) as pronunciations,
       (
           select jsonb_build_object(
               'status', l.status, 'review_step', l.review_step,
               'interval_days', l.interval_days, 'next_review_at', l.next_review_at,
               'last_review_at', l.last_review_at, 'review_count', l.review_count,
               'correct_count', l.correct_count, 'lapse_count', l.lapse_count
           ) from public.learning_progress l where l.entry_id = e.id
       ) as learning_progress
from public.entries e
where (%s is null or e.kind = %s)
and exists(select 1 from public.ignored_entries i where i.entry_id=e.id) = %s
and (%s is null or exists(select 1 from public.meanings m where m.entry_id=e.id) = %s)
order by e.frequency desc, e.id
limit %s offset %s
"""


@router.get('', response_model=LibraryPage)
def list_entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    kind: Literal['word', 'phrase'] | None = None,
    ignored: bool = False,
    has_meaning: bool | None = None,
):
    with database_cursor() as cursor:
        cursor.execute(
            '''select count(*) as total,
                count(*) filter(where exists(select 1 from public.meanings m where m.entry_id=e.id)) as with_meanings,
                count(*) filter(where not exists(select 1 from public.meanings m where m.entry_id=e.id)) as without_meanings
                from public.entries e where (%s is null or kind = %s)
                and exists(select 1 from public.ignored_entries i where i.entry_id=e.id) = %s''',
            (kind, kind, ignored),
        )
        counts = cursor.fetchone()
        total = counts['total'] if has_meaning is None else counts['with_meanings' if has_meaning else 'without_meanings']
        cursor.execute(ENTRY_SQL, (kind, kind, ignored, has_meaning, has_meaning, page_size, (page - 1) * page_size))
        items = [SavedEntry.model_validate(row) for row in cursor.fetchall()]
    return LibraryPage(items=items, total=total, page=page, page_size=page_size,
                       with_meanings=counts['with_meanings'], without_meanings=counts['without_meanings'])


@router.get('/pronunciations/{pronunciation_id}/audio')
def saved_audio(pronunciation_id: UUID):
    with database_cursor() as cursor:
        cursor.execute(
            'select audio_bucket, audio_path, audio_status from public.pronunciations where id = %s',
            (str(pronunciation_id),),
        )
        row = cursor.fetchone()
    if not row or row['audio_status'] != 'ready' or not row.get('audio_path'):
        raise HTTPException(404, 'Chưa có audio đã lưu cho phát âm này.')
    # Database credentials cannot sign private Storage URLs; use its HTTPS API.
    url = os.getenv('SUPABASE_API_URL', '').strip()
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '').strip()
    if not url.startswith('https://') or not key:
        raise HTTPException(503, 'Để nghe audio Storage, cấu hình SUPABASE_API_URL (https) và SUPABASE_SERVICE_ROLE_KEY. Đọc kho từ chỉ cần SUPABASE_URL PostgreSQL.')
    try:
        client = create_client(url, key)
        signed = client.storage.from_(row['audio_bucket']).create_signed_url(row['audio_path'], 600)
        return {'url': signed['signedURL'], 'expires_in': 600}
    except Exception as exc:
        raise HTTPException(502, 'Không tải được audio từ Storage. Kiểm tra file và quyền truy cập bucket.') from exc


@router.post('/{entry_id}/ignore')
def ignore_entry(entry_id: UUID):
    with database_cursor(readonly=False) as cursor:
        cursor.execute("select pg_advisory_xact_lock(hashtextextended('library-ignore',0))")
        cursor.execute('select pg_try_advisory_xact_lock(hashtextextended(%s,0)) as acquired',
                       ('enrich:' + str(entry_id),))
        if not cursor.fetchone()['acquired']:
            raise HTTPException(409, 'Mục này đang tra nghĩa/lưu audio. Vui lòng thử lại sau.')
        cursor.execute('select normalized_text,kind from public.entries where id=%s', (str(entry_id),))
        entry = cursor.fetchone()
        if not entry:
            raise HTTPException(404, 'Không tìm thấy từ/cụm.')
        cursor.execute('''insert into public.ignored_entries(entry_id,normalized_text,kind)
            values(%s,%s,%s) on conflict(entry_id) do nothing''',
                       (str(entry_id), entry['normalized_text'], entry['kind']))
        # Retain the full session history, but don't keep serving archived questions.
        cursor.execute("""update public.study_sessions s set status='abandoned',completed_at=now()
            where status='active' and exists(select 1 from public.study_questions q
                where q.session_id=s.id and q.entry_id=%s and q.answered_at is null)""", (str(entry_id),))
    return {'ignored': True, 'entry_id': str(entry_id)}


@router.post('/{entry_id}/restore')
def restore_entry(entry_id: UUID):
    with database_cursor(readonly=False) as cursor:
        cursor.execute("select pg_advisory_xact_lock(hashtextextended('library-ignore',0))")
        cursor.execute('select id from public.entries where id=%s', (str(entry_id),))
        if not cursor.fetchone():
            raise HTTPException(404, 'Không tìm thấy từ/cụm.')
        cursor.execute('delete from public.ignored_entries where entry_id=%s', (str(entry_id),))
    return {'ignored': False, 'entry_id': str(entry_id)}
