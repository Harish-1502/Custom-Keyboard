# cloud_sync.py
from __future__ import annotations
import json
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Callable

from desktop.cloud.auth_client import ensure_logged_in
from desktop.core.session_manager import SessionManager
from desktop.cloud.rtdb_client import RTDBClient, seed_if_missing, put_user_config, get_user_config

def load_json_file(path: str, file_lock: threading.RLock) -> Optional[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return None
    with file_lock:
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

def write_json_file(path: str, data: Dict[str, Any], file_lock: threading.RLock) -> None:
    with file_lock:
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

class CloudSync:
    """
    Minimal helper:
      - login (gets uid/idToken)
      - ensure cloud user node exists
      - backup local config to cloud on demand
    """
    def __init__(self, api_key: str, db_url: str, local_config_path: str, file_lock: threading.RLock, default_config: Dict[str, Any]):
        self.api_key = api_key
        self.rtdb = RTDBClient(db_url)
        self.local_config_path = local_config_path
        self.file_lock = file_lock
        self.default_config = default_config
        self.session = SessionManager(api_key)

        # self.uid = self.session.get_uid()
        # self.id_token = self.session.get_id_token()

    def connect(self) -> None:
        """
        Source of truth = local.
        Cloud = backup.

        Startup behavior:
        - prompt login
        - if local exists:
            - if cloud missing -> upload local (seed cloud)
            - else do nothing (keep local)
        - if local missing:
            - if cloud exists -> restore cloud to local
            - else -> write defaults local and upload defaults to cloud
        """

        print("Connecting to cloud...")
        session = ensure_logged_in(self.api_key)
        if not session:
            print("Login failed or cancelled.")
            return
        self.session.update_from_login(session)
        self.uid = session["uid"]
        self._id_token = session["idToken"]
        self._refresh_token = session["refreshToken"]

        # 1) read local (if any)
        local = load_json_file(self.local_config_path, self.file_lock)

        # 2) read cloud (may be None if first time)
        cloud = get_user_config(self.rtdb, self._id_token, self.uid)

        print(f"CloudSync connect: local exists={local is not None}, cloud exists={cloud is not None}")

        print(f"Local config: {local}")
        print(f"Cloud config: {cloud}")
        if local is not None:
            print("Local config exists. Keeping local as source of truth.")
            # Local exists → treat as truth
            return

        # local is missing:
        if cloud is not None:
            # Restore from cloud
            print("Restoring local config from cloud...")
            from desktop.cloud.cloud import full_reload_from_db
            full_reload_from_db(self.file_lock) 
            return

        # Both missing: create local defaults then upload
        print("No local or cloud config. Seeding defaults...")
        write_json_file(self.local_config_path, self.default_config, self.file_lock)
        put_user_config(self.rtdb, self.uid, self._id_token, self.default_config)
        
    def backup_now(self) -> None:
        """
        Call this after GUI saves local JSON.
        Uploads the whole local config as a snapshot to /users/{uid}.
        """
        if not self.uid or not self._id_token:
            raise RuntimeError("CloudSync not connected (missing uid/idToken)")

        local = load_json_file(self.local_config_path, self.file_lock) or self.default_config
        
        id_token = self.session.get_id_token()   # refreshes if needed
        self.rtdb.put(f"users/{self.uid}", id_token, local)

    def backup_config(self, config: Dict[str, Any]) -> None:
        """
        If you already have the config in memory (right after saving),
        upload that instead of re-reading file.
        """
        id_token = self.session.get_id_token()   # refreshes if needed
        self.rtdb.put(f"users/{self.uid}", id_token, config)

    def restore_to_local_if_possible(self) -> bool:
        """
        Returns True if it restored local from cloud.
        False if cloud had nothing.
        """
        uid = self.session.get_uid()
        token = self.session.get_id_token()
        cloud_data = self.rtdb.get(f"users/{uid}", token)

        if not cloud_data:
            return False

        # write local
        write_json_file(self.local_config_path, cloud_data, self.file_lock)
        return True
