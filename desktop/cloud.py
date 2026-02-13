from rtdb_client import get_user_config
# from firebase_admin import db
import json
from paths import CONFIG_PATH, DEFAULT_CONFIG_PATH
from threading import RLock
# import firebase_admin
# from firebase_admin import credentials
from dotenv import load_dotenv
import os
from session_manager import SessionManager
from cloud_sync import CloudSync

load_dotenv()
# db_url_path = os.getenv("DB_URL")
# cred = os.getenv("CRED")
api_key = os.getenv("API_KEY")
database_url = os.getenv("DATABASE_URL")
# print("DB URL:",db_url_path)
# cred = credentials.Certificate(cred)
FIREBASE_API_KEY = api_key
FIREBASE_DB_URL  = database_url

cloud_sync = None

# Connects to firebase database
def connecting_to_db(active_profile: str, FILE_LOCK: RLock):
    # print("Calling from cloud.py connecting_to_db")
    # try:
    #     firebase_admin.initialize_app(cred,{
    #         "databaseURL" : "https://macro-controller-default-rtdb.firebaseio.com/"
    #     })
    #     full_reload_from_db(FILE_LOCK)
    #     # Listens for changes in a specific profile
    #     db.reference(f"profiles/{active_profile}").listen(make_listener(active_profile, FILE_LOCK))

    # except BaseException:
    #     print("Can't connect to DB. Try again later")

    global cloud_sync
    try:
        cloud_sync = CloudSync(FIREBASE_API_KEY, FIREBASE_DB_URL, str(CONFIG_PATH), FILE_LOCK, default_config=json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8")))
        cloud_sync.connect()
        print("Connected to cloud and synced config.")
    except Exception as e:
        print("Failed to connect to cloud:", e)
        cloud_sync = None

# def backup_db():
#     # print("Backing up DB...")
#     uid = session.get_uid()
#     id_token = session.get_id_token()
#     config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
#     set_profiles(rtdb, uid, id_token, config.get("profiles") or {})
#     # print("Backup complete.")
        
# Handles real-time database changes in the json and then it calls the full_reload function when a change occurs
# def make_listener(active_profile: str, FILE_LOCK: RLock):
#     def _listener(event):
#         print("Listening function is called")
#         data = event.data
#         if data:
#             partial_reload_from_db(active_profile, FILE_LOCK)
#         else:
#             print("Listening function failed")
#     return _listener


#  Replaces the current json file in the project with the json from the database
def full_reload_from_db(FILE_LOCK: RLock):
    # full_data = db.reference().get()
    full_data = get_user_config(cloud_sync.rtdb, cloud_sync.uid, cloud_sync.id_token)
    # print("Called from cloud.py full reload")
    # print("Full data: ",full_data)
    with FILE_LOCK:
        try:
            with CONFIG_PATH.open("w", encoding="utf-8") as f:
                json.dump(full_data, f, indent = 2)
        except Exception as e:
            print("Failed to reload config:", e)

# Loads only part of the json file. It's used in the listener function to copy changes in the DB only related to the active profile's macros(Won't be needed anymore since it will be replaced by the full reload function) 
# def partial_reload_from_db(active_profile: str, FILE_LOCK: RLock):
#     new_subtree = db.reference(f"profiles/{active_profile}").get()
#     # print("SubTree: ",sub_tree)
#     # print("Called from cloud.py partial reload")
#     with FILE_LOCK:
#         try:
#             with CONFIG_PATH.open("r", encoding="utf-8") as f:
#                 full_data = json.load(f) or {}
#         except Exception as e:
#             print("Failed to reload config:", e)
        
#         # DEBUG
#         # print(full_data)
#         local_path = ["profiles", active_profile]
        
#         current_branch = full_data
#         for step in local_path[:-1]:
#             current_branch = current_branch[step]
        
#         current_branch[local_path[-1]] = new_subtree
        
#         # DEBUG
#         # print("Full data: ",full_data)
        
#         with CONFIG_PATH.open("w", encoding="utf-8") as f:
#             json.dump(full_data, f, indent = 2)