import json
from paths import CONFIG_PATH
from threading import RLock

# # Load the active profile before closing the program
def load_prev_state(FILE_LOCK: RLock) -> str | None:
    with FILE_LOCK:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            temp_config = json.load(f)
    return temp_config.get("activeProfile")
