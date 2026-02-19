import os
import logging
from typing import Dict, Any, Tuple, Optional
from flask import Flask, request, jsonify
import requests
from requests.exceptions import RequestException, Timeout

# -------------------- Configuration --------------------
class Config:
    BAN_CHECK_URL = "https://ff.garena.com/api/antihack/check_banned"
    PLAYER_INFO_URL = "https://flash-info-cbw4.vercel.app/info"
    PLAYER_INFO_KEY = "Flash"
    DEFAULT_LANG = "en"
    REQUEST_TIMEOUT = 10
    X_REQUESTED_WITH = os.getenv("X_REQUESTED_WITH", "B6FksShzIgjfrYImLpTsadjS86sddhFH")
    USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    CREDIT_TEXT = os.getenv("CREDIT_TEXT", "developed and making this API by @sulav_don1 main channel @sulav_don2")
    API_KEY = os.getenv("API_KEY", "Sulav")

# -------------------- Logging --------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------- Flask App --------------------
app = Flask(__name__)
app.config.from_object(Config)

BAN_CHECK_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "referer": "https://ff.garena.com/en/support/",
    "user-agent": Config.USER_AGENT,
    "x-requested-with": Config.X_REQUESTED_WITH
}

# -------------------- Authentication --------------------
def require_api_key(f):
    def decorated_function(*args, **kwargs):
        key = (request.args.get("key") or request.args.get("Key") or
               request.args.get("KEY") or request.headers.get("X-API-Key"))
        if not key or key != Config.API_KEY:
            return jsonify({"credit": Config.CREDIT_TEXT,
                            "error": "Invalid or missing API key."}), 401
        return f(*args, **kwargs)
    return decorated_function

# -------------------- Helper Functions --------------------
def validate_uid(uid: str) -> Tuple[bool, str]:
    if not uid:
        return False, "UID parameter is required."
    if not uid.isdigit():
        return False, "UID must contain only digits."
    if len(uid) < 8:
        return False, "UID is too short."
    return True, ""

def fetch_player_info(uid: str) -> Dict[str, Any]:
    default = {"level": None, "liked": None, "region": None, "nickname": None}
    params = {"uid": uid, "key": Config.PLAYER_INFO_KEY}
    try:
        resp = requests.get(Config.PLAYER_INFO_URL, params=params, timeout=Config.REQUEST_TIMEOUT)
        if resp.status_code != 200:
            logger.error(f"Player info API returned {resp.status_code}")
            return default
        data = resp.json()
        basic = data.get("basicInfo", {})
        return {
            "level": basic.get("level"),
            "liked": basic.get("liked"),
            "region": basic.get("region"),
            "nickname": basic.get("nickname")
        }
    except Exception as e:
        logger.error(f"Player info fetch failed: {e}")
        return default

def get_ban_message(ban_data: Optional[Dict]) -> str:
    if ban_data is None:
        return "Unable to check ban status"
    if ban_data.get("banned") or ban_data.get("is_banned") or ban_data.get("ban_status") == "banned":
        return "account ban already"
    else:
        return "your id is safe"

def fetch_ban_check(uid: str) -> Tuple[Optional[Dict], Optional[str], int]:
    params = {"lang": Config.DEFAULT_LANG, "uid": uid}
    try:
        resp = requests.get(Config.BAN_CHECK_URL, headers=BAN_CHECK_HEADERS,
                            params=params, timeout=Config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json(), None, 200
    except Timeout:
        return None, "Ban check timeout", 504
    except RequestException as e:
        status = e.response.status_code if hasattr(e, 'response') and e.response else 502
        return None, f"Ban check failed: {str(e)}", status
    except Exception:
        return None, "Internal error", 500

# -------------------- Endpoints --------------------
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "credit": Config.CREDIT_TEXT,
        "usage": "/check?uid=<UID>&key=Sulav",
        "output": "credit, level, liked, region, nickname, ban"
    })

@app.route("/check", methods=["GET"])
@require_api_key
def combined_check():
    uid = request.args.get("uid", "").strip()
    is_valid, err = validate_uid(uid)
    if not is_valid:
        return jsonify({"credit": Config.CREDIT_TEXT, "error": err}), 400

    player = fetch_player_info(uid)
    ban_data, ban_err, status_code = fetch_ban_check(uid)
    if ban_err:
        ban_message = f"Error: {ban_err}"
        http_status = status_code
    else:
        ban_message = get_ban_message(ban_data)
        http_status = 200

    response = {
        "credit": Config.CREDIT_TEXT,
        "level": player["level"],
        "liked": player["liked"],
        "region": player["region"],
        "nickname": player["nickname"],
        "ban": ban_message
    }
    return jsonify(response), http_status

# Vercel needs this line to export the app
# (The file is already named app, so it's fine)