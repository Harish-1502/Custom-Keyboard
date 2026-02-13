from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

CONFIG_PATH = BASE_DIR / 'config/buttonControls.json'
ASSETS_PATH = ROOT_DIR / 'assets/controller.png'

DEFAULT_CONFIG_PATH = BASE_DIR / 'config/default_config.json'