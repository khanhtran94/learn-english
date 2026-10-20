import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from app.main import app
from app import auth


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"APP_USERNAME": "owner", "APP_PASSWORD": "private-test-password"})
        self.env.start()
        self.addCleanup(self.env.stop)
        auth._sessions.clear()
        auth._attempts.clear()
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def login(self):
        return self.client.post("/auth/login", json={"username": "owner", "password": "private-test-password"})

    def test_all_private_routes_blocked(self):
        for method, path in [
            ("GET", "/entries"), ("POST", "/analyze"),
            ("POST", "/dictionary/lookup"), ("POST", "/dictionary/audio"),
            ("POST", "/entries/00000000-0000-0000-0000-000000000001/enrich"),
            ("GET", "/entries/pronunciations/00000000-0000-0000-0000-000000000001/audio"),
            ("GET", "/study/sessions/current"), ("POST", "/study/sessions"),
            ("GET", "/docs"), ("GET", "/openapi.json"),
        ]:
            self.assertEqual(self.client.request(method, path).status_code, 401, path)
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_login_logout_revokes_session(self):
        result = self.login()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.headers["cache-control"], "no-store")
        headers = {"Authorization": "Bearer " + result.json()["access_token"]}
        self.assertEqual(self.client.get("/auth/session", headers=headers).json(), {"username": "owner"})
        self.assertEqual(self.client.post("/auth/logout", headers=headers).status_code, 200)
        self.assertEqual(self.client.get("/auth/session", headers=headers).status_code, 401)

    def test_expiry_and_password_change(self):
        token = self.login().json()["access_token"]
        headers = {"Authorization": "Bearer " + token}
        with patch.dict(os.environ, {"APP_PASSWORD": "changed"}):
            self.assertEqual(self.client.get("/auth/session", headers=headers).status_code, 401)
        expires, fingerprint = auth._sessions[auth.token_key(token)]
        auth._sessions[auth.token_key(token)] = (0, fingerprint)
        self.assertEqual(self.client.get("/auth/session", headers=headers).status_code, 401)

    def test_wrong_password_throttle(self):
        for _ in range(auth.LOGIN_LIMIT):
            response = self.client.post("/auth/login", json={"username": "owner", "password": "wrong"})
            self.assertEqual(response.status_code, 401)
        response = self.login()
        self.assertEqual(response.status_code, 429)
        self.assertIn("retry-after", response.headers)

    def test_unconfigured_fails_closed(self):
        with patch.dict(os.environ, {"APP_PASSWORD": ""}):
            self.assertEqual(self.login().status_code, 503)
            self.assertEqual(self.client.get("/entries").status_code, 503)

    def test_cors_preflight_and_unauthorized_response(self):
        origin = "https://learn-english-khaki.vercel.app"
        response = self.client.options("/entries", headers={
            "Origin": origin, "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        })
        self.assertEqual(response.status_code, 200)
        response = self.client.get("/entries", headers={"Origin": origin})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["access-control-allow-origin"], origin)

    def test_invalid_token(self):
        self.assertEqual(self.client.get("/auth/session", headers={"Authorization": "Bearer fake"}).status_code, 401)
