import pytest
import desktop.ui.gui_host as gui_host
from desktop.ui.gui import parse_hotkey


def test_open_config_queues_open(monkeypatch):
    host = gui_host.GuiHost(file_lock=None, state={}, controller=None)

    started = {"count": 0}
    monkeypatch.setattr(host, "_ensure_started", lambda: started.__setitem__("count", started["count"] + 1))

    queued = []
    monkeypatch.setattr(host, "_q", type("Q", (), {"put": lambda self, fn: queued.append(fn)})())

    host._root = object()  # satisfy assert in _open()
    monkeypatch.setattr(gui_host, "open_config_gui", lambda *a, **k: queued.append("OPENED"))

    host.open_config()

    assert started["count"] == 1
    assert len(queued) == 1  # queued function
    # execute queued function
    queued[0]()
    assert "OPENED" in queued

def test_parse_hotkey_normalizes_and_splits():
    assert parse_hotkey("Ctrl + A") == ["ctrl", "a"]
    assert parse_hotkey("shift+alt+s") == ["shift", "alt", "s"]
    assert parse_hotkey("") == []
    assert parse_hotkey(None) == []