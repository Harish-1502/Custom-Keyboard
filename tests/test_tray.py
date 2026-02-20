import desktop.ui.tray as tray


def test_build_tray_calls_image_open(monkeypatch):
    opened = {"path": None}

    monkeypatch.setattr(tray, "get_assets_path", lambda: "X/controller.png")

    class FakeImage:
        pass

    monkeypatch.setattr(tray.Image, "open", lambda p: opened.__setitem__("path", p) or FakeImage())

    # Fake pystray structures
    class FakeMenuItem:
        def __init__(self, text, action):
            self.text = text
            self.action = action

    class FakeMenu:
        def __init__(self, *items):
            self.items = items

    class FakeIcon:
        def __init__(self, name, image, title, menu):
            self.name = name
            self.image = image
            self.title = title
            self.menu = menu

    monkeypatch.setattr(tray.pystray, "MenuItem", FakeMenuItem)
    monkeypatch.setattr(tray.pystray, "Menu", FakeMenu)
    monkeypatch.setattr(tray.pystray, "Icon", FakeIcon)

    class FakeApp:
        def open_website(self, *_): pass
        def tray_sign_in(self, *_): pass
        def open_gui(self, *_): pass
        def refresh_json(self, *_): pass
        def change_profile(self, *_ , **__): pass
        def tray_connect(self, *_): pass
        def tray_disconnect(self, *_): pass
        def exit_app(self, *_): pass
        FILE_LOCK = None

    icon = tray.build_tray(FakeApp())
    assert opened["path"] == "X/controller.png"
    assert icon.title == "Macro Controller"
    assert len(icon.menu.items) == 8