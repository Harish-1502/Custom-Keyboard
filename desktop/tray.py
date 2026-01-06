import pystray
from pystray import MenuItem as item
from paths import ASSETS_PATH
from PIL import Image

def build_tray(app):

    # Define the menu items
    image = Image.open(ASSETS_PATH)

    menu = pystray.Menu(
        pystray.MenuItem("Open DB", lambda icon, item: app.open_db()),
        pystray.MenuItem("Refresh json", lambda icon, item: app.refresh_json()),
        pystray.MenuItem("Change profile", lambda icon, item: app.next_profile()),
        pystray.MenuItem("Connect BLE", lambda icon, item: app.connect_ble()),
        pystray.MenuItem("Disconnect BLE", lambda icon, item: app.disconnect_ble()),
        pystray.MenuItem("Exit", lambda icon, item: app.shutdown(icon)),
    )

    return pystray.Icon("MacroPad", image, "Macro Controller", menu)