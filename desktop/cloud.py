from firebase_admin import db
import json
from paths import CONFIG_PATH
from threading import RLock
import firebase_admin
from firebase_admin import credentials
from dotenv import load_dotenv
import os

load_dotenv()
db_url_path = os.getenv("DB_URL")
cred = os.getenv("CRED")
# print("DB URL:",db_url_path)
cred = credentials.Certificate(cred)

# Connects to firebase database
def connecting_to_db(active_profile: str, FILE_LOCK: RLock):
    # print("Calling from cloud.py connecting_to_db")
    try:
        firebase_admin.initialize_app(cred,{
            "databaseURL" : "https://macro-controller-default-rtdb.firebaseio.com/"
        })
        full_reload_from_db(FILE_LOCK)
        # Listens for changes in a specific profile
        db.reference(f"profiles/{active_profile}").listen(make_listener(active_profile, FILE_LOCK))

    except BaseException:
        print("Can't connect to DB. Try again later")
        
# Handles real-time database changes in the json and then it calls the full_reload function when a change occurs
def make_listener(active_profile: str, FILE_LOCK: RLock):
    def _listener(event):
        print("Listening function is called")
        data = event.data
        if data:
            partial_reload_from_db(active_profile, FILE_LOCK)
        else:
            print("Listening function failed")
    return _listener


#  Replaces the current json file in the project with the json from the database
def full_reload_from_db(FILE_LOCK: RLock):
    full_data = db.reference().get()
    # print("Called from cloud.py full reload")
    # print("Full data: ",full_data)
    with FILE_LOCK:
        try:
            with CONFIG_PATH.open("w", encoding="utf-8") as f:
                json.dump(full_data, f, indent = 2)
        except Exception as e:
            print("Failed to reload config:", e)

# Loads only part of the json file. It's used in the listener function to copy changes in the DB only related to the active profile's macros 
def partial_reload_from_db(active_profile: str, FILE_LOCK: RLock):
    new_subtree = db.reference(f"profiles/{active_profile}").get()
    # print("SubTree: ",sub_tree)
    # print("Called from cloud.py partial reload")
    with FILE_LOCK:
        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as f:
                full_data = json.load(f) or {}
        except Exception as e:
            print("Failed to reload config:", e)
        
        # DEBUG
        # print(full_data)
        local_path = ["profiles", active_profile]
        
        current_branch = full_data
        for step in local_path[:-1]:
            current_branch = current_branch[step]
        
        current_branch[local_path[-1]] = new_subtree
        
        # DEBUG
        # print("Full data: ",full_data)
        
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(full_data, f, indent = 2)