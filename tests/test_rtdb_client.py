import pytest
from desktop.cloud.rtdb_client import seed_if_missing, get_user_config


class FakeRTDB:
    def __init__(self, initial=None):
        self.store = initial or {}

    def get(self, path, token):
        return self.store.get(path)

    def put(self, path, token, data):
        self.store[path] = data

    def patch(self, path, token, data):
        if path not in self.store:
            self.store[path] = {}
        self.store[path].update(data)


def test_seed_if_missing_creates_new():
    db = FakeRTDB()
    default = {"activeProfile": "default"}

    result = seed_if_missing(db, "uid1", "token", default)

    assert result == default
    assert db.store["users/uid1"] == default


def test_get_user_config_returns_empty_if_none():
    db = FakeRTDB()
    result = get_user_config(db, "token", "uid1")
    assert result == {}
