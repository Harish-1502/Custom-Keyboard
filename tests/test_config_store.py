import json
import threading
import pytest
from pathlib import Path

from desktop.core import config_store


@pytest.fixture
def temp_config(tmp_path, monkeypatch):
    config_path = tmp_path / "buttonControls.json"
    default_path = tmp_path / "default_config.json"

    default_data = {
        "activeProfile": "default",
        "profiles": {"default": {}}
    }

    default_path.write_text(json.dumps(default_data))

    monkeypatch.setattr(
        config_store,
        "get_config_path",
        lambda: config_path
    )

    monkeypatch.setattr(
        config_store,
        "get_default_config_path",
        lambda: default_path
    )

    monkeypatch.setattr(
        config_store.cloud,
        "cloud_sync",
        None
    )

    return config_path


def test_create_profile_success():
    data = {"profiles": {"default": {}}}
    config_store.create_profile(data, "gaming")
    assert "gaming" in data["profiles"]


def test_create_profile_duplicate():
    data = {"profiles": {"default": {}}}
    with pytest.raises(ValueError):
        config_store.create_profile(data, "default")


def test_create_profile_empty():
    data = {"profiles": {}}
    with pytest.raises(ValueError):
        config_store.create_profile(data, "  ")


def test_delete_profile_success():
    data = {"profiles": {"default": {}}}
    config_store.delete_profile(data, "default")
    assert "default" not in data["profiles"]


def test_delete_profile_missing():
    data = {"profiles": {}}
    with pytest.raises(ValueError):
        config_store.delete_profile(data, "missing")


def test_get_mapping_str():
    profile = {"BTN:1": {"keys": ["ctrl", "a"]}}
    result = config_store.get_mapping_str(profile, "BTN:1")
    assert result == "ctrl+a"


def test_ensure_local_config_creates_file(temp_config):
    lock = threading.RLock()
    config_store.ensure_local_config_exists(lock)
    assert temp_config.exists()