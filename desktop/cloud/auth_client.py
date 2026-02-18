from __future__ import annotations
import json
import os
from pathlib import Path
from tkinter import messagebox
from typing import Optional, Dict, Any
import tkinter as tk

import requests

from desktop.ui.login_dialog import prompt_credentials

FIREBASE_AUTH_BASE = "https://identitytoolkit.googleapis.com/v1"
FIREBASE_SECURETOKEN_BASE = "https://securetoken.googleapis.com/v1"

def appdata_dir() -> Path:
    # Windows AppData location or fallback to home directory
    base = os.getenv("APPDATA") or str(Path.home())
    p = Path(base) / "CustomKeyboard"
    p.mkdir(parents=True, exist_ok=True)
    return p

def auth_cache_path() -> Path:
    return appdata_dir() / "auth_cache.json"

def load_auth_cache() -> Optional[Dict[str, Any]]:
    p = auth_cache_path()
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print("Failed to load auth cache:", e)
        return None
    
def save_auth_cache(data: Dict[str, Any]) -> None:
    p = auth_cache_path()
    try:
        p.write_text(json.dumps(data), encoding="utf-8")
    except Exception as e:
        print("Failed to save auth cache:", e)


class FirebaseAuthClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is required for FirebaseAuthClient.")
        self.api_key = api_key
    
    def sign_up(self, email: str, password: str) -> Dict[str, Any]:
        url = f"{FIREBASE_AUTH_BASE}/accounts:signUp?key={self.api_key}"
        payload = {"email": email, "password": password, "returnSecureToken": True}
        response = requests.post(url, json=payload, timeout=20)
        return self._handle(response)
    
    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        url = f"{FIREBASE_AUTH_BASE}/accounts:signInWithPassword?key={self.api_key}"
        payload = {"email": email, "password": password, "returnSecureToken": True}
        response = requests.post(url, json=payload, timeout=20)
        return self._handle(response)
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        url = f"{FIREBASE_SECURETOKEN_BASE}/token?key={self.api_key}"
        payload = {"grant_type": "refresh_token", "refresh_token": refresh_token}
        response = requests.post(url, data=payload, timeout=20)
        return self._handle(response)
    
    def _handle(self, response: requests.Response) -> Dict[str, Any]:
        try:
            data = response.json()
        except Exception as e:
            raise RuntimeError(f"Invalid response from Firebase: {e}")
        
        if response.status_code >= 400:
            # Firebase returns errors like {"error":{"message":"EMAIL_NOT_FOUND"}}
            msg = data.get("error", {}).get("message", f"HTTP_{response.status_code}")
            raise RuntimeError(f"Firebase Auth error: {msg}")
        return data
    
def ensure_logged_in(api_key:str) -> Dict[str, Any]:

    print("Checking authentication status...")
    
    cache = load_auth_cache()
    print("Auth cache loaded:", "Yes" if cache else "No")

    client = FirebaseAuthClient(api_key)
    print("FirebaseAuthClient initialized.")

    if(cache is None):
        print("Cache not found. Please login.")
        creds = prompt_credentials("CustomKeyboard")
        if not creds:
            return None
        email, password = creds
    else:
        # client = FirebaseAuthClient(api_key)
        if cache.get("refreshToken"):
            try:
                refreshed = client.refresh_token(cache["refreshToken"])
                cache["idToken"] = refreshed["id_token"]
                cache["refreshToken"] = refreshed["refresh_token"]
                cache["uid"] = refreshed["user_id"]
                save_auth_cache(cache)
                return cache
            except Exception as e:
                pass  # Failed to refresh, will need to sign in again

        print("Login required. Please sign in with your email and password.")
        # email = input("Email: ").strip()
        # password = input("Password: ").strip()
        creds = prompt_credentials("CustomKeyboard")
        if not creds:
            return None
        email, password = creds

    try:
        signed_result = client.sign_in(email, password)
    except Exception as e:
        if ask_signup(str(e)):
            try:
                signed_result = client.sign_up(email, password)
            except Exception as e2:
                # signup failed -> treat as non-fatal too
                return None
        else:
            return None
        
    # After successful sign in or sign up, save tokens
    cache = {
        "idToken": signed_result["idToken"],
        "refreshToken": signed_result["refreshToken"],
        "uid": signed_result["localId"],
        "email": signed_result["email"],
    }
    save_auth_cache(cache)
    return cache

def ask_signup(err_msg: str) -> bool:
    root = tk.Tk()
    root.withdraw()
    try:
        return messagebox.askyesno(
            title="Sign in failed",
            message=f"Sign in failed:\n{err_msg}\n\nDo you want to create an account with these credentials?"
        )
    finally:
        root.destroy()

def get_session_silent(api_key: str) -> Dict[str, Any] | None:
    """
    Non-interactive: returns cached session with a fresh idToken if possible.
    Returns None if user is not logged in or refresh fails.
    """
    cache = load_auth_cache()
    if not cache.get("refreshToken"):
        return None

    client = FirebaseAuthClient(api_key)
    try:
        refreshed = client.refresh_token(cache["refreshToken"])
        cache["idToken"] = refreshed["id_token"]
        cache["refreshToken"] = refreshed["refresh_token"]
        cache["uid"] = refreshed["user_id"]
        save_auth_cache(cache)
        return cache
    except Exception:
        return None