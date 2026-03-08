import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import main


class _MockHTTPResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.headers = {}
        self.text = ""

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _MockAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, params=None, headers=None):
        if "login/oauth/access_token" in url:
            return _MockHTTPResponse(
                200,
                {"access_token": "mock_access_token"},
            )
        return _MockHTTPResponse(404, {"message": "not found"})

    async def get(self, url, headers=None):
        if url == "https://api.github.com/user":
            return _MockHTTPResponse(
                200,
                {"login": "mock-user", "id": 12345},
            )
        return _MockHTTPResponse(404, {"message": "not found"})


class AuthSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_db = main.SESSIONS_DB_PATH
        cls._tmp_dir = tempfile.TemporaryDirectory()
        main.SESSIONS_DB_PATH = os.path.join(cls._tmp_dir.name, "test_sessions.db")
        main.init_session_store()

    @classmethod
    def tearDownClass(cls):
        main.SESSIONS_DB_PATH = cls._orig_db
        try:
            cls._tmp_dir.cleanup()
        except PermissionError:
            # On Windows, sqlite may release file handles slightly later.
            pass

    def setUp(self):
        main.session_store_cleanup_expired()
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()

    def test_login_sets_oauth_state_cookie(self):
        res = self.client.get("/login/github", follow_redirects=False)
        self.assertEqual(res.status_code, 307)
        self.assertIn("oauth_state=", res.headers.get("set-cookie", ""))
        self.assertIn("github.com/login/oauth/authorize", res.headers.get("location", ""))

    def test_callback_rejects_missing_state_cookie(self):
        res = self.client.get("/auth/github/callback?code=abc&state=s1", follow_redirects=False)
        self.assertEqual(res.status_code, 400)
        self.assertIn("OAuth state cookie", res.json().get("detail", ""))

    def test_callback_rejects_state_mismatch(self):
        self.client.get("/login/github", follow_redirects=False)
        res = self.client.get("/auth/github/callback?code=abc&state=wrong", follow_redirects=False)
        self.assertEqual(res.status_code, 400)
        self.assertIn("state mismatch", res.json().get("detail", ""))

    def test_callback_creates_session_and_auth_works_then_logout(self):
        login_res = self.client.get("/login/github", follow_redirects=False)
        self.assertEqual(login_res.status_code, 307)
        location = login_res.headers["location"]
        state = location.split("state=")[1].split("&")[0]

        with patch("main.httpx.AsyncClient", _MockAsyncClient):
            callback_res = self.client.get(
                f"/auth/github/callback?code=abc123&state={state}",
                follow_redirects=False,
            )
        self.assertEqual(callback_res.status_code, 307)
        self.assertIn("session_id=", callback_res.headers.get("set-cookie", ""))

        authed = self.client.get("/test-auth")
        self.assertEqual(authed.status_code, 200)
        self.assertIn("mock-user", authed.json().get("message", ""))

        logout = self.client.post("/logout")
        self.assertEqual(logout.status_code, 200)

        authed_after = self.client.get("/test-auth")
        self.assertEqual(authed_after.status_code, 401)


if __name__ == "__main__":
    unittest.main()
