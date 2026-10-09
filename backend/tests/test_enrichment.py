import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app
from app.dictionary_models import LookupResponse
from app.services.dictionary_service import DictionaryError, get_dictionary_service
from app.services.enrichment_service import enrich_entry


class EnrichmentTests(unittest.TestCase):
    def setUp(self):
        self.entry_id = uuid4()
        self.db = patch('app.services.enrichment_service.database_cursor').start()
        self.repo_type = patch('app.services.enrichment_service.EntryRepository').start()
        self.repo = self.repo_type.return_value
        self.repo.load.return_value = {'normalized_text': 'learn', 'has_meanings': False, 'has_audio': False}
        self.storage_factory = patch('app.services.enrichment_service.storage_client').start()
        self.storage = self.storage_factory.return_value.storage.from_.return_value
        self.dictionary = MagicMock(model='test-text', audio_model='test-audio')
        self.dictionary.lookup.return_value = LookupResponse(term='learn', cached=False, found=True, ipa='/lɜːn/', meanings=[{'part_of_speech': 'verb', 'vietnamese': 'học', 'examples': [{'english': 'I learn English.', 'vietnamese': 'Tôi học tiếng Anh.'}]}])
        self.dictionary.audio.return_value = b'wave-data'
        self.addCleanup(patch.stopall)
        self.addCleanup(app.dependency_overrides.clear)

    def test_meanings_ipa_and_storage_success(self):
        result = enrich_entry(self.entry_id, self.dictionary)
        self.assertEqual(result['status'], 'complete')
        self.assertTrue(result['meanings_saved'])
        self.assertTrue(result['audio_saved'])
        self.dictionary.lookup.assert_called_once_with('learn')
        self.repo.save_meanings.assert_called_once_with(self.dictionary.lookup.return_value, 'test-text')
        self.storage.upload.assert_called_once_with(f'entries/{self.entry_id}/en-US/Kore.wav', b'wave-data', file_options={'content-type': 'audio/wav', 'upsert': 'true'})
        self.assertEqual(self.repo.audio_status.call_args.args[0], 'ready')
        self.db.return_value.__exit__.assert_called_once_with(None, None, None)

    def test_existing_complete_entry_never_calls_provider(self):
        self.repo.load.return_value.update(has_meanings=True, has_audio=True)
        result = enrich_entry(self.entry_id, self.dictionary)
        self.assertEqual(result['status'], 'complete')
        self.dictionary.lookup.assert_not_called()
        self.dictionary.audio.assert_not_called()
        self.storage_factory.assert_not_called()

    def test_existing_meanings_only_fetches_audio(self):
        self.repo.load.return_value.update(has_meanings=True)
        enrich_entry(self.entry_id, self.dictionary)
        self.dictionary.lookup.assert_not_called()
        self.repo.save_meanings.assert_not_called()
        self.dictionary.audio.assert_called_once()

    def test_upload_failure_keeps_meanings_and_commits_partial(self):
        self.storage.upload.side_effect = RuntimeError('sensitive storage credential')
        result = enrich_entry(self.entry_id, self.dictionary)
        self.assertEqual(result['status'], 'partial')
        self.assertTrue(result['meanings_saved'])
        self.assertFalse(result['audio_saved'])
        self.assertNotIn('sensitive', result['message'])
        self.assertEqual(self.repo.audio_status.call_args.args[0], 'failed')
        self.db.return_value.__exit__.assert_called_once_with(None, None, None)

    def test_audio_quota_returns_retry_without_losing_meanings(self):
        self.dictionary.audio.side_effect = DictionaryError(429, 'quota', 42)
        result = enrich_entry(self.entry_id, self.dictionary)
        self.assertEqual(result['retry_after'], 42)
        self.assertEqual(result['status'], 'partial')
        self.repo.audio_status.assert_called_once_with('pending', 'test-audio')
        self.storage.upload.assert_not_called()

    def test_lookup_quota_commits_pending_before_raising(self):
        self.dictionary.lookup.side_effect = DictionaryError(429, 'quota', 10)
        with self.assertRaises(DictionaryError):
            enrich_entry(self.entry_id, self.dictionary)
        self.repo.lookup_status.assert_called_once_with('pending')
        self.repo.save_meanings.assert_not_called()
        self.db.return_value.__exit__.assert_called_once_with(None, None, None)

    def test_not_found_does_not_generate_audio(self):
        self.dictionary.lookup.return_value = LookupResponse(term='learn', cached=False, found=False, ipa=None, meanings=[])
        result = enrich_entry(self.entry_id, self.dictionary)
        self.assertEqual(result['status'], 'not_found')
        self.repo.lookup_status.assert_called_once_with('not_found')
        self.dictionary.audio.assert_not_called()

    def test_missing_storage_preserves_meanings_without_tts_call(self):
        self.storage_factory.side_effect = DictionaryError(503, 'Missing Storage config')
        result = enrich_entry(self.entry_id, self.dictionary)
        self.assertEqual(result['status'], 'partial')
        self.dictionary.audio.assert_not_called()
        self.assertTrue(result['meanings_saved'])

    def test_api_retry_after_and_input_validation(self):
        app.dependency_overrides[get_dictionary_service] = lambda: self.dictionary
        self.dictionary.lookup.side_effect = DictionaryError(429, 'quota', 20)
        with TestClient(app) as client:
            response = client.post(f'/entries/{self.entry_id}/enrich')
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response.headers['Retry-After'], '20')
            self.assertEqual(client.post('/entries/not-an-id/enrich').status_code, 422)


class RepositoryTests(unittest.TestCase):
    def test_busy_lock_returns_conflict_and_no_provider_work(self):
        from app.services.enrichment_service import EntryRepository
        from fastapi import HTTPException
        cursor = MagicMock()
        cursor.fetchone.return_value = {'acquired': False}
        with self.assertRaises(HTTPException) as caught:
            EntryRepository(cursor, uuid4()).load()
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(cursor.execute.call_count, 1)

    def test_missing_entry(self):
        from app.services.enrichment_service import EntryRepository
        from fastapi import HTTPException
        cursor = MagicMock()
        cursor.fetchone.side_effect = [{'acquired': True}, None]
        with self.assertRaises(HTTPException) as caught:
            EntryRepository(cursor, uuid4()).load()
        self.assertEqual(caught.exception.status_code, 404)


if __name__ == '__main__':
    unittest.main()
