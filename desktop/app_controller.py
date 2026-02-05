import asyncio
import webbrowser
from firebase_admin import db
from paths import CONFIG_PATH
import json
import os

class AppController:
    def __init__(
        self,
        loop,
        file_lock,
        state,
        config_list,
        device_name,
        char_uuid,
        start_ble_session,
        stop_ble_session,
        make_listener,
        full_reload_from_db,
        array_index
    ):
        self.LOOP = loop
        self.FILE_LOCK = file_lock
        self.state = state
        self.config_list = config_list
        self.name = device_name
        self.char_uuid = char_uuid
        self.start_ble_session = start_ble_session
        self.stop_ble_session = stop_ble_session
        self.make_listener = None
        self.db = db
        self.full_reload_from_db = full_reload_from_db
        self.array_index = array_index
        self.make_listener = make_listener

    # Kills everything
    def exit_app(self, icon):
        icon.stop()
        if self.LOOP:
            self.LOOP.call_soon_threadsafe(self.LOOP.stop)
        os._exit(0)

    # Used in pystray menu to connect. For pystray, the method used in its menu has to be sync
    def tray_connect(self, *_):
        # called from tray thread → schedule work on asyncio loop
        print("Connecting to device")
        self.LOOP.call_soon_threadsafe(lambda: self.start_ble_session(self.name, self.FILE_LOCK, self.state, self.LOOP))

    # Used in pystray menu to disconnect
    def tray_disconnect(self, *_):
        print("Disconnecting from the device")
        self.LOOP.call_soon_threadsafe(self.stop_ble_session)

    # Goes to the database website
    def open_website(self, icon, item):
        webbrowser.open("https://macro-controller-default-rtdb.firebaseio.com/")
        
    # Changes the active profile in the local json file    
    def set_state(self, new_profile: str):
        with self.FILE_LOCK:
            try:
                with CONFIG_PATH.open("r", encoding="utf-8") as f:
                    data = json.load(f)
            except FileNotFoundError:
                data = {}
        
            data["activeProfile"] = new_profile
            
            with CONFIG_PATH.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        
        self.db.reference("/").update({f"activeProfile": new_profile})

    # Used to change the active profile 
    def change_profile(self, step):
        # global array_index,state

        n = len(self.config_list)
        if n == 0:
            print("No profiles available")
            return
        self.array_index = (self.array_index + step) % n
        new_active_profile = self.config_list[self.array_index]

        print(f"currently in {new_active_profile} mode")
        self.set_state(new_active_profile)
        self.state["activeProfile"] = new_active_profile
        self.db.reference(f"profiles/{new_active_profile}").listen(self.make_listener(new_active_profile, self.FILE_LOCK))

    # Increment the active profile in the config list array
    # def increment_array_index(self,*_):
    #     self.change_profile(1)