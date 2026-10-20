"""Existing feature tests isolate authentication; test_auth covers the real gate."""
from unittest.mock import patch
from fastapi.testclient import TestClient


class AuthenticatedClient(TestClient):
    def request(self, *args, **kwargs):
        with patch("app.auth.valid_session", return_value=True):
            return super().request(*args, **kwargs)
