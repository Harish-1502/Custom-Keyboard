import asyncio
import os
import threading

from desktop.core.paths import CONFIG_PATH
from dotenv import load_dotenv

from desktop.core.config_store import ensure_local_config_exists, load_prev_state
from desktop.cloud.cloud import full_reload_from_db, connecting_to_db
from desktop.ble.ble_client import start_ble_session, stop_ble_session
from desktop.ui.tray import build_tray
from desktop.ui.app_controller import AppController

load_dotenv()
address = os.getenv("ADDRESS")
char_uuid = os.getenv("CHAR_UUID")
name = os.getenv("NAME")
config_list = ["default","computer"]
FILE_LOCK = threading.RLock()
LOOP = None

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
        
connecting_to_db(FILE_LOCK)

print("config_store __file__ =", __file__)
print("CONFIG_PATH =", CONFIG_PATH)


ensure_local_config_exists(FILE_LOCK)

state = {"activeProfile": load_prev_state(FILE_LOCK), "connected": False, "gui_window": None}

# Getting the array index from the array that the active profile is in
array_index = 0
for index,profile_name  in enumerate(config_list):
    if state["activeProfile"] == profile_name :
        array_index = index
        # print("Array index: ",array_index) 

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
    full_reload_from_db,
    array_index
)
icon = build_tray(tray_controller)

threading.Thread(target=icon.run, daemon=True).start()
run_event_loop_forever()