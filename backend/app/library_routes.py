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
               'lapse_count', l.lapse_count
           ) from public.learning_progress l where l.entry_id = e.id
       ) as learning_progress
from public.entries e
where (%s is null or e.kind = %s)
order by e.frequency desc, e.id
limit %s offset %s
"""


@router.get('', response_model=LibraryPage)
def list_entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    kind: Literal['word', 'phrase'] | None = None,
):
    with database_cursor() as cursor:
        cursor.execute(
            'select count(*) as total from public.entries where (%s is null or kind = %s)',
            (kind, kind),
        )
        total = cursor.fetchone()['total']
        cursor.execute(ENTRY_SQL, (kind, kind, page_size, (page - 1) * page_size))
        items = [SavedEntry.model_validate(row) for row in cursor.fetchall()]
    return LibraryPage(items=items, total=total, page=page, page_size=page_size)


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
