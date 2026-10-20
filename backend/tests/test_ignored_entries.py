import unittest
from unittest.mock import patch
from uuid import uuid4
from fastapi import HTTPException
from app.services.import_service import save_analysis
from app.library_routes import ignore_entry, restore_entry


class IgnoredEntryTests(unittest.TestCase):
    def test_ignored_word_is_not_saved_or_returned_but_other_phrase_is(self):
        analysis = {'words': [{'word': ' London ', 'frequency': 5}],
                    'phrases': [{'phrase': 'london bridge', 'frequency': 2}]}
        with patch('app.services.import_service.database_cursor') as db, patch('app.services.import_service.execute_values') as execute:
            db.return_value.__enter__.return_value.fetchall.return_value = [
                {'normalized_text': 'london', 'kind': 'word'}]
            execute.side_effect = [[{'id': 'phrase-id', 'frequency': 2}], None]
            result = save_analysis(analysis)
            self.assertEqual(execute.call_args_list[0].args[2], [('london bridge', 'phrase', 2)])
        self.assertEqual(result['word_count'], 0)
        self.assertEqual(result['occurrences_added'], 2)
        self.assertEqual(analysis['words'], [])
        self.assertEqual(analysis['unique_words'], 0)
        self.assertEqual(analysis['total_phrases'], 2)

    def test_all_ignored_no_upsert_or_progress(self):
        with patch('app.services.import_service.database_cursor') as db, patch('app.services.import_service.execute_values') as execute:
            db.return_value.__enter__.return_value.fetchall.return_value = [
                {'normalized_text': 'london', 'kind': 'word'}]
            result = save_analysis({'words': [{'word': 'London', 'frequency': 1}], 'phrases': []})
            execute.assert_not_called()
        self.assertEqual(result['entry_ids'], [])
        self.assertEqual(result['occurrences_added'], 0)

    def test_ignore_preserves_original_data(self):
        with patch('app.library_routes.database_cursor') as db:
            cursor = db.return_value.__enter__.return_value
            cursor.fetchone.side_effect = [{'acquired': True}, {'normalized_text': 'london', 'kind': 'word'}]
            self.assertTrue(ignore_entry(uuid4())['ignored'])
            sql = ' '.join(call.args[0] for call in cursor.execute.call_args_list).lower()
            self.assertIn('insert into public.ignored_entries', sql)
            self.assertNotIn('delete from', sql)
            self.assertIn("status='abandoned'", sql)

    def test_enriching_entry_cannot_be_ignored_mid_request(self):
        with patch('app.library_routes.database_cursor') as db:
            db.return_value.__enter__.return_value.fetchone.return_value = {'acquired': False}
            with self.assertRaises(HTTPException) as error:
                ignore_entry(uuid4())
            self.assertEqual(error.exception.status_code, 409)

    def test_restore_removes_only_archive_membership(self):
        with patch('app.library_routes.database_cursor') as db:
            self.assertFalse(restore_entry(uuid4())['ignored'])
            sql = db.return_value.__enter__.return_value.execute.call_args.args[0]
            self.assertIn('delete from public.ignored_entries', sql)
