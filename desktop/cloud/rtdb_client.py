from __future__ import annotations
import json
from typing import Any, Dict, Optional
import requests

class RTDBClient:
    def __init__(self, database_url: str):
        if not database_url:
            raise ValueError("Database URL is required for RTDBClient.")
        self.database_url = database_url.rstrip('/')

    def _url(self, path: str) -> str:
        path = path.strip("/")
        return f"{self.database_url}/{path}.json"
        
    def get(self, path: str, id_token: str) -> Any:
        r = requests.get(self._url(path), params={"auth": id_token}, timeout=20)
        return self._handle(r)

    def put(self, path: str, id_token: str, data: Any) -> Any:
        r = requests.put(self._url(path), params={"auth": id_token}, json=data, timeout=20)
        return self._handle(r)

    def patch(self, path: str, id_token: str, data: Dict[str, Any]) -> Any:
        r = requests.patch(self._url(path), params={"auth": id_token}, json=data, timeout=20)
        return self._handle(r)
    
    def _handle(self, response: requests.Response) -> Any:
        try:
            data = response.json()
        except Exception as e:
            response.raise_for_status()
            raise RuntimeError("Invalid response from RTDB") from e
        return data
    
def seed_if_missing(
    rtdb: RTDBClient,
    uid: str,
    id_token: str,
    default_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Ensures /users/{uid} exists. Returns the cloud config after seeding.
    """
    path = f"users/{uid}"
    existing = rtdb.get(path, id_token)
    if existing is None:
        # First-time user: create their root config
        rtdb.put(path, id_token, default_config)
        return default_config
    
    if isinstance(existing, str):
        fixed = json.loads(existing)          # convert to dict
        rtdb.put(path, id_token, fixed)       # write back corrected structure
        return fixed
    
    return existing


def get_user_config(rtdb: RTDBClient, uid: str, id_token: str) -> Dict[str, Any]:
    data = rtdb.get(f"users/{uid}", id_token)

    if data is None:
        return {}

    if isinstance(data, str):
        return json.loads(data)
    
    return data


def set_active_profile(rtdb: RTDBClient, uid: str, id_token: str, profile: str) -> None:
    rtdb.patch(f"users/{uid}", id_token, {"activeProfile": profile})


def set_profiles(rtdb: RTDBClient, uid: str, id_token: str, profiles: Dict[str, Any]) -> None:
    rtdb.patch(f"users/{uid}/profiles", id_token, profiles)

def put_user_config(rtdb: RTDBClient, uid: str, id_token: str, config: Dict[str, Any]) -> None:
    rtdb.put(f"users/{uid}", id_token, config)
