from __future__ import annotations
import time
from typing import Dict, Any, Optional

from auth_client import FirebaseAuthClient, load_auth_cache, save_auth_cache

class SessionManager:
    def __init__(self, api_key: str):
        self.auth_client = FirebaseAuthClient(api_key)
        self._cache: Dict[str, Any] = load_auth_cache() or {}
        self._last_refresh_ts: float = 0

    def is_logged_in(self) -> bool:
        return bool(self._cache.get("refreshToken") and self._cache.get("uid"))
    
    # get the ui
    def get_uid(self) -> str:
        uid = self._cache.get("uid")
        if not uid:
            raise RuntimeError("Not logged in: missing uid")
        return uid
    
    # get the id token
    def get_id_token(self) -> str:
        """
        Returns a valid idToken. Refreshes using refreshToken if needed.
        We refresh opportunistically:
          - if no idToken in cache
          - or if we haven't refreshed in a while
        (You can tighten this later by tracking token expiry.)
        """
        if not self._cache.get("refreshToken"):
            raise RuntimeError("Not logged in: missing refreshToken")

        # If missing idToken or it's been a while, refresh.
        # Firebase idTokens typically last ~1 hour; refresh every 45 minutes safely.
        now = time.time()
        should_refresh = (not self._cache.get("idToken")) or (now - self._last_refresh_ts > 45 * 60)

        if should_refresh:
            refreshed = self.auth_client.refresh_token(self._cache["refreshToken"])
            # securetoken endpoint fields:
            # id_token, refresh_token, user_id
            self._cache["idToken"] = refreshed["id_token"]
            self._cache["refreshToken"] = refreshed["refresh_token"]
            self._cache["uid"] = refreshed["user_id"]
            self._last_refresh_ts = now
            save_auth_cache(self._cache)

        return self._cache["idToken"]

    def update_from_login(self, signed: Dict[str, Any]) -> None:
        """
        If you do an explicit login/signup and get a response with localId/idToken/refreshToken,
        store it here.
        """
        self._cache = {
            "email": signed.get("email"),
            "uid": signed["localId"],
            "idToken": signed["idToken"],
            "refreshToken": signed["refreshToken"],
        }
        self._last_refresh_ts = time.time()
        save_auth_cache(self._cache)

    def clear(self) -> None:
        self._cache = {}
        save_auth_cache({})