from desktop.core.paths import base_path


def test_base_path_returns_path():
    p = base_path()
    assert p.exists()
