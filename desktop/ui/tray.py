import pystray
from desktop.core.paths import ASSETS_PATH
from PIL import Image

def build_tray(app):

    # Define the menu items
    print(ASSETS_PATH)
    image = Image.open(ASSETS_PATH)

    menu = pystray.Menu(
        pystray.MenuItem("Open DB", lambda icon, item: app.open_website(icon, item)),
        pystray.MenuItem("Open GUI", lambda icon, item: app.open_gui()),
        pystray.MenuItem("Refresh json", lambda icon, item: app.full_reload_from_db(app.FILE_LOCK)),
        pystray.MenuItem("Change profile", lambda icon, item: app.change_profile(step=1)),
        pystray.MenuItem("Connect BLE", lambda icon, item: app.tray_connect(icon, item)),
        pystray.MenuItem("Disconnect BLE", lambda icon, item: app.tray_disconnect(icon, item)),
        pystray.MenuItem("Exit", lambda icon, item: app.exit_app(icon)),
        
    )

    return pystray.Icon("MacroPad", image, "Macro Controller", menu)