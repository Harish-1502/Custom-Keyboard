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
from bleak import BleakClient
from dotenv import load_dotenv

load_dotenv()
address = os.getenv("ADDRESS")
char_uuid = os.getenv("CHAR_UUID")

if not address:
    raise RuntimeError("Missing ADDRESS env var (BLE MAC). Set ADDRESS=AA:BB:CC:DD:EE:FF")
if not char_uuid:
    raise RuntimeError("Missing CHAR_UUID env var (notify characteristic UUID).")

config = {}
cred = credentials.Certificate("./macro-controller-firebase-adminsdk-fbsvc-744d7fc317.json")
image = Image.open("./controller.png")
config_list = ["default","computer"]
FILE_LOCK = threading.RLock()
BLE_TASK = None
LOOP = None

# Load the active profile before closing the program
def load_prev_state():
    with FILE_LOCK:
        with open("buttonControls.json", "r") as f:
            temp_config = json.load(f)
    return temp_config.get("activeProfile")

active_profile = load_prev_state()
# print("activeProfile from recall function: ", active_profile) ----DEBUG
# Getting the array index from the array that the active profile is in
for index,config in enumerate(config_list):
    if active_profile == config:
        array_index = index
        # print("Array index: ",array_index) 

# active_profile = db.reference().get("activeProfile")
# print("Active Profile: ",active_profile)

# Kills everything
def exit_app(icon, item):
    icon.stop()
    if LOOP:
        LOOP.call_soon_threadsafe(LOOP.stop)
    os._exit(0)

#  Replaces the current json file in the project with the json from the database
def full_reload_from_db():
    full_data = db.reference().get()
    # print("Full data: ",full_data)
    with FILE_LOCK:
        try:
            with open("buttonControls.json","w") as f:
                json.dump(full_data, f, indent = 2)
        except Exception as e:
            print("Failed to reload config:", e)

# Loads only part of the json file. It's used in the listener function to copy changes in the DB only related to the active profile's macros 
def partial_reload_from_db(active_profile: str):
    new_subtree = db.reference(f"profiles/{active_profile}").get()
    # print("SubTree: ",sub_tree)
    with FILE_LOCK:
        try:
            with open("buttonControls.json","r") as f:
                full_data = json.load(f) or {}
        except Exception as e:
            print("Failed to reload config:", e)
        
        # print(full_data)
        local_path = ["profiles", active_profile]
        
        current_branch = full_data
        for step in local_path[:-1]:
            current_branch = current_branch[step]
        
        current_branch[local_path[-1]] = new_subtree
        
        # print("Full data: ",full_data)
        
        with open("buttonControls.json","w") as f:
            json.dump(full_data, f, indent = 2)
        
# Connects to firebase database
def connecting_to_db():
    try:
        firebase_admin.initialize_app(cred,{
            "databaseURL" : "https://macro-controller-default-rtdb.firebaseio.com/"
        })
        full_reload_from_db()
        # Easier to debug partial from here
        # partial_reload_from_db(active_profile)
        # Listens for changes in a specific profile
        db.reference(f"profiles/{active_profile}").listen(listener)    
    except BaseException:
        print("Can't connect to DB. Try again later")
    

# Handles real-time database changes in the json and then it calls the full_reload function when a change occurs
def listener(event):
    print("Listening function is called")
    # print("Raw event: ",event)
    data = event.data
    # print("Processed event: ",data)
    if(data):
        try:
            print("Writing from database into json file")
            partial_reload_from_db(active_profile)
        except Exception as e:
            print("Failed to update config from full reload:", e)     
    else:
        print("Listening function failed")

     
# Reads buttonControls.json, gets the button_id and profile, finds the action and executes it
def trigger_macro(button_id, profile):
    with FILE_LOCK:
        with open("buttonControls.json", "r") as f:
            config_file = json.load(f)
    action = config_file.get("profiles",{}).get(profile).get(button_id)
    print(action)
    if action:
        keys = action.get("keys")
        if keys:
            print(f"Triggering {button_id}: printing {keys}")
            pyautogui.hotkey(*keys)
        else:
            print("keys is undefined")
    else:
        print("No action was mapped for this button")

#Verifies if there is a characteristic uuid and what properties it has so it prevents the "it's connected but nothing happens" error 
async def verify_char_uuid(client, char_uuid: str):
    service = client.services or await client.get_services()
    ch_uuid = service.get_characteristic(char_uuid)
    if not ch_uuid:
        raise RuntimeError(f"Characteristic {char_uuid} not found on device.")

    props = getattr(ch_uuid, "properties", []) or []
    if "notify" not in props:
        raise RuntimeError(f"Characteristic {char_uuid} is not notifiable. Props: {props}")

    print(f"GATT OK → found {char_uuid} with properties {props}")
            
# Gets the button ID and activates the trigger_macro function
async def handle_notification(sender,data):
    msg = data.decode("utf-8").strip()
    print(f"Received {msg}")
    trigger_macro(msg,active_profile)

# Used to initiate the device connection and BLE connection
async def connect(address:str, char_uuid:str):
    try:
        async with BleakClient(address, timeout = 20.0) as client:
            print("Connected to ESP32 Macro Pad!")
            await verify_char_uuid(client, char_uuid)
            await client.start_notify(char_uuid, handle_notification)
            print("Listening for notifications...")
            # await asyncio.sleep(99999)  # Keeps the program running
            disc = asyncio.Event()
            client.set_disconnected_callback(lambda _: disc.set())
            await disc.wait()
            print("BLE disconnected (session ended).")
    except Exception as e:
        print("BLE session error:", e)

# Helper function to do connect 
def start_ble_session():
    global BLE_TASK
    if BLE_TASK and not BLE_TASK.done():
        print("BLE session already running.")
        return BLE_TASK
    BLE_TASK = LOOP.create_task(connect(address, char_uuid))
    return BLE_TASK

# Helper function to disconnect 
def stop_ble_session():
    global BLE_TASK
    if BLE_TASK and not BLE_TASK.done():
        BLE_TASK.cancel()
        print("Cancelling BLE session...")
    BLE_TASK = None

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
            with open("./buttonControls.json","r",encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {}
    
        data["activeProfile"] = new_profile
        
        with open("./buttonControls.json","w",encoding="utf-8") as f:
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
    db.reference(f"profiles/{active_profile}").listen(listener)    

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
        
connecting_to_db()
threading.Thread(target=icon.run, daemon=True).start()
run_event_loop_forever()