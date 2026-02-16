# gui_ctk.py
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from rtdb_client import set_active_profile
# from firebase_admin import db
from config_store import load_config, save_config, get_profiles, get_mapping_str, set_mapping
import cloud

BUTTON_IDS = ["BTN:1", "BTN:2", "BTN:3", "BTN:4"]


def parse_hotkey(text: str) -> list[str]:
    """
    Accepts:
      "ctrl+a"  "ctrl + a"  "Ctrl+A"  "shift+alt+s"
    Returns:
      ["ctrl","a"]
    """
    t = (text or "").strip().lower().replace(" ", "")
    if not t:
        return []
    parts = [p for p in t.split("+") if p]
    return parts


class ConfigGui(ctk.CTkToplevel):
    def __init__(self, master, file_lock, state):
        super().__init__(master)

        # ---- Theme ----
        ctk.set_appearance_mode("dark")          # "dark" | "light" | "system"
        ctk.set_default_color_theme("dark-blue") # "blue" | "green" | "dark-blue"

        self.title("MacroPad Config")
        self.geometry("760x440")
        self.minsize(700, 400)

        self.file_lock = file_lock
        self.app_state = state

        self.data = load_config(self.file_lock)
        self.profiles = get_profiles(self.data)
        if not self.profiles:
            messagebox.showerror("Error", "No profiles found in config.")
            self.destroy()
            return

        # Root layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Vars
        self.profile_var = tk.StringVar(value=self.app_state.get("activeProfile") or self.profiles[0])
        self.entry_vars: dict[str, tk.StringVar] = {}
        self.conn_var = tk.StringVar(value="Disconnected")

        self._build_topbar()
        self._build_main()
        self._build_bottombar()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._load_profile_into_fields()

        # Make sure window is on top when opened from tray
        self.lift()
        self.focus_force()      

    def _build_topbar(self):
        top = ctk.CTkFrame(self, corner_radius=16)
        top.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        top.grid_columnconfigure(1, weight=1)
        top.grid_columnconfigure(6, weight=1)

        ctk.CTkLabel(top, text="Profile", font=ctk.CTkFont(size=14, weight="bold")) \
            .grid(row=0, column=0, padx=(14, 8), pady=12, sticky="w")

        self.profile_menu = ctk.CTkOptionMenu(
            top,
            variable=self.profile_var,
            values=self.profiles,
            width=200,
            command=lambda _: self._load_profile_into_fields()
        )
        self.profile_menu.grid(row=0, column=1, padx=(0, 12), pady=12, sticky="w")

        ctk.CTkButton(top, text="Add", width=90, command=self._add_profile).grid(row=0, column=2, padx=6, pady=12)
        ctk.CTkButton(
            top, text="Delete", width=90,
            fg_color="#8a2f2f", hover_color="#a63a3a",
            command=self._delete_profile
        ).grid(row=0, column=3, padx=6, pady=12)

        # Status pill on the right
        self.status_pill = ctk.CTkLabel(
            top,
            textvariable=self.conn_var,
            corner_radius=999,
            padx=14,
            pady=6
        )
        self.status_pill.grid(row=0, column=6, padx=14, pady=12, sticky="e")

        # initialize from app state
        self._apply_conn_style(bool(self.app_state.get("connected")))


    def _build_main(self):
        main = ctk.CTkFrame(self, corner_radius=16)
        main.grid(row=1, column=0, sticky="nsew", padx=14, pady=8)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(0, weight=1)

        # Title row
        ctk.CTkLabel(main, text="Button Mappings", font=ctk.CTkFont(size=14, weight="bold")) \
            .grid(row=0, column=0, padx=14, pady=(14, 8), sticky="w")

        # Header row
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.grid(row=1, column=0, padx=14, pady=(0, 6), sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header, text="Button", text_color="#bdbdbd") \
            .grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header, text="Hotkey (ex: ctrl+a)", text_color="#bdbdbd") \
            .grid(row=0, column=1, sticky="w")

        # Rows
        body = ctk.CTkFrame(main, fg_color="transparent")
        body.grid(row=2, column=0, padx=14, pady=(0, 14), sticky="nsew")
        body.grid_columnconfigure(1, weight=1)

        for i, btn in enumerate(BUTTON_IDS):
            r = i

            ctk.CTkLabel(body, text=btn).grid(row=r, column=0, sticky="w", pady=8)

            var = tk.StringVar()
            entry = ctk.CTkEntry(body, textvariable=var, placeholder_text="e.g. ctrl+shift+s")
            entry.grid(row=r, column=1, sticky="ew", pady=8, padx=(12, 0))

            self.entry_vars[btn] = var

        # Tip text
        ctk.CTkLabel(
            main,
            text="Tip: Use + to combine keys (ctrl+shift+s). Avoid only-modifiers (ctrl+shift).",
            text_color="#bdbdbd"
        ).grid(row=3, column=0, padx=14, pady=(0, 14), sticky="w")

    def _build_bottombar(self):
        bottom = ctk.CTkFrame(self, corner_radius=16)
        bottom.grid(row=2, column=0, sticky="ew", padx=14, pady=(8, 14))
        bottom.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            bottom, text="Reload", width=120,
            fg_color="#3a3a3a", hover_color="#444",
            command=self._reload_from_disk
        ).grid(row=0, column=0, padx=14, pady=12, sticky="w")

        right = ctk.CTkFrame(bottom, fg_color="transparent")
        right.grid(row=0, column=1, padx=14, pady=12, sticky="e")

        ctk.CTkButton(
            right, text="Close", width=120,
            fg_color="#3a3a3a", hover_color="#444",
            command=self._on_close
        ).grid(row=0, column=0, padx=(0, 8))

        ctk.CTkButton(right, text="Save", width=120, command=self._save).grid(row=0, column=1)

    # --------- Logic stays the same (just UI refresh helpers) ---------

    def _refresh_profile_menu(self):
        # CustomTkinter option menu needs explicit value refresh
        self.profile_menu.configure(values=self.profiles)

    def _reload_from_disk(self):
        self.data = load_config(self.file_lock)
        self.profiles = get_profiles(self.data)
        if not self.profiles:
            messagebox.showerror("Error", "No profiles found in config.")
            return

        self._refresh_profile_menu()
        if self.profile_var.get() not in self.profiles:
            self.profile_var.set(self.profiles[0])
        self._load_profile_into_fields()

    def _load_profile_into_fields(self):
        prof = self.profile_var.get()
        prof_data = (self.data.get("profiles") or {}).get(prof) or {}
        for btn in BUTTON_IDS:
            self.entry_vars[btn].set(get_mapping_str(prof_data, btn))

    def _save(self):
        prof = self.profile_var.get()
        profiles_dict = self.data.setdefault("profiles", {})
        prof_data = profiles_dict.setdefault(prof, {})

        for btn in BUTTON_IDS:
            raw = self.entry_vars[btn].get()
            keys = parse_hotkey(raw)

            if keys and all(k in ("ctrl", "alt", "shift", "win") for k in keys):
                messagebox.showerror("Invalid hotkey", f"Button {btn}: include a non-modifier key (ex: ctrl+a).")
                return

            set_mapping(prof_data, btn, keys)

        self.data["activeProfile"] = prof
        self.app_state["activeProfile"] = prof
        
        try:
            save_config(self.file_lock, self.data, cloud.cloud_sync, prof)
            # db.reference("/").update({"activeProfile": prof})
            # db.reference(f"profiles/{prof}").set(prof_data)

        except Exception as e:
            messagebox.showwarning("Saved locally", f"Saved locally, but Firebase update failed:\n{e}")
            return

        messagebox.showinfo("Saved", "Config saved successfully.")

    def _add_profile(self):
        # CustomTkinter input dialog
        dialog = ctk.CTkInputDialog(title="Add Profile", text="Enter new profile name:")
        name = dialog.get_input()

        if not name:
            return
        name = name.strip()
        if not name:
            return

        profiles = self.data.setdefault("profiles", {})
        if name in profiles:
            messagebox.showerror("Error", "Profile already exists.")
            return

        profiles[name] = {btn: {"keys": []} for btn in BUTTON_IDS}

        self.data["activeProfile"] = name
        self.app_state["activeProfile"] = name

        save_config(self.file_lock, self.data, cloud.cloud_sync)

        # Refresh
        self.profiles = get_profiles(self.data)
        self._refresh_profile_menu()
        self.profile_var.set(name)
        self._load_profile_into_fields()

        messagebox.showinfo("Profile added", f"Created profile '{name}' with empty mappings.")

    def _delete_profile(self):
        prof = self.profile_var.get()

        if len(self.profiles) <= 1:
            messagebox.showerror("Error", "You must keep at least one profile.")
            return

        if not messagebox.askyesno("Delete Profile", f"Delete '{prof}'?"):
            return

        del self.data["profiles"][prof]

        if self.app_state.get("activeProfile") == prof:
            remaining = list(self.data["profiles"].keys())
            new_active = remaining[0]
            self.data["activeProfile"] = new_active
            self.app_state["activeProfile"] = new_active

        save_config(self.file_lock, self.data, cloud.cloud_sync)

        self.profiles = get_profiles(self.data)
        self._refresh_profile_menu()
        self.profile_var.set(self.app_state["activeProfile"])
        self._load_profile_into_fields()

    def _on_close(self):
        # Clear GUI reference so BLE code doesn't talk to a dead window
        try:
            self.app_state["gui_window"] = None
        except Exception:
            pass

        self.destroy()

    def _apply_conn_style(self, connected: bool):
        if connected:
            self.conn_var.set("Connected")
            self.status_pill.configure(fg_color="#1f6f3b")  # green
        else:
            self.conn_var.set("Disconnected")
            self.status_pill.configure(fg_color="#6b2b2b")  # red

    def set_connected(self, connected: bool):
        """Safe to call from ANY thread."""
        try:
            self.after(0, lambda: self._apply_conn_style(connected))
        except Exception:
            pass

def open_config_gui(file_lock, state):
    """
    Same behavior as your original: safe to call from tray thread *if*
    your app already uses a GUI host that schedules onto the main Tk thread.
    """
    root = tk._default_root
    if root is None:
        # Create a hidden root window (CTk is fine too, but Tk is safest for shared tkinter state)
        root = tk.Tk()
        root.withdraw()

    win = ConfigGui(root, file_lock=file_lock, state=state)
    state["gui_window"] = win
    try:
        win.set_connected(bool(state.get("connected")))
    except Exception:
        pass

    win.lift()
    win.focus_force()
