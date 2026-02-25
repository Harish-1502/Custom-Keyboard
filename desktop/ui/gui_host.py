# gui_host.py
import threading
import queue
import tkinter as tk
import customtkinter as ctk

from desktop.ui.gui import ConfigGui, open_config_gui

class GuiHost:
    def __init__(self, file_lock, state, controller):
        self.file_lock = file_lock
        self.state = state
        self.controller = controller

        self._q: "queue.Queue[callable]" = queue.Queue()
        self._thread: threading.Thread | None = None
        self._root: ctk.CTk | None = None
        self._ready = threading.Event()
        self.win_ref = None

    # Ensure the GUI thread is started. Checks if already started.
    def _ensure_started(self):
        if self._thread and self._thread.is_alive():
            return

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    # The GUI thread main loop
    def _run(self):
        self._root = ctk.CTk()
        
        self._root.withdraw()
        self._ready.set()

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

        # Wait briefly so first click doesn't race the Tk thread
        self._ready.wait(timeout=1.0)

        def _open():
            if self._root is None:
                print("GUI: _open() called but root is None")
                return

            # If already open, just focus it
            win = self.win_ref or self.state.get("gui_window")
            try:
                if win is not None and win.winfo_exists():
                    win.deiconify()
                    win.lift()
                    win.focus_force()
                    return
            except Exception:
                pass

            # Create window using the correct master
            self.win_ref = open_config_gui(self._root, self.file_lock, self.state, self.controller)

            # Ensure it appears (some Windows setups need this)
            win = self.state.get("gui_window")
            try:
                if win is not None:
                    win.deiconify()
                    win.lift()
                    win.focus_force()
                    win.after(200, lambda: (win.lift(), win.focus_force()))
            except Exception:
                pass

            print("GUI: state gui_window =", self.state.get("gui_window"))
            
        
        self._q.put(_open)
