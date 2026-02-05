import asyncio
import os
import threading

from dotenv import load_dotenv

from config_store import load_prev_state
from cloud import full_reload_from_db, make_listener, connecting_to_db
from ble_client import start_ble_session, stop_ble_session
from tray import build_tray
from app_controller import AppController

load_dotenv()
address = os.getenv("ADDRESS")
char_uuid = os.getenv("CHAR_UUID")
cred = os.getenv("CRED")
name = os.getenv("NAME")
config_list = ["default","computer"]
FILE_LOCK = threading.RLock()
LOOP = None

# Loading previous state from shutdown
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

# Creates the icon on the tray menu
tray_controller = AppController(
    LOOP,
    FILE_LOCK,
    state,
    config_list,
    name,
    char_uuid,
    start_ble_session,
    stop_ble_session,
    make_listener,
    full_reload_from_db,
    array_index
)

icon = build_tray(tray_controller)

# Used to run the forever loop and will gracefully close everything
def run_event_loop_forever():
    global LOOP,address, char_uuid
    LOOP = asyncio.new_event_loop()          # 1) make a brand-new event loop
    asyncio.set_event_loop(LOOP)             # 2) mark it as “the current loop” in this thread

    tray_controller.LOOP = LOOP  # set the loop in the tray controller
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