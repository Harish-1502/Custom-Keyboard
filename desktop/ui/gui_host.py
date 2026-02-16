# gui_host.py
import threading
import queue
import tkinter as tk

from desktop.ui.gui import ConfigGui, open_config_gui

class GuiHost:
    def __init__(self, file_lock, state):
        self.file_lock = file_lock
        self.state = state
        self._q: "queue.Queue[callable]" = queue.Queue()
        self._thread: threading.Thread | None = None
        self._root: tk.Tk | None = None

    # Ensure the GUI thread is started. Checks if already started.
    def _ensure_started(self):
        if self._thread and self._thread.is_alive():
            return

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    # The GUI thread main loop
    def _run(self):
        self._root = tk.Tk()
        self._root.withdraw()

        # Pump function to run queued tasks. Runs every 50ms.
        # This allows work to be done without blocking the GUI.
        def pump():
            while True:
                try:
                    fn = self._q.get_nowait()
                except queue.Empty:
                    break
                try:
                    fn()
                except Exception as e:
                    print("GUI task error:", e)
            self._root.after(50, pump)

        self._root.after(50, pump)
        self._root.mainloop()

    # First checks that the GUI is started
    def open_config(self):
        self._ensure_started()

        # Function to open the config window
        def _open():
            assert self._root is not None
            open_config_gui(self.file_lock, self.state)

        # Queue the open task to be run in the GUI thread
        self._q.put(_open)
