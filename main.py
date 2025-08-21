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

# Connects to firebase database
firebase_admin.initialize_app(cred,{
    "databaseURL" : "https://macro-controller-default-rtdb.firebaseio.com/"
})

# Kills everything
def exit_app(icon, item):
    icon.stop()
    os._exit(0)

#  Replaces the current json file in the project with the json from the database
# TODO: change that to dump 1 profile 
def full_reload():
    full_data = db.reference().get()
    # print("Full data: ",full_data)
    try:
        with open("buttonControls.json","w") as f:
            json.dump(full_data, f, indent = 2)
    except Exception as e:
        print("Failed to reload config:", e) 

# Handles real-time database changes in the json and then it calls the full_reload function when a change occurs
def listener(event):
    print("Listening function is called")
    # print("Raw event: ",event)
    data = event.data
    # print("Processed event: ",data)
    if(data):
        try:
            print("Writing from database into json file")
            full_reload()
        except Exception as e:
            print("Failed to update config from full reload:", e)     
    else:
        print("Listening function failed")

# Listens for changes in a specific profile
db.reference("computer").listen(listener)

# Reads buttonControls.json, gets the button_id and profile, finds the action and executes it
#TODO: use a lock for file reading if multiple buttons are pushed
def trigger_macro(button_id, profile):
    with open("buttonControls.json", "r") as f:
        config_file = json.load(f)
    action = config_file.get(profile,{}).get(button_id)
    # print(action)
    if action:
        keys = action.get("keys")
        if keys:
            print(f"Triggering {button_id}: printing {keys}")
            pyautogui.hotkey(*keys)
        else:
            print("keys is undefined")
    else:
        print("No action was mapped for this button")
            
# Gets the button ID and activates the trigger_macro function
async def handle_notification(sender,data):
    msg = data.decode("utf-8").strip()
    print(f"Received {msg}")
    trigger_macro(msg)

async def main(address):
    async with BleakClient(address, timeout = 20.0) as client:
        print("Connected to ESP32 Macro Pad!")
        await client.start_notify(char_uuid, handle_notification)
        print("Listening for notifications...")
        await asyncio.sleep(99999)  # Keeps the program running

# Goes to the database website
def open_website(icon, item):
    webbrowser.open("https://macro-controller-default-rtdb.firebaseio.com/")

# Creates all the right-click actions on the icon
menu = pystray.Menu(
    pystray.MenuItem("Open DB", open_website),
    pystray.MenuItem("Exit", exit_app)
)
# Creates the icon on the tray menu
icon = pystray.Icon("MacroPad", image, "Macro Controller", menu)

# def exit():
#     if keyboard.wait("q"):
#         os._exit(0)
        

full_reload()
threading.Thread(target=icon.run, daemon=True).start()
# threading.Thread(target=exit, daemon=True).start()
asyncio.run(main(address))