"""Persistent personal study sessions. Answers and schedules are server-authoritative."""
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from psycopg2.extras import Json
from pydantic import BaseModel, Field, field_validator

from app.database import database_cursor
from app.services.study_rules import build_question, grade, review_update

router = APIRouter(prefix='/study', tags=['study'])


class StartSession(BaseModel):
    mode: Literal['en_vi', 'listening', 'vi_en', 'cloze']
    scope: Literal['due_new', 'learned'] = 'due_new'
    size: int = Field(default=10, ge=1, le=30)


class Answer(BaseModel):
    answer: str = Field(min_length=1, max_length=200)

    @field_validator('answer')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('Vui lòng nhập đáp án.')
        return value.strip()


def session_view(cursor, session_id):
    cursor.execute('select * from public.study_sessions where id=%s', (str(session_id),))
    session = cursor.fetchone()
    if session is None:
        raise HTTPException(404, 'Không tìm thấy phiên học.')
    cursor.execute('''select count(*) as total, count(answered_at) as answered,
        count(*) filter(where correct=true) as correct,
        count(*) filter(where correct=false) as incorrect,
        count(*) filter(where is_retry=false) as words
        from public.study_questions where session_id=%s''', (str(session_id),))
    summary = dict(cursor.fetchone())
    question = None
    if session['status'] == 'active':
        cursor.execute('select id,position,is_retry,payload from public.study_questions where session_id=%s and answered_at is null order by position limit 1', (str(session_id),))
        row = cursor.fetchone()
        if row:
            payload = row['payload']
            question = {'id': str(row['id']), 'is_retry': row['is_retry'], 'mode': payload['mode'],
                        'prompt': payload['prompt'], 'options': payload['options'],
                        'audio_id': payload['audio_id'] if payload['mode'] == 'listening' else None}
    return {'id': str(session['id']), 'mode': session['mode'], 'scope': session['scope'],
            'status': session['status'], 'summary': summary, 'question': question}


@router.get('/sessions/current')
def current_session():
    with database_cursor() as cursor:
        cursor.execute("select id from public.study_sessions where status='active' order by created_at desc limit 1")
        row = cursor.fetchone()
        return session_view(cursor, row['id']) if row else None


@router.get('/sessions/{session_id}')
def get_session(session_id: UUID):
    with database_cursor() as cursor:
        return session_view(cursor, session_id)


@router.post('/sessions')
def start_session(request: StartSession):
    now = datetime.now(timezone.utc)
    with database_cursor(readonly=False) as cursor:
        cursor.execute("select pg_advisory_xact_lock(hashtextextended('personal-study-session',0))")
        cursor.execute("select id from public.study_sessions where status='active' limit 1")
        if cursor.fetchone():
            raise HTTPException(409, 'Bạn đang có phiên học chưa xong. Tiếp tục hoặc kết thúc phiên trước.')
        cursor.execute('''
            select e.id,e.normalized_text,e.frequency,
                coalesce((select jsonb_agg(jsonb_build_object('meaning_vi',m.meaning_vi,
                    'part_of_speech',m.part_of_speech,'examples',m.examples,'short_answers',m.short_answers)
                    order by m.sort_order) from public.meanings m where m.entry_id=e.id),'[]'::jsonb) as meanings,
                (select p.id from public.pronunciations p where p.entry_id=e.id and p.audio_status='ready'
                    and p.audio_path is not null order by p.id limit 1) as audio_id,
                (select p.ipa from public.pronunciations p where p.entry_id=e.id and p.ipa is not null limit 1) as ipa,
                coalesce(l.status,'new') as learning_status,l.next_review_at
            from public.entries e left join public.learning_progress l on l.entry_id=e.id
            where exists(select 1 from public.meanings m where m.entry_id=e.id)
        ''')
        catalog = [dict(row) for row in cursor.fetchall()]
        for entry in catalog:
            entry['id'] = str(entry['id'])
            entry['audio_id'] = str(entry['audio_id']) if entry['audio_id'] else None
        def is_due(entry):
            return entry['learning_status'] != 'new' and (entry['next_review_at'] is None or entry['next_review_at'] <= now)
        candidates = [entry for entry in catalog if
                      (request.scope == 'learned' and entry['learning_status'] != 'new') or
                      (request.scope == 'due_new' and (entry['learning_status'] == 'new' or is_due(entry)))]
        candidates.sort(key=lambda entry: (0 if is_due(entry) else 1, -entry['frequency'], entry['id']))
        questions = []
        for entry in candidates:
            payload = build_question(entry, catalog, request.mode)
            if payload:
                questions.append((entry['id'], payload))
            if len(questions) >= request.size:
                break
        if not questions and request.mode == 'cloze':
            raise HTTPException(422, 'Chưa có thẻ phù hợp để điền từ. Cần câu ví dụ tiếng Anh chứa nguyên từ/cụm cần học; hãy thử ôn từ đã học nếu chưa có thẻ đến hạn.')
        if not questions:
            raise HTTPException(422, 'Chưa có thẻ phù hợp: cần nghĩa ngắn; bài nghe cần audio; trắc nghiệm cần ít nhất một nghĩa khác làm đáp án nhiễu. Các thẻ đã học có thể chưa đến hạn.')
        cursor.execute('insert into public.study_sessions(mode,scope) values(%s,%s) returning id', (request.mode, request.scope))
        session_id = cursor.fetchone()['id']
        for position, (entry_id, payload) in enumerate(questions):
            cursor.execute('insert into public.study_questions(session_id,entry_id,position,payload) values(%s,%s,%s,%s)', (str(session_id), entry_id, position, Json(payload)))
        return session_view(cursor, session_id)


@router.post('/sessions/{session_id}/questions/{question_id}/answer')
def submit_answer(session_id: UUID, question_id: UUID, request: Answer):
    with database_cursor(readonly=False) as cursor:
        # Serialize responses across tabs; replaying a completed question never counts twice.
        cursor.execute('select status from public.study_sessions where id=%s for update', (str(session_id),))
        session = cursor.fetchone()
        if not session:
            raise HTTPException(404, 'Không tìm thấy phiên học.')
        cursor.execute('select * from public.study_questions where id=%s and session_id=%s for update', (str(question_id), str(session_id)))
        question = cursor.fetchone()
        if not question:
            raise HTTPException(404, 'Không tìm thấy câu hỏi.')
        if question['answered_at']:
            return question['feedback']
        if session['status'] != 'active':
            raise HTTPException(409, 'Phiên học đã kết thúc.')
        cursor.execute('select id from public.study_questions where session_id=%s and answered_at is null order by position limit 1', (str(session_id),))
        if str(cursor.fetchone()['id']) != str(question_id):
            raise HTTPException(409, 'Hãy trả lời câu hiện tại trước.')
        try:
            correct = grade(question['payload'], request.answer)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        entry_id = str(question['entry_id'])
        cursor.execute('insert into public.learning_progress(entry_id) values(%s) on conflict(entry_id) do nothing', (entry_id,))
        cursor.execute('select * from public.learning_progress where entry_id=%s for update', (entry_id,))
        progress = cursor.fetchone()
        now = datetime.now(timezone.utc)
        update = review_update(progress, correct, question['is_retry'], now)
        cursor.execute('''update public.learning_progress set status='reviewing',review_step=%s,interval_days=%s,
            next_review_at=%s,last_review_at=%s,last_success_at=case when %s then %s else last_success_at end,
            review_count=review_count+1,correct_count=correct_count+%s,lapse_count=lapse_count+%s
            where entry_id=%s''', (update['review_step'],update['interval_days'],update['next_review_at'],now,
                                  correct,now,int(correct),int(not correct),entry_id))
        cursor.execute('insert into public.review_logs(entry_id,result,reviewed_at,interval_before,interval_after) values(%s,%s,%s,%s,%s)',
                       (entry_id,'remembered' if correct else 'forgotten',now,update['interval_before'],update['interval_days']))
        retry_added = not correct and not question['is_retry']
        if retry_added:
            cursor.execute('select coalesce(max(position),-1)+1 as position from public.study_questions where session_id=%s', (str(session_id),))
            position = cursor.fetchone()['position']
            cursor.execute('insert into public.study_questions(session_id,entry_id,position,is_retry,payload) values(%s,%s,%s,true,%s)',
                           (str(session_id),entry_id,position,Json(question['payload'])))
        payload = question['payload']
        feedback = {'correct': correct, 'word': payload['word'], 'example_sentence': payload.get('example_sentence'), 'accepted': payload['accepted'],
                    'meanings': payload['meanings'], 'ipa': payload['ipa'], 'audio_id': payload['audio_id'],
                    'retry_added': retry_added, 'is_retry': question['is_retry'],
                    'correct_count': progress['correct_count'] + int(correct),
                    'interval_days': update['interval_days'], 'next_review_at': update['next_review_at'].isoformat(),
                    'schedule_changed': update['schedule_changed']}
        cursor.execute('update public.study_questions set submitted_answer=%s,correct=%s,feedback=%s,answered_at=%s where id=%s',
                       (request.answer,correct,Json(feedback),now,str(question_id)))
        cursor.execute('''update public.study_sessions set status='completed',completed_at=%s where id=%s
            and not exists(select 1 from public.study_questions where session_id=%s and answered_at is null)''',
                       (now,str(session_id),str(session_id)))
        return feedback


@router.post('/sessions/{session_id}/finish')
def finish_session(session_id: UUID):
    with database_cursor(readonly=False) as cursor:
        cursor.execute("update public.study_sessions set status='abandoned',completed_at=now() where id=%s and status='active'", (str(session_id),))
        return session_view(cursor, session_id)
