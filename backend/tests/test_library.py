import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import psycopg2
from fastapi.testclient import TestClient
from app.main import app
from app.database import database_cursor


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.cursor = MagicMock()
        self.connection = MagicMock()
        self.connection.cursor.return_value.__enter__.return_value = self.cursor
        self.connect = patch('app.database.psycopg2.connect', return_value=self.connection).start()
        self.env = patch.dict('os.environ', {'SUPABASE_URL': 'postgresql://postgres:test@localhost/postgres', 'SUPABASE_API_URL': 'https://example.supabase.co', 'SUPABASE_SERVICE_ROLE_KEY': 'test-only'}).start()
        self.addCleanup(patch.stopall)
        self.row = {
            'id': str(uuid4()), 'normalized_text': 'learn', 'kind': 'word',
            'frequency': 6, 'lookup_status': 'pending',
            'first_seen_at': datetime.now(timezone.utc), 'last_seen_at': datetime.now(timezone.utc),
            'meanings': [], 'pronunciations': [], 'learning_progress': None,
        }
        self.cursor.fetchone.return_value = {'total': 1}
        self.cursor.fetchall.return_value = [self.row]
        self.api = TestClient(app)
        self.addCleanup(self.api.close)

    def test_entry_without_children_and_close_connection(self):
        response = self.api.get('/entries')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['items'][0]['normalized_text'], 'learn')
        self.assertEqual(data['items'][0]['frequency'], 6)
        self.assertIsNone(data['items'][0]['learning_progress'])
        self.assertEqual(self.cursor.execute.call_args.args[1], (None, None, 20, 0))
        self.connection.close.assert_called_once()
        self.connection.set_session.assert_called_once_with(readonly=True, isolation_level='REPEATABLE READ')
        self.assertEqual(self.connect.call_args.kwargs['sslmode'], 'require')

    def test_pagination_filter_and_empty(self):
        self.cursor.fetchall.return_value = []
        self.cursor.fetchone.return_value = {'total': 0}
        response = self.api.get('/entries?page=2&page_size=10&kind=phrase')
        self.assertEqual(response.json()['items'], [])
        self.assertEqual(self.cursor.execute.call_args.args[1], ('phrase', 'phrase', 10, 10))
        for query in ('page=0', 'page_size=101', 'kind=invalid'):
            self.assertEqual(self.api.get('/entries?' + query).status_code, 422)

    def test_meanings_and_progress(self):
        self.row['meanings'] = [{'id': str(uuid4()), 'part_of_speech': 'verb', 'meaning_vi': 'học', 'examples': [{'english': 'I learn.', 'vietnamese': 'Tôi học.'}], 'sort_order': 1}]
        self.row['learning_progress'] = {'status': 'reviewing', 'review_step': 1, 'interval_days': 1, 'next_review_at': '2026-10-11T00:00:00Z', 'last_review_at': None, 'review_count': 1, 'lapse_count': 0}
        data = self.api.get('/entries').json()['items'][0]
        self.assertEqual(data['meanings'][0]['meaning_vi'], 'học')
        self.assertEqual(data['learning_progress']['interval_days'], 1)

    def test_db_failure_is_safe_and_connection_closes(self):
        self.cursor.execute.side_effect = psycopg2.OperationalError('secret-password')
        response = self.api.get('/entries')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('secret-password', response.text)
        self.connection.close.assert_called_once()

    def test_missing_configuration(self):
        with patch('app.database.load_dotenv'), patch.dict('os.environ', {'SUPABASE_URL': ''}):
            self.assertEqual(self.api.get('/entries').status_code, 503)
        self.connect.assert_not_called()

    def test_connection_failure(self):
        self.connect.side_effect = psycopg2.OperationalError('secret-password')
        response = self.api.get('/entries')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('secret-password', response.text)

    def test_saved_audio_missing_and_signing(self):
        identifier = str(uuid4())
        self.cursor.fetchone.return_value = {'audio_bucket': 'pronunciation', 'audio_path': 'entries/test.wav', 'audio_status': 'ready'}
        with patch('app.library_routes.create_client') as create:
            create.return_value.storage.from_.return_value.create_signed_url.return_value = {'signedURL': 'https://example.com/signed.wav'}
            response = self.api.get(f'/entries/pronunciations/{identifier}/audio')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['expires_in'], 600)
            self.assertEqual(self.cursor.execute.call_args.args[1], (identifier,))
        self.cursor.fetchone.return_value = None
        self.assertEqual(self.api.get(f'/entries/pronunciations/{identifier}/audio').status_code, 404)
        self.assertEqual(self.api.get('/entries/pronunciations/not-a-uuid/audio').status_code, 422)

    def test_read_does_not_require_storage_credentials(self):
        with patch.dict('os.environ', {'SUPABASE_API_URL': '', 'SUPABASE_SERVICE_ROLE_KEY': ''}):
            self.assertEqual(self.api.get('/entries').status_code, 200)


if __name__ == '__main__':
    unittest.main()
