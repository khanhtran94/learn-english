import unittest
from app.services.study_rules import build_question, grade
from app.study_routes import StartSession, session_view
from unittest.mock import MagicMock

class ClozeTests(unittest.TestCase):
    def entry(self, word='learn', sentences=None):
        return dict(id='1',normalized_text=word,meanings=[dict(meaning_vi='học',examples=[{'english':s} for s in (sentences or [])])])
    def test_cloze_and_grading(self):
        q=build_question(self.entry(sentences=['I want to learn English.']),[], 'cloze')
        self.assertEqual(q['prompt'],'I want to _____ English.')
        self.assertEqual(q['example_sentence'],'I want to learn English.')
        self.assertTrue(grade(q,' LEARN '))
        self.assertFalse(grade(q,'learned'))
    def test_word_boundaries(self):
        for sentence in ['I learned English.', 'A learner.', 'Re-learn it.', "learn's"]:
            self.assertIsNone(build_question(self.entry(sentences=[sentence]),[], 'cloze'))
    def test_phrase_and_repeated_target(self):
        q=build_question(self.entry('look up',['Look up a word, then look up another.']),[],'cloze')
        self.assertEqual(q['prompt'],'_____ a word, then _____ another.')
        self.assertTrue(grade(q,'look up'))
    def test_missing_examples(self):
        self.assertIsNone(build_question(self.entry(),[],'cloze'))
        self.assertIsNone(build_question(self.entry(sentences=[None]),[],'cloze'))
    def test_no_short_meaning_required(self):
        e=self.entry(sentences=['We learn.']); e['meanings'][0]['meaning_vi']=''
        self.assertIsNotNone(build_question(e,[],'cloze'))
    def test_api_accepts_mode_and_hides_solution(self):
        self.assertEqual(StartSession(mode='cloze').mode,'cloze')
        q=build_question(self.entry(sentences=['We learn.']),[],'cloze')
        cursor=MagicMock(); cursor.fetchone.side_effect=[dict(id='s',mode='cloze',scope='due_new',status='active'),dict(total=1),dict(id='q',is_retry=False,payload=q)]
        public=session_view(cursor,'s')['question']
        self.assertNotIn('accepted',public)
        self.assertNotIn('example_sentence',public)
        self.assertIsNone(public['audio_id'])
