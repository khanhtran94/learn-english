import base64
import io
import tempfile
import unittest
import wave
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.dictionary_service import DictionaryError, DictionaryService, get_dictionary_service
from app.services.dictionary_store import DictionaryStore, RateLimitError

ENTRY = '{"found":true,"ipa":"/bæŋk/","meanings":[{"part_of_speech":"noun","vietnamese":"ngân hàng","examples":[{"english":"I went to the bank.","vietnamese":"Tôi đến ngân hàng."}]},{"part_of_speech":"noun","vietnamese":"bờ sông","examples":[]}]}'


class DictionaryTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict("os.environ", {"GEMINI_API_KEY": "test-only"})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "cache.db"
        self.store = DictionaryStore(self.path)
        self.client = MagicMock()
        self.client.models.generate_content.return_value = SimpleNamespace(text=ENTRY)
        self.service = DictionaryService(self.store, client=self.client)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.temp.cleanup()

    def test_multiple_meanings_and_persistent_cache(self):
        first = self.service.lookup("bank")
        second = DictionaryService(DictionaryStore(self.path), client=self.client).lookup("bank")
        self.assertEqual(len(first.meanings), 2)
        self.assertEqual(first.ipa, "/bæŋk/")
        self.assertFalse(first.cached)
        self.assertTrue(second.cached)
        self.client.models.generate_content.assert_called_once()

    def test_concurrent_same_term_only_calls_once(self):
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(self.service.lookup, ["bank"] * 6))
        self.assertEqual(sum(not result.cached for result in results), 1)
        self.client.models.generate_content.assert_called_once()

    def test_rolling_rate_limit_and_boundary(self):
        for _ in range(15):
            self.store.reserve_call(now=100)
        with self.assertRaises(RateLimitError) as caught:
            DictionaryStore(self.path).reserve_call(now=159)
        self.assertEqual(caught.exception.retry_after, 1)
        self.store.reserve_call(now=160)

    def test_concurrent_limiter_shared_connections(self):
        def attempt(_):
            try:
                self.store.reserve_call(now=100)
                return True
            except RateLimitError:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(attempt, range(25))), 15)

    def test_no_data_is_cached_but_errors_are_not(self):
        self.client.models.generate_content.return_value.text = '{"found":false,"ipa":null,"meanings":[]}'
        self.assertFalse(self.service.lookup("unknown").found)
        self.assertTrue(self.service.lookup("unknown").cached)
        for text in (None, 'not json', '{"found":true,"ipa":null,"meanings":[]}'):
            self.client.models.generate_content.return_value.text = text
            with self.assertRaises(DictionaryError) as caught:
                self.service.lookup("bad")
            self.assertEqual(caught.exception.status, 502)
        self.client.models.generate_content.return_value.text = ENTRY
        self.assertTrue(self.service.lookup("bad").found)

    def test_provider_429_and_timeout(self):
        import httpx
        error = RuntimeError("sensitive provider error")
        error.code = 429
        for exc, status in ((error, 429), (httpx.ReadTimeout("timeout"), 504), (RuntimeError("secret"), 502)):
            self.client.models.generate_content.side_effect = exc
            with self.assertRaises(DictionaryError) as caught:
                self.service.lookup("bank")
            self.assertEqual(caught.exception.status, status)
            self.assertNotIn("secret", caught.exception.message)

    def test_missing_api_key(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
            with self.assertRaises(DictionaryError) as caught:
                DictionaryService(self.store).lookup("bank")
        self.assertEqual(caught.exception.status, 503)
        with closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM calls').fetchone()[0], 0)

    def make_audio(self):
        stream = io.BytesIO()
        with wave.open(stream, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(24000)
            wav.writeframes(b'\0\0' * 100)
        return stream.getvalue()

    def test_audio_cache_and_shared_limit(self):
        audio = self.make_audio()
        import httpx
        requests = []
        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={"steps": [{"type": "model_output", "content": [{"type": "audio", "data": base64.b64encode(audio).decode()}]}]})
        self.service.audio_transport = httpx.MockTransport(handler)
        self.assertEqual(self.service.audio("bank"), audio)
        self.assertEqual(self.service.audio("bank"), audio)
        self.assertEqual(len(requests), 1)
        for _ in range(14):
            self.store.reserve_call()
        with self.assertRaises(DictionaryError) as caught:
            self.service.lookup("bank")
        self.assertEqual(caught.exception.status, 429)
        self.client.models.generate_content.assert_not_called()
        self.assertEqual(self.service.audio("bank"), audio)

    def test_missing_and_invalid_audio(self):
        for output, status in ((None, 404), (SimpleNamespace(data="bad"), 502), (SimpleNamespace(data=base64.b64encode(b'not wav').decode()), 502)):
            import httpx
            payload = {"steps": []} if output is None else {"steps": [{"type": "model_output", "content": [{"type": "audio", "data": output.data}]}]}
            self.service.audio_transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
            with self.assertRaises(DictionaryError) as caught:
                self.service.audio("bank")
            self.assertEqual(caught.exception.status, status)

    def test_supabase_hit_and_failure_fallback(self):
        import json
        remote = MagicMock()
        remote.table.return_value.select.return_value.eq.return_value.gt.return_value.limit.return_value.execute.return_value.data = [{"entry": json.loads(ENTRY)}]
        service = DictionaryService(self.store, client=self.client, remote=remote)
        self.assertTrue(service.lookup("bank").cached)
        self.client.models.generate_content.assert_not_called()
        remote.table.side_effect = RuntimeError("database unavailable")
        self.assertTrue(service.lookup("river").found)
        self.assertTrue(service.lookup("river").cached)

    def test_api_normalization_validation_and_retry_header(self):
        app.dependency_overrides[get_dictionary_service] = lambda: self.service
        with TestClient(app) as api:
            response = api.post('/dictionary/lookup', json={"term": "  BANK  "})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["term"], "bank")
            for body in ({"term": ["bank", "car"]}, {"term": "bank, car"}, {"term": ""}, {"term": "a " * 13}, {"term": "bank", "extra": True}):
                self.assertEqual(api.post('/dictionary/lookup', json=body).status_code, 422)
            for _ in range(14):
                self.store.reserve_call()
            response = api.post('/dictionary/lookup', json={"term": "car"})
            self.assertEqual(response.status_code, 429)
            self.assertGreater(int(response.headers['Retry-After']), 0)
            self.assertEqual(api.post('/dictionary/lookup', json={"term": "bank"}).status_code, 200)

    def test_sdk_transport_contract_without_network(self):
        import httpx
        from google import genai
        from google.genai import types
        requests = []
        def handler(request):
            requests.append(request)
            return httpx.Response(429, json={"error": {"code": 429, "message": "quota", "status": "RESOURCE_EXHAUSTED"}})
        with genai.Client(api_key="test-only", http_options=types.HttpOptions(
            client_args={"transport": httpx.MockTransport(handler)},
            retry_options=types.HttpRetryOptions(attempts=1), timeout=30000,
        )) as client:
            service = DictionaryService(self.store, client=client, audio_transport=httpx.MockTransport(handler))
            for operation in (service.lookup, service.audio):
                with self.assertRaises(DictionaryError) as caught:
                    operation("bank")
                self.assertEqual(caught.exception.status, 429)
        self.assertEqual(len(requests), 2, "SDK must not retry outside the limiter")


if __name__ == '__main__':
    unittest.main()
