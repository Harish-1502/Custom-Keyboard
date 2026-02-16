import json
from paths import CONFIG_PATH, DEFAULT_CONFIG_PATH
from threading import RLock
from rtdb_client import RTDBClient, set_profiles, set_active_profile
from auth_client import ensure_logged_in
import cloud

EMBEDDED_DEFAULT_CONFIG = {
    "activeProfile": "default",
    "profiles": {
        "default": {}
    }
}

# # Load the active profile before closing the program
def load_prev_state(file_lock: RLock) -> str | None:
    with file_lock:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            temp_config = json.load(f)
    return temp_config.get("activeProfile")

def load_config(file_lock):

    ensure_local_config_exists(file_lock)
    
    with file_lock:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
        
def save_config(file_lock, data, cloud_sync=cloud.cloud_sync, prof: str | None = None):

    ensure_local_config_exists(file_lock)

    with file_lock:
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
    if cloud_sync:
        try:
            cloud.cloud_sync.backup_config(data)
            # set_active_profile(cloud_sync.rtdb, cloud_sync.uid, cloud_sync.id_token, prof or data.get("activeProfile"))
        except Exception as e:
            print("Cloud backup failed:", e)

def get_mapping_str(profile_data: dict, button_id: str) -> str:
    """
    Returns human-friendly mapping like "ctrl+a" or "" if missing.
    Expects JSON structure: profiles[profile][button_id] = {"keys": ["ctrl","a"]}
    """
    action = (profile_data or {}).get(button_id) or {}
    keys = action.get("keys") or []
    return "+".join(keys)


def set_mapping(profile_data: dict, button_id: str, keys: list[str]):
    profile_data.setdefault(button_id, {})
    profile_data[button_id]["keys"] = keys

def get_profiles(data) -> list[str]:
    return list((data.get("profiles") or {}).keys())

def create_profile(data: dict, profile_name: str, template_profile: str | None = None):
    profiles = data.setdefault("profiles", {})
    name = profile_name.strip()
    if not name:
        raise ValueError("Profile name is empty.")
    if name in profiles:
        raise ValueError("Profile already exists.")

    if template_profile and template_profile in profiles:
        profiles[name] = json.loads(json.dumps(profiles[template_profile]))  # deep copy
    else:
        profiles[name] = {}  # empty profile

def delete_profile(data: dict, profile_name: str):
    profiles = data.get("profiles") or {}
    if profile_name not in profiles:
        raise ValueError("Profile not found.")
    del profiles[profile_name]

def ensure_local_config_exists(file_lock):

    with file_lock:
        if CONFIG_PATH.exists():
            return

    # Try to restore from cloud if available
    if cloud.cloud_sync:
        try:
            restored = cloud.cloud_sync.restore_to_local_if_possible()
            if restored:
                return
        except Exception as e:
            print("Cloud restore failed:", e)

    # Fallback: create defaults locally
    if DEFAULT_CONFIG_PATH.exists():
        try:
            default_config = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            print("Default config file is unreadable, using embedded defaults:", e)
            default_config = EMBEDDED_DEFAULT_CONFIG
    else:
        print("Default config file missing, using embedded defaults.")
        default_config = EMBEDDED_DEFAULT_CONFIG

    # 4) Write local config
    with file_lock:
        CONFIG_PATH.write_text(json.dumps(default_config, indent=2), encoding="utf-8")

    # 5) Optional: seed cloud so future restores work
    if cloud.cloud_sync:
        try:
            cloud.cloud_sync.backup_config(default_config)
        except Exception as e:
            print("Cloud seed failed:", e)

    print("Local config created.")