from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent          # .../desktop/core
DESKTOP_DIR = CORE_DIR.parent                       # .../desktop
ROOT_DIR = DESKTOP_DIR.parent                       # repo root
CONFIG_DIR = DESKTOP_DIR / "config"

def get_config_path():
    return CONFIG_DIR / "buttonControls.json"

def get_default_config_path():
    return CONFIG_DIR / "default_config.json"

def get_assets_path():
    return ROOT_DIR / "assets" / "controller.png"
