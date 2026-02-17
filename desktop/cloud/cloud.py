from desktop.cloud.rtdb_client import get_user_config
import json
from desktop.core.paths import get_config_path, get_default_config_path
from threading import RLock
from dotenv import load_dotenv
import os
from desktop.cloud.cloud_sync import CloudSync

load_dotenv()
api_key = os.getenv("API_KEY")
database_url = os.getenv("DATABASE_URL")
FIREBASE_API_KEY = api_key
FIREBASE_DB_URL  = database_url

cloud_sync = None

# Connects to firebase database
def connecting_to_db(FILE_LOCK: RLock):
    import desktop.core.config_store as config_store

    global cloud_sync
    try:
        if get_default_config_path().exists():
            default_cfg = json.loads(get_default_config_path().read_text(encoding="utf-8"))
        else:
            default_cfg = config_store.EMBEDDED_DEFAULT_CONFIG
        
        cloud_sync = CloudSync(
                FIREBASE_API_KEY, 
                FIREBASE_DB_URL, 
                str(get_config_path()), 
                FILE_LOCK, 
                default_config=default_cfg)
        
        cloud_sync.connect()
        print("Connected to cloud and synced config.")
    except Exception as e:
        print("Failed to connect to cloud:", e)
        cloud_sync = None

#  Replaces the current json file in the project with the json from the database
def full_reload_from_db(FILE_LOCK: RLock):
    full_data = get_user_config(cloud_sync.rtdb, cloud_sync.uid, cloud_sync.id_token)

    with FILE_LOCK:
        try:
            with get_config_path().open("w", encoding="utf-8") as f:
                json.dump(full_data, f, indent = 2)
        except Exception as e:
            print("Failed to reload config:", e)