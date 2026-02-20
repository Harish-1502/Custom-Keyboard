import json
import threading
import pytest
from pathlib import Path
from desktop.ble import ble_client


def test_verify_char_uuid_missing():
    class FakeServices:
        def get_characteristic(self, uuid):
            return None

    class FakeClient:
        services = FakeServices()

    with pytest.raises(RuntimeError):
        import asyncio
        asyncio.run(
            ble_client.verify_char_uuid(FakeClient(), "uuid")
        )


def test_trigger_macro(tmp_path, monkeypatch):
    config_path = tmp_path / "buttonControls.json"
    config_path.write_text(json.dumps({
        "profiles": {
            "default": {
                "BTN:1": {"keys": ["ctrl", "a"]}
            }
        }
    }))

    monkeypatch.setattr(
        ble_client,
        "get_config_path",
        lambda: config_path
    )

    calls = []

    monkeypatch.setattr(
        ble_client.pyautogui,
        "hotkey",
        lambda *keys: calls.append(keys)
    )

    ble_client.trigger_macro("BTN:1", "default", threading.RLock())
    assert calls == [("ctrl", "a")]
