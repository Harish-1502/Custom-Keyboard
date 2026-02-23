from desktop.core.paths import get_assets_path
from PIL import Image

def _get_pystray():
    try:
        import pystray  # type: ignore
        return pystray
    except Exception:
        return None
    
def build_tray(app):
    pystray = _get_pystray()
    if pystray is None:
        return None
    
    # Define the menu items
    ASSETS_PATH = get_assets_path()
    # print(ASSETS_PATH)
    image = Image.open(ASSETS_PATH)

    menu = pystray.Menu(
        pystray.MenuItem("Open DB", lambda icon, item: app.open_website(icon, item)),
        pystray.MenuItem("Connect to DB", lambda icon, item: app.tray_sign_in(icon, item)),
        pystray.MenuItem("Open GUI", lambda icon, item: app.open_gui()),
        pystray.MenuItem("Refresh json", lambda icon, item: app.refresh_json(app.FILE_LOCK)),
        pystray.MenuItem("Change profile", lambda icon, item: app.change_profile(step=1)),
        pystray.MenuItem("Connect BLE", lambda icon, item: app.tray_connect(icon, item)),
        pystray.MenuItem("Disconnect BLE", lambda icon, item: app.tray_disconnect(icon, item)),
        pystray.MenuItem("Exit", lambda icon, item: app.exit_app(icon)),
        
    )

    return pystray.Icon("MacroPad", image, "Macro Controller", menu)