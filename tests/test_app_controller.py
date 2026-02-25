import json
import threading
from pathlib import Path
import pytest

import desktop.ui.app_controller as app_controller


class FakeLoop:
    def __init__(self):
        self.calls = []

    def call_soon_threadsafe(self, fn):
        self.calls.append(("call_soon_threadsafe", fn))
        # We do NOT auto-run the callback; tests can choose to run it.

    def create_task(self, coro):
        self.calls.append(("create_task", coro))
        return "TASK"


class FakeIcon:
    def __init__(self):
        self.title = ""
        self.notifications = []

    def notify(self, msg, title):
        self.notifications.append((title, msg))

    def stop(self):
        self.stopped = True


def test_apply_tray_title_sets_connected_or_disconnected():
    loop = FakeLoop()
    lock = threading.RLock()
    state = {"connected": False, "activeProfile": "default"}
    app = app_controller.AppController(
        loop, lock, state,
        config_list=["default", "computer"],
        device_name="X", char_uuid="Y",
        start_ble_session=lambda *a, **k: None,
        stop_ble_session=lambda *a, **k: None,
        full_reload_from_db=lambda *a, **k: None,
        connecting_to_db=lambda *a, **k: None,
        array_index=0
    )

    icon = FakeIcon()
    app.set_icon(icon)
    assert "Disconnected" in icon.title

    state["connected"] = True
    app.apply_tray_title()
    assert "Connected" in icon.title


def test_notify_calls_icon_notify_and_updates_title():
    loop = FakeLoop()
    lock = threading.RLock()
    state = {"connected": True, "activeProfile": "default"}
    app = app_controller.AppController(
        loop, lock, state,
        ["default"], "X", "Y",
        start_ble_session=lambda *a, **k: None,
        stop_ble_session=lambda *a, **k: None,
        full_reload_from_db=lambda *a, **k: None,
        connecting_to_db=lambda *a, **k: None,
        array_index=0
    )

    icon = FakeIcon()
    app.set_icon(icon)

    app.notify("Hello")
    assert icon.notifications == [("Custom Keyboard", "Hello")]
    assert "Connected" in icon.title


def test_tray_connect_schedules_start_ble_session():
    called = {"args": None}

    def fake_start(name, lock, state, loop, **kwargs):
        called["args"] = (name, lock, state, loop, kwargs)

    loop = FakeLoop()
    lock = threading.RLock()
    state = {"connected": False, "activeProfile": "default"}
    app = app_controller.AppController(
        loop, lock, state, ["default"], "DevName", "UUID",
        start_ble_session=fake_start,
        stop_ble_session=lambda *a, **k: None,
        full_reload_from_db=lambda *a, **k: None,
        connecting_to_db=lambda *a, **k: None,
        array_index=0
    )

    app.tray_connect()

    assert loop.calls and loop.calls[0][0] == "call_soon_threadsafe"
    # Run the scheduled callback
    loop.calls[0][1]()
    assert called["args"][0] == "DevName"
    assert "on_connected" in called["args"][4]
    assert "on_disconnected" in called["args"][4]
    assert "on_error" in called["args"][4]


def test_tray_disconnect_schedules_stop_ble_session():
    called = {"stop": 0}

    def fake_stop():
        called["stop"] += 1

    loop = FakeLoop()
    lock = threading.RLock()
    state = {"connected": True, "activeProfile": "default"}
    app = app_controller.AppController(
        loop, lock, state, ["default"], "X", "Y",
        start_ble_session=lambda *a, **k: None,
        stop_ble_session=fake_stop,
        full_reload_from_db=lambda *a, **k: None,
        connecting_to_db=lambda *a, **k: None,
        array_index=0
    )

    app.tray_disconnect()
    assert loop.calls[0][0] == "call_soon_threadsafe"
    loop.calls[0][1]()  # execute scheduled stop
    assert called["stop"] == 1


def test_ble_handlers_update_state_and_notify(monkeypatch):
    loop = FakeLoop()
    lock = threading.RLock()
    state = {"connected": False, "activeProfile": "default"}
    app = app_controller.AppController(
        loop, lock, state, ["default"], "X", "Y",
        start_ble_session=lambda *a, **k: None,
        stop_ble_session=lambda *a, **k: None,
        full_reload_from_db=lambda *a, **k: None,
        connecting_to_db=lambda *a, **k: None,
        array_index=0
    )

    icon = FakeIcon()
    app.set_icon(icon)

    app.on_ble_connected()
    assert state["connected"] is True
    assert ("Custom Keyboard", "Device connected") in icon.notifications

    app.on_ble_disconnected()
    assert state["connected"] is False
    assert ("Custom Keyboard", "Device disconnected") in icon.notifications


def test_change_profile_wraps_and_calls_set_state(monkeypatch):
    loop = FakeLoop()
    lock = threading.RLock()
    state = {"connected": False, "activeProfile": "default"}

    app = app_controller.AppController(
        loop, lock, state, ["default", "computer"], "X", "Y",
        start_ble_session=lambda *a, **k: None,
        stop_ble_session=lambda *a, **k: None,
        full_reload_from_db=lambda *a, **k: None,
        connecting_to_db=lambda *a, **k: None,
        array_index=0
    )

    called = []
    monkeypatch.setattr(app, "set_state", lambda prof: called.append(prof))

    app.change_profile(step=1)
    assert app.array_index == 1
    assert state["activeProfile"] == "computer"
    assert called == ["computer"]

    app.change_profile(step=1)
    assert state["activeProfile"] == "default"   # wrap
    assert called[-1] == "default"


def test_set_state_writes_json_and_calls_cloud(monkeypatch, tmp_path):
    loop = FakeLoop()
    lock = threading.RLock()
    state = {"connected": False, "activeProfile": "default"}
    app = app_controller.AppController(
        loop, lock, state, ["default"], "X", "Y",
        start_ble_session=lambda *a, **k: None,
        stop_ble_session=lambda *a, **k: None,
        full_reload_from_db=lambda *a, **k: None,
        connecting_to_db=lambda *a, **k: None,
        array_index=0
    )

    # Patch config path
    cfg_path = tmp_path / "buttonControls.json"
    monkeypatch.setattr(app_controller, "get_config_path", lambda: cfg_path)

    # Patch set_active_profile call + cloud.cloud_sync
    calls = []
    monkeypatch.setattr(app_controller, "set_active_profile", lambda rtdb, uid, token, prof: calls.append((uid, prof)))

    class FakeCloudSync:
        rtdb = object()
        uid = "UID"
        id_token = "TOKEN"

    monkeypatch.setattr(app_controller.cloud, "cloud_sync", FakeCloudSync())

    app.set_state("computer")

    saved = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert saved["activeProfile"] == "computer"
    assert calls == [("UID", "computer")]

def test_set_state_does_not_crash_when_cloud_sync_missing(monkeypatch, tmp_path):
    import desktop.ui.app_controller as app_controller
    import threading, json

    loop = FakeLoop()
    lock = threading.RLock()
    state = {"activeProfile": "default"}
    app = app_controller.AppController(loop, lock, state, ["default"], "X", "Y",
                                       lambda *a, **k: None, lambda *a, **k: None,
                                       lambda *a, **k: None, lambda *a, **k: None, 0)

    monkeypatch.setattr(app_controller, "get_config_path", lambda: tmp_path / "buttonControls.json")
    monkeypatch.setattr(app_controller.cloud, "cloud_sync", None)

    # Right now this will likely crash unless you guard it.
    app.set_state("default")