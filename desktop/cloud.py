from rtdb_client import get_user_config
import json
from paths import CONFIG_PATH, DEFAULT_CONFIG_PATH
from threading import RLock
from dotenv import load_dotenv
import os
from cloud_sync import CloudSync

load_dotenv()
api_key = os.getenv("API_KEY")
database_url = os.getenv("DATABASE_URL")
FIREBASE_API_KEY = api_key
FIREBASE_DB_URL  = database_url

cloud_sync = None

# Connects to firebase database
def connecting_to_db(FILE_LOCK: RLock):
    import config_store

    global cloud_sync
    try:
        if DEFAULT_CONFIG_PATH.exists():
            default_cfg = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
        else:
            default_cfg = config_store.EMBEDDED_DEFAULT_CONFIG
        
        cloud_sync = CloudSync(
                FIREBASE_API_KEY, 
                FIREBASE_DB_URL, 
                str(CONFIG_PATH), 
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
            with CONFIG_PATH.open("w", encoding="utf-8") as f:
                json.dump(full_data, f, indent = 2)
        except Exception as e:
            print("Failed to reload config:", e)