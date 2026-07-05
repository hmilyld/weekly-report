import threading

from app.key_cache import KeyCache


class TestKeyCache:
    def test_cache_and_retrieve(self):
        cache = KeyCache()
        cache.set(1, b"key1")
        assert cache.get(1) == b"key1"

    def test_get_missing_key(self):
        cache = KeyCache()
        assert cache.get(999) is None

    def test_remove_key(self):
        cache = KeyCache()
        cache.set(1, b"key1")
        cache.remove(1)
        assert cache.get(1) is None

    def test_remove_missing_key(self):
        cache = KeyCache()
        cache.remove(999)

    def test_overwrite_key(self):
        cache = KeyCache()
        cache.set(1, b"key1")
        cache.set(1, b"key2")
        assert cache.get(1) == b"key2"

    def test_multiple_users(self):
        cache = KeyCache()
        cache.set(1, b"key1")
        cache.set(2, b"key2")
        assert cache.get(1) == b"key1"
        assert cache.get(2) == b"key2"

    def test_clear_all(self):
        cache = KeyCache()
        cache.set(1, b"key1")
        cache.set(2, b"key2")
        cache.clear()
        assert cache.get(1) is None
        assert cache.get(2) is None

    def test_concurrent_access(self):
        cache = KeyCache()
        errors = []

        def writer(user_id: int):
            try:
                for i in range(100):
                    cache.set(user_id, f"key{i}".encode())
            except Exception as e:
                errors.append(e)

        def reader(user_id: int):
            try:
                for _ in range(100):
                    cache.get(user_id)
            except Exception as e:
                errors.append(e)

        threads = []
        for uid in range(5):
            threads.append(threading.Thread(target=writer, args=(uid,)))
            threads.append(threading.Thread(target=reader, args=(uid,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
