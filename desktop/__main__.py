import asyncio
import os
import threading
from dotenv import load_dotenv

from desktop.core.config_store import ensure_local_config_exists, load_prev_state
from desktop.cloud.cloud import full_reload_from_db, connecting_to_db
from desktop.ble.ble_client import start_ble_session, stop_ble_session
from desktop.ui.tray import build_tray
from desktop.ui.app_controller import AppController

def require_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v

def main():
    load_dotenv()

    address = require_env("ADDRESS")
    char_uuid = require_env("CHAR_UUID")
    name = os.getenv("NAME") or "Macropad"

    config_list = ["default", "computer"]
    file_lock = threading.RLock()

    # 1) Ensure local config exists BEFORE reading it
    ensure_local_config_exists(file_lock)

    state = {
        "activeProfile": load_prev_state(file_lock),
        "connected": False,
        "gui_window": None,
    }

    # 2) Compute array_index safely
    try:
        array_index = config_list.index(state["activeProfile"])
    except ValueError:
        array_index = 0

    # 3) Create the loop first
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # 4) Start cloud sync after local config is guaranteed
    connecting_to_db(file_lock)

    # 5) Build controller with a real loop (no patching later)
    tray_controller = AppController(
        loop,
        file_lock,
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

    # 6) Start BLE + run loop forever with proper cleanup
    try:
        loop.call_soon(lambda: start_ble_session(name, file_lock, state, loop))
        loop.run_forever()
    finally:
        stop_ble_session()
        pending = asyncio.all_tasks(loop)
        for t in pending:
            t.cancel()
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()

if __name__ == "__main__":
    main()
