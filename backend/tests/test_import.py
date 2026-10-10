import unittest
from unittest.mock import MagicMock, patch

import psycopg2
from fastapi.testclient import TestClient

from app.main import app
from app.services.import_service import save_analysis


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.analysis = {
            'words': [{'word': 'learn', 'frequency': 3}],
            'phrases': [{'phrase': 'machine learning', 'frequency': 2}],
        }

    def test_bulk_upsert_preserves_progress_and_dictionary(self):
        with patch('app.services.import_service.database_cursor') as db, patch('app.services.import_service.execute_values') as execute:
            execute.side_effect = [[{'id': 'word-id'}, {'id': 'phrase-id'}], None]
            result = save_analysis(self.analysis)
        db.assert_called_once_with(readonly=False)
        self.assertEqual(result, {'saved': True, 'entry_ids': ['phrase-id', 'word-id'], 'word_count': 1, 'phrase_count': 1, 'occurrences_added': 5})
        entry_call, progress_call = execute.call_args_list
        self.assertEqual(entry_call.args[2], [('learn', 'word', 3), ('machine learning', 'phrase', 2)])
        self.assertIn('frequency = public.entries.frequency + excluded.frequency', entry_call.args[1])
        self.assertNotIn('lookup_status =', entry_call.args[1])
        self.assertIn('on conflict (entry_id) do nothing', progress_call.args[1])
        self.assertEqual(progress_call.args[2], [('word-id',), ('phrase-id',)])

    def test_empty_analysis_and_normalization(self):
        with patch('app.services.import_service.database_cursor') as db:
            result = save_analysis({'words': [], 'phrases': []})
            db.assert_not_called()
            self.assertEqual(result['occurrences_added'], 0)
        analysis = {'words': [{'word': ' LEARN ', 'frequency': 2}, {'word': 'learn', 'frequency': 3}], 'phrases': []}
        with patch('app.services.import_service.database_cursor'), patch('app.services.import_service.execute_values', side_effect=[[{'id': 'id'}], None]) as execute:
            self.assertEqual(save_analysis(analysis)['word_count'], 1)
            self.assertEqual(execute.call_args_list[0].args[2], [('learn', 'word', 5)])

    def test_second_write_failure_rolls_back_and_closes_connection(self):
        connection, cursor = MagicMock(), MagicMock()
        connection.cursor.return_value.__enter__.return_value = cursor
        with patch('app.database.load_dotenv'), patch.dict('os.environ', {'SUPABASE_URL': 'postgresql://test:test@localhost/test'}), patch('app.database.psycopg2.connect', return_value=connection), patch('app.services.import_service.execute_values', side_effect=[[{'id': 'id'}], psycopg2.DatabaseError('secret')]):
            from fastapi import HTTPException
            with self.assertRaises(HTTPException) as caught:
                save_analysis(self.analysis)
        self.assertEqual(caught.exception.status_code, 503)
        self.assertNotIn('secret', caught.exception.detail)
        self.assertIs(connection.__exit__.call_args.args[0], psycopg2.DatabaseError)
        connection.close.assert_called_once()

    def test_repeated_uploads_both_save(self):
        with patch('app.main.save_analysis', return_value={'saved': True, 'word_count': 1, 'phrase_count': 0, 'occurrences_added': 1}) as save, TestClient(app) as client:
            for _ in range(2):
                response = client.post('/analyze', data={'text': 'Learn English.'})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()['storage']['saved'])
            self.assertEqual(save.call_count, 2)

    def test_save_failure_not_reported_as_success(self):
        from fastapi import HTTPException
        with patch('app.main.save_analysis', side_effect=HTTPException(503, 'Cannot save')), TestClient(app) as client:
            response = client.post('/analyze', data={'text': 'Learn English.'})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('storage', response.json())

    def test_invalid_input_does_not_write(self):
        with patch('app.main.save_analysis') as save, TestClient(app) as client:
            self.assertEqual(client.post('/analyze', data={'text': '   '}).status_code, 400)
            save.assert_not_called()


if __name__ == '__main__':
    unittest.main()
