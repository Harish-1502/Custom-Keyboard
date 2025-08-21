import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("FIREBASE_WEB_API_KEY")
db_url = "https://macro-controller-default-rtdb.firebaseio.com/"

def anonymous_sign_in(API_KEY_USED: str):
    """
    Anonymous sign-in via Firebase Identity Toolkit.
    """
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY_USED}"
    r = requests.post(url,json={"returnSecureToken":True},timeout=10)
    r.raise_for_status()
    data = r.json()
    return data["idToken"],data["localId"],data["refreshToken"]

def refresh_token(API_KEY_USED: str, refresh_token:str):
    """
    Refreshes an expiring ID using the Secure Token API method
    """
    url = f"https://securetoken.googleapis.com/v1/token?key={API_KEY_USED}"
    payload = {
        "grant_type": refresh_token,"refresh_token": refresh_token
        }
    r = requests.post(url,json=payload,timeout=10)
    r.raise_for_status()
    data = r.json()
    return data["idToken"],data["localId"],data["refreshToken"]

def get_config_from_db(db_url: str, uid: str, id_token: str):
    """
    Use a get request to get access to the json in the db. It would return a json in the db if found or nothing if not found
    """
    url = f"{db_url.rstrip('/')}/devices/{uid}/config.json?auth={id_token}"
    r = requests.get(url, timeout = 8)
    print("DEBUG URL:", r.url)
    print("DEBUG TEXT:", r.text)
    # r.raise_for_status()
    return r.json() or {}


idt, uid, rt = anonymous_sign_in(API_KEY)
print("✅ Signed in anonymously")
print("uid:", uid)
print("idToken(len):", len(idt))
print("refreshToken(len):", len(rt))

json = get_config_from_db(db_url,uid,idt)
print("json:", json)


# print("API_KEY from env:", os.getenv("FIREBASE_WEB_API_KEY"))
