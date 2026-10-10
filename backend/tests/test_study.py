import unittest
from datetime import datetime, timedelta, timezone
from app.services.study_rules import build_question, grade, review_update, short_answers
from app.study_routes import submit_answer, Answer
from unittest.mock import patch, MagicMock
from uuid import uuid4

class StudyRulesTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.entry = dict(id='1', normalized_text='learn', meanings=[dict(meaning_vi='học, học hỏi, tiếp thu (verb)')], audio_id='audio')
        self.other = dict(id='2', normalized_text='eat', meanings=[dict(meaning_vi='ăn')])
    def test_short_meanings(self):
        self.assertEqual(short_answers(self.entry['meanings']), ['học', 'học hỏi', 'tiếp thu'])
    def test_choices(self):
        q = build_question(self.entry, [self.entry, self.other], 'en_vi')
        self.assertEqual(sum(grade(q, o['id']) for o in q['options']), 1)
        with self.assertRaises(ValueError): grade(q, 'invented')
    def test_no_distractors(self):
        self.assertIsNone(build_question(self.entry, [self.entry], 'en_vi'))
    def test_listening(self):
        q = build_question(self.entry, [self.entry], 'listening')
        self.assertTrue(grade(q, '  LEARN!  '))
        self.assertFalse(grade(q, 'learned'))
        self.assertIsNone(build_question(self.other, [self.other], 'listening'))
    def test_reverse_synonyms(self):
        synonym = dict(id='3', normalized_text='study', meanings=[dict(meaning_vi='học')])
        q = build_question(self.entry, [self.entry, synonym], 'vi_en')
        self.assertTrue(grade(q, 'study'))
    def progress(self, step=0, due=None):
        return dict(status='new' if step==0 else 'reviewing', review_step=step, interval_days=0 if step==0 else 9, next_review_at=due)
    def test_new(self):
        result=review_update(self.progress(), True, False, self.now)
        self.assertEqual(result['interval_days'],1)
        self.assertEqual(result['next_review_at'],self.now+timedelta(days=1))
    def test_after_nine(self):
        self.assertEqual(review_update(self.progress(5,self.now),True,False,self.now)['interval_days'],14)
    def test_failure_and_retry(self):
        result=review_update(self.progress(5,self.now),False,False,self.now)
        self.assertEqual(result['review_step'],1)
        progress=dict(status='reviewing',**{k:result[k] for k in ('review_step','interval_days','next_review_at')})
        retry=review_update(progress,True,True,self.now)
        self.assertFalse(retry['schedule_changed'])
    def test_early_practice(self):
        result=review_update(self.progress(5,self.now+timedelta(days=2)),True,False,self.now)
        self.assertFalse(result['schedule_changed'])
    def test_answer_replay_does_not_update_progress(self):
        cursor=MagicMock()
        cursor.fetchone.side_effect=[{'status':'completed'}, {'answered_at':self.now,'feedback':{'correct':True}}]
        with patch('app.study_routes.database_cursor') as db:
            db.return_value.__enter__.return_value=cursor
            self.assertEqual(submit_answer(uuid4(),uuid4(),Answer(answer='learn')),{'correct':True})
        self.assertEqual(cursor.execute.call_count,2)

if __name__=='__main__': unittest.main()
