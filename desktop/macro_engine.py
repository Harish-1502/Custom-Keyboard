
# Kills everything
def exit_app(icon, item):
    icon.stop()
    if LOOP:
        LOOP.call_soon_threadsafe(LOOP.stop)
    os._exit(0)