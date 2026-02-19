import asyncio
from email.mime import message
import webbrowser
from desktop.cloud.rtdb_client import set_active_profile
from desktop.ui.gui_host import GuiHost
# from firebase_admin import db
from desktop.core.paths import get_config_path
import json
import os
import desktop.cloud.cloud as cloud
import requests
import dotenv

dotenv.load_dotenv()

URL = os.getenv("DATABASE_URL")
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
        full_reload_from_db,
        connecting_to_db,
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
        self.full_reload_from_db = full_reload_from_db
        self.connecting_to_db = connecting_to_db
        self.array_index = array_index
        self._gui = GuiHost(self.FILE_LOCK, self.state, self)
        self.icon = None
        self.cloud_sync = None

    def set_icon(self, icon):
        self.icon = icon
        self.apply_tray_title()
    
    def refresh_json(self, file_lock):
        self.notify("Refreshing config from database...")
        try:
            self.full_reload_from_db(file_lock)
            self.notify("Config refreshed from database.")
        except requests.exceptions.RequestException as e:
            self.notify(f"Network error during refresh: {e}") 
        except Exception as e:
            self.notify(f"Failed to refresh config: {e}")

    def apply_tray_title(self):
        if not self.icon:
            return
        status = "Connected" if self.state.get("connected") else "Disconnected"
        self.icon.title = f"Custom Keyboard - {status}"

    def notify(self, message: str, title: str = "Custom Keyboard"):
        print("NOTIFY:", message)
        if self.icon:
            self.apply_tray_title()   # <-- correct name
            try:
                self.icon.notify(message, title)
            except Exception as e:
                print("Tray notify failed:", e)

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
        self.LOOP.call_soon_threadsafe(lambda: self.start_ble_session(self.name, self.FILE_LOCK, self.state, self.LOOP, on_connected=self.on_ble_connected, on_disconnected=self.on_ble_disconnected, on_error=self.on_ble_error))

    # Used in pystray menu to disconnect
    def tray_disconnect(self, *_):
        print("Disconnecting from the device")
        self.LOOP.call_soon_threadsafe(self.stop_ble_session)

    def tray_sign_in(self, *_):
    # Don’t block the tray thread; schedule onto asyncio loop
        self.LOOP.call_soon_threadsafe(lambda: self.LOOP.create_task(self._async_cloud_connect()))
    
    async def _async_cloud_connect(self):
        await asyncio.to_thread(self.connecting_to_db, self.FILE_LOCK)

    # Goes to the database website
    def open_website(self, icon, item):
        webbrowser.open(URL)
        
    # Changes the active profile in the local json file    
    def set_state(self, new_profile: str):
        with self.FILE_LOCK:
            try:
                with get_config_path().open("r", encoding="utf-8") as f:
                    data = json.load(f)
            except FileNotFoundError:
                data = {}
        
            data["activeProfile"] = new_profile
            
            with get_config_path().open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        
        # self.db.reference("/").update({f"activeProfile": new_profile})
        set_active_profile(cloud.cloud_sync.rtdb, cloud.cloud_sync.uid, cloud.cloud_sync.id_token, new_profile)

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
        # self.db.reference(f"profiles/{new_active_profile}").listen(self.make_listener(new_active_profile, self.FILE_LOCK))

    def open_gui(self):
        self._gui.open_config()

# -------- Professional BLE event handlers --------
    def on_ble_connected(self):
        self.state["connected"] = True
        self.notify("Device connected")

    def on_ble_disconnected(self):
        self.state["connected"] = False
        self.notify("Device disconnected")

    def on_ble_error(self, err: str):
        self.state["connected"] = False
        self.notify(f"BLE error: {err}")