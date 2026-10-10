import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.rate_limits import RateLimits, load_rate_limits
from app.services.dictionary_store import DictionaryStore, RateLimitError


class RateConfigTests(unittest.TestCase):
    def tearDown(self):
        load_rate_limits.cache_clear()

    def test_checked_in_config(self):
        load_rate_limits.cache_clear()
        self.assertEqual(load_rate_limits(), RateLimits(3, 60))

    def test_configurable_window_and_lowered_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            store = DictionaryStore(Path(folder) / 'test.db')
            with patch('app.services.dictionary_store.load_rate_limits', return_value=RateLimits(4, 120)):
                for now in (100, 110, 120, 130):
                    store.reserve_call(now=now)
            with patch('app.services.dictionary_store.load_rate_limits', return_value=RateLimits(2, 120)):
                with self.assertRaises(RateLimitError) as caught:
                    store.reserve_call(now=140)
                self.assertEqual(caught.exception.retry_after, 100)
                store.reserve_call(now=240)

    def test_invalid_configuration(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'config.toml'
            for value in ('0', '-1', 'true', '"3"'):
                path.write_text('[gemini]\nmax_requests=' + value + '\nwindow_seconds=60\n')
                load_rate_limits.cache_clear()
                with patch('app.rate_limits.CONFIG_PATH', path), self.assertRaises(ValueError):
                    load_rate_limits()

    def test_custom_file_values(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'config.toml'
            path.write_text('[gemini]\nmax_requests=5\nwindow_seconds=90\n')
            load_rate_limits.cache_clear()
            with patch('app.rate_limits.CONFIG_PATH', path):
                self.assertEqual(load_rate_limits(), RateLimits(5, 90))


if __name__ == '__main__':
    unittest.main()
