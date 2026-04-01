import json
import os
from datetime import datetime

SESSIONS_FILE = "data/sessions.json"


def _load_sessions():
    if not os.path.exists(SESSIONS_FILE):
        return {}
    with open(SESSIONS_FILE, "r") as f:
        return json.load(f)


def _save_sessions(data):
    with open(SESSIONS_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ---------------- START SESSION ----------------
def start_session(email, session_id):
    data = _load_sessions()

    if email not in data:
        data[email] = {"sessions": []}

    data[email]["sessions"].append({
        "session_id": session_id,
        "login_time": datetime.utcnow().isoformat(),
        "logout_time": None,
        "activities": []
    })

    _save_sessions(data)


# ---------------- LOG ACTIVITY ----------------
def log_activity(email, session_id, activity_type, details=None):
    data = _load_sessions()

    if email not in data:
        return

    for s in reversed(data[email]["sessions"]):
        if s["session_id"] == session_id:
            s["activities"].append({
                "type": activity_type,
                "time": datetime.utcnow().isoformat(),
                "details": details
            })
            break

    _save_sessions(data)


# ---------------- END SESSION ----------------
def end_session(email, session_id):
    data = _load_sessions()

    if email not in data:
        return

    for s in data[email]["sessions"]:
        if s["session_id"] == session_id:
            s["logout_time"] = datetime.utcnow().isoformat()
            break

    _save_sessions(data)
