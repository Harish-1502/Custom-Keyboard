import json
from cloud_sync import CloudSync
from paths import CONFIG_PATH
from threading import RLock
from rtdb_client import RTDBClient, set_profiles, set_active_profile
from auth_client import ensure_logged_in

# # Load the active profile before closing the program
def load_prev_state(FILE_LOCK: RLock) -> str | None:
    with FILE_LOCK:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            temp_config = json.load(f)
    return temp_config.get("activeProfile")

def load_config(file_lock):
    with file_lock:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
        
def save_config(file_lock, data, cloud_sync=CloudSync, prof=str):
    with file_lock:
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
    if cloud_sync:
        try:
            cloud_sync.backup_config(data)
            set_active_profile(cloud_sync.rtdb, cloud_sync.uid, cloud_sync.id_token, prof or data.get("activeProfile"))
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

# config_store.py

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
