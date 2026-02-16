from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent          # .../desktop/core
DESKTOP_DIR = CORE_DIR.parent                       # .../desktop
ROOT_DIR = DESKTOP_DIR.parent                       # repo root

CONFIG_DIR = DESKTOP_DIR / "config"
CONFIG_PATH = CONFIG_DIR / "buttonControls.json"
DEFAULT_CONFIG_PATH = CONFIG_DIR / "default_config.json"

ASSETS_PATH = ROOT_DIR / "assets" / "controller.png"
