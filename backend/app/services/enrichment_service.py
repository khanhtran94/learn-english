"""Enrich one saved entry, preserving meanings even when audio fails."""
import os
from uuid import UUID

from fastapi import HTTPException
from psycopg2.extras import Json
from supabase import create_client

from app.database import database_cursor
from app.services.dictionary_service import DictionaryError

BUCKET = 'pronunciation'
VOICE = 'Kore'
ACCENT = 'en-US'


class EntryRepository:
    def __init__(self, cursor, entry_id):
        self.cursor = cursor
        self.entry_id = str(entry_id)

    def load(self):
        self.cursor.execute('select pg_try_advisory_xact_lock(hashtextextended(%s, 0)) as acquired', ('enrich:' + self.entry_id,))
        if not self.cursor.fetchone()['acquired']:
            raise HTTPException(409, 'Từ/cụm này đang được xử lý. Vui lòng chờ.', headers={'Retry-After': '5'})
        self.cursor.execute('''
            select e.normalized_text,
                   exists(select 1 from public.meanings m where m.entry_id=e.id) as has_meanings,
                   exists(select 1 from public.pronunciations p where p.entry_id=e.id
                          and p.audio_status='ready' and p.audio_path is not null) as has_audio
            from public.entries e where e.id=%s
        ''', (self.entry_id,))
        row = self.cursor.fetchone()
        if row is None:
            raise HTTPException(404, 'Không tìm thấy từ/cụm trong kho.')
        return row

    def lookup_status(self, status):
        self.cursor.execute('update public.entries set lookup_status=%s, lookup_attempted_at=now() where id=%s', (status, self.entry_id))

    def save_meanings(self, result, model):
        # Called only when no meanings exist; never overwrite existing definitions.
        for order, meaning in enumerate(result.meanings, start=1):
            self.cursor.execute('''
                insert into public.meanings(entry_id,part_of_speech,meaning_vi,examples,sort_order,provider,model)
                values (%s,%s,%s,%s,%s,'gemini',%s)
            ''', (self.entry_id, meaning.part_of_speech, meaning.vietnamese,
                  Json([example.model_dump() for example in meaning.examples]), order, model))
        self.cursor.execute('''
            insert into public.pronunciations(entry_id,ipa,accent,voice,provider,model)
            values (%s,%s,%s,%s,'gemini',%s)
            on conflict(entry_id,accent,voice) do update set
                ipa=coalesce(public.pronunciations.ipa, excluded.ipa)
        ''', (self.entry_id, result.ipa, ACCENT, VOICE, model))

    def audio_status(self, status, model, path=None, size=None):
        self.cursor.execute('''
            insert into public.pronunciations
                (entry_id,accent,voice,audio_status,audio_bucket,audio_path,mime_type,size_bytes,provider,model,audio_attempted_at)
            values (%s,%s,%s,%s,%s,%s,%s,%s,'gemini',%s,now())
            on conflict(entry_id,accent,voice) do update set
                audio_status=excluded.audio_status,
                audio_bucket=excluded.audio_bucket,
                audio_path=coalesce(excluded.audio_path, public.pronunciations.audio_path),
                mime_type=coalesce(excluded.mime_type, public.pronunciations.mime_type),
                size_bytes=coalesce(excluded.size_bytes, public.pronunciations.size_bytes),
                model=excluded.model, audio_attempted_at=now()
        ''', (self.entry_id, ACCENT, VOICE, status, BUCKET, path,
              'audio/wav' if path else None, size, model))


def storage_client():
    url = os.getenv('SUPABASE_API_URL', '').strip()
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '').strip()
    if not url.startswith('https://') or not key:
        raise DictionaryError(503, 'Thiếu SUPABASE_API_URL hoặc SUPABASE_SERVICE_ROLE_KEY để upload audio.')
    try:
        return create_client(url, key)
    except Exception as exc:
        raise DictionaryError(503, 'Cấu hình Supabase Storage không hợp lệ.') from exc


def enrich_entry(entry_id: UUID, dictionary):
    failure = None
    result = {'entry_id': str(entry_id), 'status': 'complete', 'meanings_saved': False,
              'audio_saved': False, 'message': None, 'retry_after': 0}
    # One advisory transaction lock per entry; no sleeps or automatic retries here.
    # This also coordinates separate backend workers. Closing releases the lock.
    with database_cursor(readonly=False) as cursor:
        repo = EntryRepository(cursor, entry_id)
        entry = repo.load()
        has_meanings = entry['has_meanings']
        if not has_meanings:
            try:
                definition = dictionary.lookup(entry['normalized_text'])
                if definition.found:
                    repo.save_meanings(definition, dictionary.model)
                    has_meanings = True
                    result['meanings_saved'] = True
                else:
                    repo.lookup_status('not_found')
                    result['status'] = 'not_found'
                    result['message'] = 'Gemini chưa tìm thấy nghĩa cho từ/cụm này.'
            except DictionaryError as exc:
                repo.lookup_status('pending' if exc.status == 429 else 'failed')
                failure = exc
        if has_meanings:
            repo.lookup_status('ready')
            if not entry['has_audio']:
                try:
                    client = storage_client()
                    audio = dictionary.audio(entry['normalized_text'])
                    path = f'entries/{entry_id}/{ACCENT}/{VOICE}.wav'
                    try:
                        client.storage.from_(BUCKET).upload(
                            path, audio,
                            file_options={'content-type': 'audio/wav', 'upsert': 'true'},
                        )
                    except Exception as exc:
                        raise DictionaryError(502, 'Không upload được audio. Kiểm tra bucket pronunciation và quyền Storage.') from exc
                    repo.audio_status('ready', dictionary.audio_model, path, len(audio))
                    result['audio_saved'] = True
                except DictionaryError as exc:
                    repo.audio_status('pending' if exc.status == 429 else 'failed', dictionary.audio_model)
                    result.update(status='partial', message=exc.message, retry_after=exc.retry_after or 0)
    # Meaning failures are surfaced only after the failed/pending state commits.
    if failure:
        raise failure
    return result
