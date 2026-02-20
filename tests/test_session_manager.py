import pytest
import desktop.core.session_manager as session_manager


def test_get_uid_without_login(monkeypatch):
    # Patch where it's USED (session_manager.load_auth_cache), not where it's DEFINED
    monkeypatch.setattr(session_manager, "load_auth_cache", lambda: {})
    sm = session_manager.SessionManager("API_KEY")
    with pytest.raises(RuntimeError):
        sm.get_uid()


def test_update_from_login(monkeypatch):
    # Prevent disk writes during tests (optional but cleaner)
    monkeypatch.setattr(session_manager, "save_auth_cache", lambda _data: None)

    sm = session_manager.SessionManager("API_KEY")
    sm.update_from_login({
        "uid": "uid123",
        "idToken": "token",
        "refreshToken": "refresh"
    })
    assert sm.get_uid() == "uid123"
