import json
import asyncio
import json
import pyautogui
import firebase_admin
import pystray
import webbrowser
import os
import keyboard
import threading
import array

from PIL import Image
from firebase_admin import credentials, db
from bleak import BleakClient, BleakScanner
from dotenv import load_dotenv
from pathlib import Path

from config_store import load_prev_state
from cloud import full_reload_from_db, make_listener, connecting_to_db
from ble_client import start_ble_session, stop_ble_session

load_dotenv()
address = os.getenv("ADDRESS")
char_uuid = os.getenv("CHAR_UUID")
cred = os.getenv("CRED")
name = os.getenv("NAME")

if not address:
    raise RuntimeError("Missing ADDRESS env var (BLE MAC). Set ADDRESS=AA:BB:CC:DD:EE:FF")
if not char_uuid:
    raise RuntimeError("Missing CHAR_UUID env var (notify characteristic UUID).")

config = {}
cred = credentials.Certificate(cred)
image = Image.open("./assets/controller.png")
config_list = ["default","computer"]
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / 'config/buttonControls.json'
FILE_LOCK = threading.RLock()
BLE_TASK: asyncio.Task | None = None
BLE_CLIENT: BleakClient | None = None
BLE_STOP_EVENT: asyncio.Event | None = None
LOOP = None

# Loading previous state from shutdown
# active_profile = load_prev_state(FILE_LOCK) or "default"
state = {"activeProfile": load_prev_state(FILE_LOCK)}

# DEBUG
# print("activeProfile from recall function: ", active_profile) 

# Getting the array index from the array that the active profile is in
array_index = 0
for index,profile_name  in enumerate(config_list):
    if state["activeProfile"] == profile_name :
        array_index = index
        # print("Array index: ",array_index) 

# DEBUG
# active_profile = db.reference().get("activeProfile")
# print("Active Profile: ",active_profile)

# Kills everything
def exit_app(icon, item):
    icon.stop()
    if LOOP:
        LOOP.call_soon_threadsafe(LOOP.stop)
    os._exit(0)

# Helper function to do connect 
# def start_ble_session():
#     global BLE_TASK
#     if BLE_TASK and not BLE_TASK.done():
#         print("BLE session already running.")
#         return BLE_TASK
    
#     async def connect_wrapper():
#         await asyncio.sleep(0.5)
#         await connect(name, char_uuid, BLE_CLIENT, BLE_STOP_EVENT, BLE_TASK, active_profile, FILE_LOCK)

#     BLE_TASK = LOOP.create_task(connect_wrapper())
#     return BLE_TASK

# Helper function to disconnect 
# def stop_ble_session():
#     global BLE_TASK,BLE_STOP_EVENT
#     if BLE_STOP_EVENT and not BLE_STOP_EVENT.is_set():
#         BLE_STOP_EVENT.set()
#         # BLE_TASK.cancel()
#         print("Requesting BLE session cancel...")
#         return
#     # BLE_TASK = None
    
#     print("No BLE session to cancel.")

# Used in pystray menu to connect. For pystray, the method used in its menu has to be sync
def tray_connect(*_):
    # called from tray thread → schedule work on asyncio loop
    print("Connecting to device")
    LOOP.call_soon_threadsafe(lambda: start_ble_session(name, FILE_LOCK, state, LOOP))

# Used in pystray menu to disconnect
def tray_disconnect(*_):
    print("Disconnecting from the device")
    LOOP.call_soon_threadsafe(stop_ble_session)

# Goes to the database website
def open_website(icon, item):
    webbrowser.open("https://macro-controller-default-rtdb.firebaseio.com/")
    
# Changes the active profile in the local json file    
def set_state(new_profile: str):
    with FILE_LOCK:
        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {}
    
        data["activeProfile"] = new_profile
        
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
    db.reference("/").update({f"activeProfile": new_profile})

# Used to change the active profile 
def change_profile(step):
    global array_index,state

    n = len(config_list)
    if n == 0:
        print("No profiles available")
        return
    array_index = (array_index + step) % n
    new_active_profile = config_list[array_index]

    print(f"currently in {new_active_profile} mode")
    set_state(new_active_profile)
    state["activeProfile"] = new_active_profile
    db.reference(f"profiles/{new_active_profile}").listen(make_listener(new_active_profile, FILE_LOCK))

# Increment the active profile in the config list array
def increment_array_index(*_):
    change_profile(1)
    
# Creates all the right-click actions on the icon
menu = pystray.Menu(
    pystray.MenuItem("Open DB", open_website),
    pystray.MenuItem("Refresh json", lambda *_: full_reload_from_db(FILE_LOCK)),
    pystray.MenuItem("Change profile", increment_array_index),
    pystray.MenuItem("Connect BLE", tray_connect),
    pystray.MenuItem("Disconnect BLE", tray_disconnect),
    pystray.MenuItem("Exit", exit_app)
)

# Creates the icon on the tray menu
icon = pystray.Icon("MacroPad", image, "Macro Controller", menu)

# Used to run the forever loop and will gracefully close everything
def run_event_loop_forever():
    global LOOP,address, char_uuid
    LOOP = asyncio.new_event_loop()          # 1) make a brand-new event loop
    asyncio.set_event_loop(LOOP)             # 2) mark it as “the current loop” in this thread
    try:
        LOOP.call_soon(lambda: start_ble_session("Macropad", FILE_LOCK, state, LOOP))  # 3) schedule your BLE task
        LOOP.run_forever()                   # 3) BLOCK here and keep the loop alive
    finally:
        stop_ble_session()                   # 4) if we’re stopping, cancel your BLE task
        pending = asyncio.all_tasks(LOOP)    # 5) grab any other pending tasks on this loop
        for t in pending: t.cancel()         # 6) ask them to cancel
        LOOP.run_until_complete(             # 7) let them finish cleanup
            asyncio.gather(*pending, return_exceptions=True)
        )
        LOOP.close()                         # 8) close the loop cleanly
        
connecting_to_db(state["activeProfile"],FILE_LOCK)
threading.Thread(target=icon.run, daemon=True).start()
run_event_loop_forever()