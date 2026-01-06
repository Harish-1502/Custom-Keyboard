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
from cloud import full_reload_from_db, partial_reload_from_db, make_listener, connecting_to_db
from ble_client import verify_char_uuid, find_device_address_by_name, connect,trigger_macro

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
active_profile = load_prev_state(FILE_LOCK) or "default"

# DEBUG
# print("activeProfile from recall function: ", active_profile) 

# Getting the array index from the array that the active profile is in
for index,config in enumerate(config_list):
    if active_profile == config:
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
def start_ble_session():
    global BLE_TASK
    if BLE_TASK and not BLE_TASK.done():
        print("BLE session already running.")
        return BLE_TASK
    
    async def connect_wrapper():
        await asyncio.sleep(0.5)
        await connect(name, char_uuid, BLE_CLIENT, BLE_STOP_EVENT, BLE_TASK, active_profile, FILE_LOCK)

    BLE_TASK = LOOP.create_task(connect_wrapper())
    return BLE_TASK

# Helper function to disconnect 
def stop_ble_session():
    global BLE_TASK,BLE_STOP_EVENT
    if BLE_STOP_EVENT and not BLE_STOP_EVENT.is_set():
        BLE_STOP_EVENT.set()
        # BLE_TASK.cancel()
        print("Requesting BLE session cancel...")
        return
    # BLE_TASK = None
    
    print("No BLE session to cancel.")

# Used in pystray menu to connect. For pystray, the method used in its menu has to be sync
def tray_connect(*_):
    # called from tray thread → schedule work on asyncio loop
    print("Connecting to device")
    LOOP.call_soon_threadsafe(start_ble_session)

# Used in pystray menu to disconnect
def tray_disconnect(*_):
    print("Disconnecting from the device")
    LOOP.call_soon_threadsafe(stop_ble_session)

# Goes to the database website
def open_website(icon, item):
    webbrowser.open("https://macro-controller-default-rtdb.firebaseio.com/")
    
# Changes the active profile in the local json file    
def set_active_profile(new_profile: str):
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
    global array_index,active_profile
    n = len(config_list)
    if n == 0:
        print("No profiles available")
        return
    array_index = (array_index + step) % n
    active_profile = config_list[array_index]
    print(f"currently in {active_profile} mode")
    set_active_profile(active_profile)
    db.reference(f"profiles/{active_profile}").listen(make_listener(active_profile, FILE_LOCK))

# Increment the active profile in the config list array
def increment_array_index(*_):
    change_profile(1)
    
# Creates all the right-click actions on the icon
menu = pystray.Menu(
    pystray.MenuItem("Open DB", open_website),
    pystray.MenuItem("Refresh json", full_reload_from_db),
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
        LOOP.call_soon(start_ble_session)
        LOOP.run_forever()                   # 3) BLOCK here and keep the loop alive
    finally:
        stop_ble_session()                   # 4) if we’re stopping, cancel your BLE task
        pending = asyncio.all_tasks(LOOP)    # 5) grab any other pending tasks on this loop
        for t in pending: t.cancel()         # 6) ask them to cancel
        LOOP.run_until_complete(             # 7) let them finish cleanup
            asyncio.gather(*pending, return_exceptions=True)
        )
        LOOP.close()                         # 8) close the loop cleanly
        
connecting_to_db(active_profile,FILE_LOCK)
threading.Thread(target=icon.run, daemon=True).start()
run_event_loop_forever()