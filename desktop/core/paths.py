import sys
import os
from pathlib import Path

from desktop.cloud.auth_client import appdata_dir

# APP_NAME = "CustomKeyboard"

# --------------------------------------------------
# Base path (works in dev + PyInstaller)
# --------------------------------------------------

def base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent

# --------------------------------------------------
# Bundled assets (read-only)
# --------------------------------------------------

def get_default_config_path() -> Path:
    return base_path() / "config" / "default_config.json"

def get_assets_path() -> Path:
    return base_path().parent / "assets" / "controller.png"

# --------------------------------------------------
# User data (writable)
# --------------------------------------------------

def get_config_path() -> Path:
    return appdata_dir() / "buttonControls.json"

# DEBUGGING: Print paths to verify correctness
# print("Config path:", get_config_path())
# print("Default config path:", get_default_config_path())
# print("Assets path:", get_assets_path())
# print("Appdata dir:", appdata_dir())
# print("Base path:", base_path())