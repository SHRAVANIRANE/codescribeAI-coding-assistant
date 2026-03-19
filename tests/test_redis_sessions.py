import time
import unittest
from unittest.mock import patch

import main


class RedisSessionStoreTests(unittest.TestCase):
    def setUp(self):
        # Ensure we operate in redis session mode for the duration of this test.
        self._orig_store_type = main.SESSION_STORE_TYPE
        self._orig_redis_client = main._redis_client
        main.SESSION_STORE_TYPE = "redis"
        main._redis_client = None

        # Provide a lightweight in-memory Redis stub.
        self._store = {}

        class FakeRedis:
            def __init__(self, store):
                self._store = store

            def ping(self):
                return True

            def set(self, key, value, ex=None):
                self._store[key] = value

            def get(self, key):
                return self._store.get(key)

            def delete(self, key):
                self._store.pop(key, None)

        self.fake_redis = FakeRedis(self._store)
        self._patcher = patch("main._get_redis_client", return_value=self.fake_redis)
        self._patcher.start()

        # Initialize store (no-op for redis) to ensure no SQLite usage.
        main.init_session_store()

    def tearDown(self):
        self._patcher.stop()
        main.SESSION_STORE_TYPE = self._orig_store_type
        main._redis_client = self._orig_redis_client

    def test_redis_session_store_basic_flow(self):
        session_id = "test-session"
        session_data = {
            "user": "redis-user",
            "expires": time.time() + 60,
        }

        # Save and retrieve
        main.session_store_set(session_id, session_data)
        got = main.session_store_get(session_id)
        self.assertIsNotNone(got)
        self.assertEqual(got.get("user"), "redis-user")

        # Delete should remove session
        main.session_store_delete(session_id)
        self.assertIsNone(main.session_store_get(session_id))


if __name__ == "__main__":
    unittest.main()
