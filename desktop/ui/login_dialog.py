import tkinter as tk
from tkinter import ttk, messagebox

def prompt_credentials(app_name: str = "CustomKeyboard") -> tuple[str, str] | None:
    root = tk.Tk()
    root.title(f"{app_name} - Sign in")
    root.resizable(False, False)

    email_var = tk.StringVar()
    pass_var = tk.StringVar()

    frm = ttk.Frame(root, padding=12)
    frm.grid()

    ttk.Label(frm, text="Email").grid(row=0, column=0, sticky="w")
    email_entry = ttk.Entry(frm, textvariable=email_var, width=34)
    email_entry.grid(row=1, column=0, pady=(0, 10))

    ttk.Label(frm, text="Password").grid(row=2, column=0, sticky="w")
    pass_entry = ttk.Entry(frm, textvariable=pass_var, width=34, show="•")
    pass_entry.grid(row=3, column=0, pady=(0, 10))

    result: dict[str, str] = {}

    def on_ok():
        email = email_var.get().strip()
        pwd = pass_var.get()
        if not email or not pwd:
            messagebox.showerror("Missing info", "Please enter email and password.")
            return
        result["email"] = email
        result["password"] = pwd
        root.destroy()

    def on_cancel():
        root.destroy()

    btns = ttk.Frame(frm)
    btns.grid(row=4, column=0, sticky="e")
    ttk.Button(btns, text="Cancel", command=on_cancel).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(btns, text="Sign in", command=on_ok).grid(row=0, column=1)

    email_entry.focus()
    root.mainloop()

    if "email" in result:
        return result["email"], result["password"]
    return None
