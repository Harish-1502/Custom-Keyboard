import asyncio, os
from bleak import BleakClient, BleakScanner
from dotenv import load_dotenv
import json
import pyautogui

from paths import CONFIG_PATH
from threading import RLock


load_dotenv()

address = os.getenv("ADDRESS")
char_uuid = os.getenv("CHAR_UUID")

if not address:
    raise RuntimeError("Missing ADDRESS env var (BLE MAC). Set ADDRESS=AA:BB:CC:DD:EE:FF")
if not char_uuid:
    raise RuntimeError("Missing CHAR_UUID env var (notify characteristic UUID).")

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
    
async def find_device_address_by_name(name: str, timeout: float = 8.0) -> str:
    devices = await BleakScanner.discover(timeout=timeout)
    for d in devices:
        if (d.name or "").strip() == name:
            return d.address
    raise RuntimeError(f"Device '{name}' not found in scan.")

# Used to initiate the device connection and BLE connection
async def connect(device_name:str, char_uuid:str, BLE_CLIENT: BleakClient | None, BLE_STOP_EVENT: asyncio.Event | None, BLE_TASK: asyncio.Task | None, active_profile, FILE_LOCK: RLock):
    
    # global BLE_CLIENT, BLE_STOP_EVENT, BLE_TASK
    
    BLE_STOP_EVENT = asyncio.Event()
    
    try:
        address = await find_device_address_by_name(device_name, timeout=8.0)
        print(f"Connecting to {address} ...")
        
        client = BleakClient(address, timeout=20.0)
        
        BLE_CLIENT = client
        
        disc = asyncio.Event()
        client.set_disconnected_callback(lambda _: disc.set())
        
        await client.connect()
        print("Connected to ESP32 Macro Pad!")
        
        await asyncio.sleep(0.8)

        # Retry service discovery a couple times (ESP32 often needs it)
        for attempt in range(1, 4):
            try:
                await verify_char_uuid(client, char_uuid)
                break
            except Exception as e:
                if attempt == 3:
                    raise
                print(f"GATT not ready yet (attempt {attempt}): {e}")
                await asyncio.sleep(0.8)
        handler = make_notification_handler(active_profile, FILE_LOCK)
        await client.start_notify(char_uuid, handler)
        print("Listening for notifications...")
        
        disc_task = asyncio.create_task(disc.wait())
        stop_task = asyncio.create_task(BLE_STOP_EVENT.wait())
        
        done, pending = await asyncio.wait(
            [disc_task, stop_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        
        for task in pending:
            task.cancel()
            
        
    except Exception as e:
        print("BLE session error:", e)
        
    finally:        
        if BLE_CLIENT:
            if BLE_CLIENT.is_connected:
                try:
                    await BLE_CLIENT.stop_notify(char_uuid)
                except Exception as e:
                    print("Failed to stop notify:", e)
                await BLE_CLIENT.disconnect()
        
        BLE_CLIENT = None
        BLE_STOP_EVENT = None
        BLE_TASK = None
        print("BLE disconnected (session ended).")
        
# Gets the button ID and activates the trigger_macro function
def make_notification_handler(active_profile, FILE_LOCK: RLock):
    def notification(sender, data):   
        msg = data.decode("utf-8").strip()
        print(f"Received {msg}")
        print(f"Active Profile; {active_profile}")
        trigger_macro(msg,active_profile, FILE_LOCK)
    return notification

# Reads buttonControls.json, gets the button_id and profile, finds the action and executes it
def trigger_macro(button_id, profile, FILE_LOCK):
    with FILE_LOCK:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
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
        
# Helper function to do connect 
def start_ble_session(BLE_TASK: asyncio.Task | None, LOOP, BLE_CLIENT: BleakClient | None, BLE_STOP_EVENT: asyncio.Event | None, active_profile, FILE_LOCK: RLock):
    # global BLE_TASK
    if BLE_TASK and not BLE_TASK.done():
        print("BLE session already running.")
        return BLE_TASK
    
    async def connect_wrapper():
        await asyncio.sleep(0.5)
        await connect(name, char_uuid, BLE_CLIENT, BLE_STOP_EVENT, BLE_TASK, active_profile, FILE_LOCK)

    BLE_TASK = LOOP.create_task(connect_wrapper())
    return BLE_TASK

# Helper function to disconnect 
def stop_ble_session(BLE_TASK: asyncio.Task | None, BLE_STOP_EVENT: asyncio.Event | None):
    # global BLE_TASK,BLE_STOP_EVENT
    if BLE_STOP_EVENT and not BLE_STOP_EVENT.is_set():
        BLE_STOP_EVENT.set()
        # BLE_TASK.cancel()
        print("Requesting BLE session cancel...")
        return
    # BLE_TASK = None
    
    print("No BLE session to cancel.")