import json
import os
import uuid
from datetime import datetime
from flask import session
USERS_FILE = "data/users.json"
SESSIONS_FILE = "data/sessions.json"
def _load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        return json.load(f)
def _save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)
# ---------------- SIGNUP ----------------
def signup_user(email, password, is_student=True):
    data = _load_json(USERS_FILE, {"users": {}})
    if email in data["users"]:
        return False, "User already exists"
    data["users"][email] = {
        "password": password,
        "created_at": datetime.utcnow().isoformat(),
        "status": "pending" if is_student else "approved",
        "role": "student" if is_student else "admin"
    }
    _save_json(USERS_FILE, data)
    return True, "Signup successful. Please wait for admin approval." if is_student else "Signup successful"
# ---------------- LOGIN ----------------
def login_user(email, password):
    users = _load_json(USERS_FILE, {"users": {}})
    if email not in users["users"]:
        return False, "User not found"
    user = users["users"][email]
    if user["password"] != password:
        return False, "Invalid password"
    if user.get("status") == "pending":
        return False, "Your account is pending approval by an admin."
    if user.get("status") == "rejected":
        return False, "Your account registration was rejected."
    session_id = str(uuid.uuid4())
    session["user_email"] = email
    session["session_id"] = session_id
    return True, session_id
# ---------------- SESSION CHECK ----------------
def is_logged_in():
    return "user_email" in session and "session_id" in session
def get_current_user():
    return session.get("user_email"), session.get("session_id")
def get_user_role(email):
    data = _load_json(USERS_FILE, {"users": {}})
    user_info = data["users"].get(email, {})
    return user_info.get("role", "student")
def get_user_details(email):
    data = _load_json(USERS_FILE, {"users": {}})
    user_info = data["users"].get(email, {})
    if not user_info:
        return None
    
    # Extract name from email (before @) and format
    name_part = email.split('@')[0]
    # Convert email username to display name (capitalize first letter, replace dots/underscores with spaces)
    display_name = name_part.replace('.', ' ').replace('_', ' ').title()
    
    # Generate student ID from email and creation date
    created_at = user_info.get("created_at", "")
    if created_at:
        # Extract year from creation date
        year = created_at.split('-')[0]
        # Generate a simple ID from email hash and year
        import hashlib
        email_hash = hashlib.md5(email.encode()).hexdigest()[:6].upper()
        student_id = f"STU-{year}-{email_hash}"
    else:
        student_id = f"STU-{datetime.utcnow().year}-UNKNOWN"
    
    return {
        "email": email,
        "name": display_name,
        "student_id": student_id,
        "role": user_info.get("role", "student"),
        "status": user_info.get("status", "pending"),
        "created_at": user_info.get("created_at", "")
    }
def logout_user():
    session.clear()
def get_pending_users():
    data = _load_json(USERS_FILE, {"users": {}})
    pending = []
    for email, info in data["users"].items():
        if info.get("status") == "pending":
            pending.append({
                "email": email,
                "created_at": info.get("created_at"),
                "role": info.get("role", "student")
            })
    return pending
def update_user_status(email, status):
    data = _load_json(USERS_FILE, {"users": {}})
    if email in data["users"]:
        data["users"][email]["status"] = status
        _save_json(USERS_FILE, data)
        return True
    return False
def get_all_students():
    data = _load_json(USERS_FILE, {"users": {}})
    students = []
    for email, info in data["users"].items():
        if info.get("role") == "student":
            students.append({
                "email": email,
                "status": info.get("status", "pending"),
                "created_at": info.get("created_at")
            })
    return students
def get_all_sessions():
    if not os.path.exists(SESSIONS_FILE):
        return []
    with open(SESSIONS_FILE, "r") as f:
        data = json.load(f)
    all_sessions = []
    for email, user_data in data.items():
        for session in user_data.get("sessions", []):
            session_info = session.copy()
            session_info["email"] = email
            all_sessions.append(session_info)
    # Sort by login_time descending
    all_sessions.sort(key=lambda x: x.get("login_time", ""), reverse=True)
    return all_sessions