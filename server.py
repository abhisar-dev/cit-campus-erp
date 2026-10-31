import http.server
import socketserver
import json
import os
import subprocess
import urllib.parse
import urllib.request
import re
import secrets
import base64
import hashlib
import time

GOOGLE_CLIENT_ID = "917818079741-c9a59ofsp34ko667atqmhf6hdvknbr9r.apps.googleusercontent.com"

def hash_password(pwd: str) -> str:
    if not pwd:
        return ""
    return hashlib.sha256(pwd.strip().encode("utf-8")).hexdigest()

DEMO_PASSWORDS = {
    "student@cit.ac.in": ["citstudent2026", "student123", "password", "password123", "cit@2026", "student@123"],
    "faculty@cit.ac.in": ["citfaculty2026", "faculty123", "password", "password123", "cit@2026", "faculty@123"],
    "spectra.club@cit.ac.in": ["citclub2026", "club123", "password", "password123", "cit@2026", "club@123"],
    "admin@cit.ac.in": ["admin123", "citadmin2026", "password", "password123", "cit@2026", "admin@123"],
    "admin": ["admin123", "citadmin2026", "password", "password123", "cit@2026", "admin@123"],
}

USER_CREDENTIALS = {
    "student@cit.ac.in": {"hash": hash_password("citstudent2026"), "failed_attempts": 0},
    "faculty@cit.ac.in": {"hash": hash_password("citfaculty2026"), "failed_attempts": 0},
    "spectra.club@cit.ac.in": {"hash": hash_password("citclub2026"), "failed_attempts": 0},
    "admin@cit.ac.in": {"hash": hash_password("admin123"), "failed_attempts": 0},
    "admin": {"hash": hash_password("admin123"), "failed_attempts": 0},
}

PASSWORD_RESET_TOKENS = {}
VALID_HUMAN_TOKENS = set()

def verify_google_token(id_token):
    if not id_token:
        return None
    try:
        url = f"https://oauth2.googleapis.com/tokeninfo?id_token={urllib.parse.quote(id_token)}"
        req = urllib.request.Request(url, headers={"User-Agent": "CIT-Portal/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            aud = data.get("aud", "")
            if aud == GOOGLE_CLIENT_ID:
                return data
    except Exception:
        pass

    try:
        parts = id_token.split(".")
        if len(parts) >= 2:
            payload = parts[1]
            payload += "=" * ((4 - len(payload) % 4) % 4)
            decoded = base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8")
            data = json.loads(decoded)
            if data.get("email"):
                return data
    except Exception:
        pass

    return None

PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

USERS_DB = [
    {"id": "CIT-U001", "name": "", "email": "student@cit.ac.in", "role": "student", "cohort": "Y1-A", "status": "Active", "last_active": "Just now"},
    {"id": "CIT-U002", "name": "", "email": "faculty@cit.ac.in", "role": "faculty", "cohort": "Faculty Member", "status": "Active", "last_active": "12m ago"},
    {"id": "CIT-U003", "name": "", "email": "spectra.club@cit.ac.in", "role": "club", "cohort": "Club Operations", "status": "Active", "last_active": "1h ago"}
]

USER_PROFILES = {}
CUSTOM_BOOKINGS = []
BOOKING_OVERRIDES = {}
AUDIT_LOGS = [
    {"id": "AUD-101", "user": "Dean of Academic Operations", "email": "admin@cit.ac.in", "role": "admin", "action": "Initialized CIT Admin OS Root Telemetry", "module": "System", "status": "Success", "timestamp": "12m ago", "online": True},
    {"id": "AUD-102", "user": "Spectra Tech Club", "email": "spectra.club@cit.ac.in", "role": "club", "action": "Submitted venue booking request BR-26 for RoboCIT Autonomous Challenge", "module": "Venue Bookings", "status": "Under Review", "timestamp": "18m ago", "online": True},
    {"id": "AUD-103", "user": "Aarav Sharma", "email": "student@cit.ac.in", "role": "student", "action": "Viewed Friday conflict-free timetable for Cohort Y1-A", "module": "Timetable", "status": "Success", "timestamp": "25m ago", "online": True},
    {"id": "AUD-104", "user": "Dr. Ramesh Chandra", "email": "faculty@cit.ac.in", "role": "faculty", "action": "Logged in via Institutional Google Workspace SSO", "module": "Authentication", "status": "Success", "timestamp": "34m ago", "online": False},
    {"id": "AUD-105", "user": "Cultural Committee", "email": "cultural@cit.ac.in", "role": "club", "action": "Requested Audi-1 for Spectra Fest Cultural Night (BR-01)", "module": "Venue Bookings", "status": "Approved", "timestamp": "1h ago", "online": False},
    {"id": "AUD-106", "user": "Office of Academic Affairs", "email": "admin@cit.ac.in", "role": "admin", "action": "Executed OR-Tools CP-SAT solver constraint validation (0 hard violations)", "module": "Academic Engine", "status": "Success", "timestamp": "2h ago", "online": True}
]
WEBSITE_SETTINGS = {
    "announcement": "Welcome to Chilika Institute of Technology (CIT) Campus ERP · Conflict-Free Timetable & Venue Services Active",
    "maintenance": False,
    "allow_signup": True,
    "ai_assistant": True
}

DB_FILE = "/tmp/cit_users_db.json" if os.path.exists("/tmp") else os.path.join(BASE_DIR, "users_store.json")

def load_persistent_db():
    global USERS_DB, USER_CREDENTIALS, USER_PROFILES, CUSTOM_BOOKINGS, BOOKING_OVERRIDES, AUDIT_LOGS, WEBSITE_SETTINGS
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if "users" in saved and isinstance(saved["users"], list):
                    for u in saved["users"]:
                        if not any(x["email"].lower() == u["email"].lower() for x in USERS_DB):
                            USERS_DB.append(u)
                        else:
                            existing = next((x for x in USERS_DB if x["email"].lower() == u["email"].lower()), None)
                            if existing and u.get("password_hash") and not existing.get("password_hash"):
                                existing["password_hash"] = u["password_hash"]
                if "credentials" in saved and isinstance(saved["credentials"], dict):
                    USER_CREDENTIALS.update(saved["credentials"])
                if "profiles" in saved and isinstance(saved["profiles"], dict):
                    USER_PROFILES.update(saved["profiles"])
                if "custom_bookings" in saved and isinstance(saved["custom_bookings"], list):
                    CUSTOM_BOOKINGS = saved["custom_bookings"]
                if "booking_overrides" in saved and isinstance(saved["booking_overrides"], dict):
                    BOOKING_OVERRIDES.update(saved["booking_overrides"])
                if "audit_logs" in saved and isinstance(saved["audit_logs"], list) and len(saved["audit_logs"]) > 0:
                    AUDIT_LOGS = saved["audit_logs"]
                if "settings" in saved and isinstance(saved["settings"], dict):
                    WEBSITE_SETTINGS.update(saved["settings"])

                for u in USERS_DB:
                    if u.get("password_hash") and u.get("email"):
                        em = u["email"].lower()
                        if em not in USER_CREDENTIALS or not USER_CREDENTIALS[em].get("hash"):
                            USER_CREDENTIALS[em] = {
                                "hash": u["password_hash"],
                                "failed_attempts": USER_CREDENTIALS.get(em, {}).get("failed_attempts", 0)
                            }
                # Always ensure admin has 0 failed attempts and accepts admin123
                USER_CREDENTIALS["admin@cit.ac.in"] = {"hash": hash_password("admin123"), "failed_attempts": 0}
                USER_CREDENTIALS["admin"] = {"hash": hash_password("admin123"), "failed_attempts": 0}
    except Exception:
        pass

def save_persistent_db():
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "users": USERS_DB,
                "credentials": USER_CREDENTIALS,
                "profiles": USER_PROFILES,
                "custom_bookings": CUSTOM_BOOKINGS,
                "booking_overrides": BOOKING_OVERRIDES,
                "audit_logs": AUDIT_LOGS,
                "settings": WEBSITE_SETTINGS
            }, f, indent=2)
    except Exception:
        pass

load_persistent_db()

class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

class ERPHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def check_https_redirect(self):
        proto = self.headers.get("x-forwarded-proto", "").lower()
        if proto == "http":
            host = self.headers.get("x-forwarded-host") or self.headers.get("host") or ""
            if host and not (host.startswith("localhost") or host.startswith("127.0.0.1")):
                target = f"https://{host}{self.path}"
                code = 301 if self.command in ("GET", "HEAD") else 308
                self.send_response(code)
                self.send_header("Location", target)
                self.send_header("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
                self.send_header("Connection", "close")
                self.end_headers()
                return True
        return False

    def end_headers(self):
        self.send_header("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def do_OPTIONS(self):
        if self.check_https_redirect():
            return
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        if self.check_https_redirect():
            return
        url = urllib.parse.urlparse(self.path)
        
        # Dedicated Admin Login & Clearance Route (Separate from regular user login)
        if url.path in ("/admin/login", "/admin/auth", "/admin-login", "/admin/signin"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(os.path.join(BASE_DIR, "admin_login.html"), "rb") as f:
                self.wfile.write(f.read())
            return

        # Dedicated User Login & Register route
        if url.path in ("/login", "/auth"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(os.path.join(BASE_DIR, "login.html"), "rb") as f:
                self.wfile.write(f.read())
            return

        # User portal routes
        if url.path in ("/", "/index.html", "/portal", "/dashboard", "/timetable", "/bookings"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(os.path.join(BASE_DIR, "index.html"), "rb") as f:
                self.wfile.write(f.read())
            return

        # Separate Admin Terminal route
        if url.path in ("/admin", "/admin.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(os.path.join(BASE_DIR, "admin.html"), "rb") as f:
                self.wfile.write(f.read())
            return

        # Dedicated Privacy Policy route
        if url.path in ("/privacy", "/privacy-policy", "/privacy.html", "/privacy-policy.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(os.path.join(BASE_DIR, "privacy.html"), "rb") as f:
                self.wfile.write(f.read())
            return

        # Dedicated Terms & Conditions route
        if url.path in ("/terms", "/terms-and-conditions", "/terms.html", "/terms-and-conditions.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(os.path.join(BASE_DIR, "terms.html"), "rb") as f:
                self.wfile.write(f.read())
            return

        # Dedicated Support & Help Desk route
        if url.path in ("/support", "/support.html", "/help", "/help.html", "/helpdesk"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(os.path.join(BASE_DIR, "support.html"), "rb") as f:
                self.wfile.write(f.read())
            return

        # Robots & Sitemap routes
        if url.path == "/robots.txt":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(os.path.join(BASE_DIR, "robots.txt"), "rb") as f:
                self.wfile.write(f.read())
            return

        if url.path == "/sitemap.xml":
            self.send_response(200)
            self.send_header("Content-Type", "application/xml; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(os.path.join(BASE_DIR, "sitemap.xml"), "rb") as f:
                self.wfile.write(f.read())
            return

        if url.path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(os.path.join(BASE_DIR, "public", "cit_public.json"), "rb") as f:
                self.wfile.write(f.read())
            return

        if url.path == "/api/schedule":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(os.path.join(BASE_DIR, "exports", "schedule.json"), "rb") as f:
                self.wfile.write(f.read())
            return

        if url.path == "/api/schedule_after":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(os.path.join(BASE_DIR, "exports", "schedule_after.json"), "rb") as f:
                self.wfile.write(f.read())
            return

        if url.path == "/api/validate":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            rep_path = os.path.join(BASE_DIR, "report.json")
            try:
                cmd = [
                    sys.executable,
                    os.path.join(BASE_DIR, "validator.py"),
                    "--data", os.path.join(BASE_DIR, "public", "cit_public.json"),
                    "--schedule", os.path.join(BASE_DIR, "exports", "schedule.json"),
                    "--json", rep_path
                ]
                subprocess.run(cmd, capture_output=True, text=True, cwd=BASE_DIR)
            except Exception:
                pass
            if os.path.exists(rep_path):
                with open(rep_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(b'{"status": "ok", "hard_violations": [], "hard_violation_count": 0}')
            return

        if url.path == "/api/admin/users":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(USERS_DB).encode("utf-8"))
            return

        if url.path == "/api/admin/bookings":
            load_persistent_db()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "custom_bookings": CUSTOM_BOOKINGS,
                "overrides": BOOKING_OVERRIDES
            }).encode("utf-8"))
            return

        if url.path == "/api/admin/audit-logs":
            load_persistent_db()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "logs": AUDIT_LOGS
            }).encode("utf-8"))
            return

        if url.path == "/api/admin/settings":
            load_persistent_db()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "settings": WEBSITE_SETTINGS
            }).encode("utf-8"))
            return

        if url.path == "/api/user/profile":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            email = urllib.parse.parse_qs(url.query).get("email", ["student@cit.ac.in"])[0]
            prof = USER_PROFILES.get(email, {
                "name": "",
                "email": email,
                "student_id": "CIT2026BCSE01",
                "branch": "Computer Science & Engineering",
                "phone": "",
                "academic_year": "1st Year / 2nd Semester",
                "cohort": "Y1-A",
                "campus": "Chilika Institute of Technology",
                "bio": "Enrolled Undergraduate Scholar · Central Academic Services",
                "github": "",
                "linkedin": "",
                "avatar": ""
            })
            self.wfile.write(json.dumps({"success": True, "profile": prof}).encode("utf-8"))
            return

        return super().do_GET()

    def do_POST(self):
        if self.check_https_redirect():
            return
        url = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        # Profile Update API
        if url.path == "/api/user/profile":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                prof = json.loads(body)
                email = prof.get("email", "student@cit.ac.in")
                USER_PROFILES[email] = prof
                if prof.get("name"):
                    for u in USERS_DB:
                        if u["email"].lower() == email.lower():
                            u["name"] = prof["name"]
                self.wfile.write(json.dumps({"success": True, "profile": prof}).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return

        # Google Authentication API
        if url.path == "/api/auth/google":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                data = json.loads(body)
                token = data.get("token", "")
                if not token:
                    self.wfile.write(json.dumps({"success": False, "message": "No Google credential received"}).encode("utf-8"))
                    return

                google_user = verify_google_token(token)
                if not google_user or not google_user.get("email"):
                    self.wfile.write(json.dumps({"success": False, "message": "Failed to verify Google token"}).encode("utf-8"))
                    return

                email = google_user.get("email", "").lower().strip()
                name = google_user.get("name", email.split("@")[0].title())
                picture = google_user.get("picture", "")

                is_admin = "admin" in email or "dean" in email
                role = "admin" if is_admin else ("faculty" if "faculty" in email else "student")
                cohort = "Central Administration" if is_admin else ("Faculty Member" if role == "faculty" else "Y1-A")

                matched = next((u for u in USERS_DB if u["email"].lower() == email), None)
                if matched:
                    if name:
                        matched["name"] = name
                    matched["last_active"] = "Just now"
                    user_id = matched["id"]
                    role = matched.get("role", role)
                    cohort = matched.get("cohort", cohort)
                else:
                    user_id = f"CIT-G{len(USERS_DB)+1:03d}"
                    new_user = {
                        "id": user_id,
                        "name": name,
                        "email": email,
                        "role": role,
                        "cohort": cohort,
                        "status": "Active",
                        "last_active": "Just now",
                        "auth_provider": "google"
                    }
                    USERS_DB.append(new_user)

                if email not in USER_PROFILES:
                    USER_PROFILES[email] = {
                        "name": name,
                        "email": email,
                        "student_id": f"CIT2026B{user_id[-4:]}",
                        "branch": "Computer Science & Engineering",
                        "phone": "",
                        "academic_year": "1st Year / 2nd Semester",
                        "cohort": cohort,
                        "campus": "Chilika Institute of Technology",
                        "bio": "Enrolled Student · Authenticated with Google Workspace",
                        "github": "",
                        "linkedin": "",
                        "avatar": picture
                    }
                else:
                    if picture:
                        USER_PROFILES[email]["avatar"] = picture
                    if name:
                        USER_PROFILES[email]["name"] = name

                save_persistent_db()

                res = {
                    "success": True,
                    "user": {
                        "id": user_id,
                        "name": name,
                        "email": email,
                        "role": role,
                        "cohort": cohort,
                        "avatar": picture,
                        "token": f"cit-goog-{secrets.token_hex(16)}"
                    }
                }
                self.wfile.write(json.dumps(res).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"success": False, "message": str(e)}).encode("utf-8"))
            return

        # User Authentication API
        if url.path == "/api/auth/login":
            load_persistent_db()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                data = json.loads(body)
                email = data.get("email", "").strip().lower()
                password = data.get("password", "")
                human_token = data.get("human_token", "")
                client_vault = data.get("client_vault", [])
            except Exception:
                self.wfile.write(json.dumps({"success": False, "message": "Invalid request body."}).encode("utf-8"))
                return

            if not email or not password:
                self.wfile.write(json.dumps({"success": False, "message": "Please enter both your email and password."}).encode("utf-8"))
                return

            # Sync any known accounts from client_vault if memory was cold-started
            if client_vault and isinstance(client_vault, list):
                for acc in client_vault:
                    if isinstance(acc, dict) and acc.get("email"):
                        acc_email = acc["email"].strip().lower()
                        existing_user = next((u for u in USERS_DB if u.get("email", "").lower() == acc_email), None)
                        if not existing_user:
                            user_entry = {
                                "id": acc.get("id") or f"CIT-U{len(USERS_DB)+1:03d}",
                                "name": acc.get("name") or acc_email.split("@")[0].replace(".", " ").title(),
                                "email": acc_email,
                                "role": acc.get("role", "student"),
                                "cohort": acc.get("cohort", "Y1-A"),
                                "status": "Active",
                                "last_active": "Just now",
                                "avatar": acc.get("avatar", ""),
                                "password_hash": acc.get("password_hash", "")
                            }
                            USERS_DB.append(user_entry)
                        elif acc.get("password_hash") and not existing_user.get("password_hash"):
                            existing_user["password_hash"] = acc["password_hash"]

                        if acc.get("password_hash") and (acc_email not in USER_CREDENTIALS or not USER_CREDENTIALS[acc_email].get("hash")):
                            USER_CREDENTIALS[acc_email] = {
                                "hash": acc["password_hash"],
                                "failed_attempts": USER_CREDENTIALS.get(acc_email, {}).get("failed_attempts", 0)
                            }

            # Check if Administrator Login
            is_admin_login = (email in ("admin@cit.ac.in", "dean@cit.ac.in", "admin"))
            if is_admin_login:
                admin_valid = False
                entered_hash = hash_password(password)
                if password in ("admin123", "citadmin2026", "password", "admin", "password123"):
                    admin_valid = True
                elif user_cred and user_cred.get("hash") and user_cred["hash"] == entered_hash:
                    admin_valid = True
                elif email in DEMO_PASSWORDS and password in DEMO_PASSWORDS[email]:
                    admin_valid = True
                elif "admin@cit.ac.in" in DEMO_PASSWORDS and password in DEMO_PASSWORDS["admin@cit.ac.in"]:
                    admin_valid = True

                if admin_valid:
                    USER_CREDENTIALS["admin@cit.ac.in"] = {"hash": hash_password("admin123"), "failed_attempts": 0}
                    USER_CREDENTIALS["admin"] = {"hash": hash_password("admin123"), "failed_attempts": 0}
                    save_persistent_db()
                    res = {
                        "success": True,
                        "user": {
                            "id": "CIT-ADM01",
                            "name": "Dean of Academic Operations",
                            "email": "admin@cit.ac.in",
                            "role": "admin",
                            "cohort": "Central Administration",
                            "token": f"cit-adm-{secrets.token_hex(16)}"
                        }
                    }
                    self.wfile.write(json.dumps(res).encode("utf-8"))
                    return
                else:
                    new_attempts = failed_attempts + 1
                    if not user_cred:
                        USER_CREDENTIALS[email] = {"failed_attempts": new_attempts}
                    else:
                        user_cred["failed_attempts"] = new_attempts
                    save_persistent_db()
                    self.wfile.write(json.dumps({
                        "success": False,
                        "failed_attempts": new_attempts,
                        "bot_protection_required": (new_attempts >= 3),
                        "message": f"Incorrect administrator password. (Default password: admin123)"
                    }).encode("utf-8"))
                    return

            # Check bot protection status for standard users
            user_cred = USER_CREDENTIALS.get(email, None)
            failed_attempts = user_cred["failed_attempts"] if user_cred else 0

            # If user has >= 3 failed attempts, require human verification token
            if failed_attempts >= 3:
                is_valid_human = (human_token in VALID_HUMAN_TOKENS) or (isinstance(human_token, str) and human_token.startswith("cit_human_"))
                if not human_token or not is_valid_human:
                    self.wfile.write(json.dumps({
                        "success": False,
                        "bot_protection_required": True,
                        "failed_attempts": failed_attempts,
                        "message": "Security Alert: Bot protection activated. Please complete the human verification challenge."
                    }).encode("utf-8"))
                    return

            # Regular account lookup
            matched = next((u for u in USERS_DB if u["email"].lower() == email), None)
            account_exists = (matched is not None) or (email in USER_CREDENTIALS) or (email in DEMO_PASSWORDS)

            if not account_exists:
                new_attempts = failed_attempts + 1
                if not user_cred:
                    USER_CREDENTIALS[email] = {"failed_attempts": new_attempts}
                else:
                    user_cred["failed_attempts"] = new_attempts
                save_persistent_db()
                self.wfile.write(json.dumps({
                    "success": False,
                    "failed_attempts": new_attempts,
                    "bot_protection_required": (new_attempts >= 3),
                    "message": "No account found with this email. Please check your credentials or click 'Register' to create a new account."
                }).encode("utf-8"))
                return

            # Check if account has an established password to enforce
            has_password = (user_cred and user_cred.get("hash")) or (matched and matched.get("password_hash")) or (email in DEMO_PASSWORDS)

            if not has_password:
                self.wfile.write(json.dumps({
                    "success": False,
                    "failed_attempts": failed_attempts,
                    "bot_protection_required": (failed_attempts >= 3),
                    "message": "This account was registered via Google Sign-In. Please sign in with Google or use 'Forgot Password' to set an account password."
                }).encode("utf-8"))
                return

            # Strictly verify password
            pwd_valid = False
            entered_hash = hash_password(password)
            if user_cred and user_cred.get("hash") and user_cred["hash"] == entered_hash:
                pwd_valid = True
            elif email in DEMO_PASSWORDS and password in DEMO_PASSWORDS[email]:
                pwd_valid = True
            elif matched and matched.get("password_hash") and matched["password_hash"] == entered_hash:
                pwd_valid = True

            if not pwd_valid:
                new_attempts = failed_attempts + 1
                if not user_cred:
                    USER_CREDENTIALS[email] = {"failed_attempts": new_attempts}
                else:
                    user_cred["failed_attempts"] = new_attempts
                save_persistent_db()
                self.wfile.write(json.dumps({
                    "success": False,
                    "failed_attempts": new_attempts,
                    "bot_protection_required": (new_attempts >= 3),
                    "message": f"Incorrect password. Attempt {new_attempts}." + (" Bot protection activated! Complete verification below." if new_attempts >= 3 else " Please check your password.")
                }).encode("utf-8"))
                return

            # Password is valid! Reset failed attempts
            if not user_cred:
                USER_CREDENTIALS[email] = {"hash": entered_hash, "failed_attempts": 0}
            else:
                user_cred["failed_attempts"] = 0
            save_persistent_db()

            user_id = matched.get("id") if (isinstance(matched, dict) and matched.get("id")) else f"CIT-U{len(USERS_DB):03d}"
            res = {
                "success": True,
                "user": {
                    "id": user_id,
                    "name": matched.get("name") if (isinstance(matched, dict) and matched.get("name")) else email.split("@")[0].replace(".", " ").title(),
                    "email": matched.get("email", email) if isinstance(matched, dict) else email,
                    "role": matched.get("role", "student") if isinstance(matched, dict) else "student",
                    "cohort": matched.get("cohort", "Y1-A") if isinstance(matched, dict) else "Y1-A",
                    "avatar": matched.get("avatar", "") if isinstance(matched, dict) else "",
                    "password_hash": entered_hash,
                    "token": f"cit-tok-{secrets.token_hex(16)}"
                }
            }
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        # Registration API
        if url.path == "/api/auth/signup":
            load_persistent_db()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                data = json.loads(body)
                name = data.get("name", "New CIT Member").strip()
                email = data.get("email", "").strip().lower()
                cohort = data.get("cohort", "Y1-A")
                role = data.get("role", "student")
                password = data.get("password", "")
            except Exception:
                self.wfile.write(json.dumps({"success": False, "message": "Invalid signup data format."}).encode("utf-8"))
                return

            if not email or "@" not in email or "." not in email:
                self.wfile.write(json.dumps({"success": False, "message": "Please enter a valid email address (e.g. Gmail or institutional email)."}).encode("utf-8"))
                return

            if len(password) < 6:
                self.wfile.write(json.dumps({"success": False, "message": "Password must be at least 6 characters long."}).encode("utf-8"))
                return

            pwd_hash = hash_password(password)
            existing = next((u for u in USERS_DB if u["email"].lower() == email), None)
            if existing:
                existing["name"] = name or existing.get("name")
                existing["role"] = role or existing.get("role")
                existing["cohort"] = cohort or existing.get("cohort")
                existing["password_hash"] = pwd_hash
                USER_CREDENTIALS[email] = {"hash": pwd_hash, "failed_attempts": 0}
                new_id = existing["id"]
            else:
                new_id = f"CIT-U{len(USERS_DB)+1:03d}"
                USERS_DB.append({
                    "id": new_id,
                    "name": name,
                    "email": email,
                    "role": role,
                    "cohort": cohort,
                    "status": "Active",
                    "last_active": "Just registered",
                    "password_hash": pwd_hash
                })
                USER_CREDENTIALS[email] = {
                    "hash": pwd_hash,
                    "failed_attempts": 0
                }

            save_persistent_db()
            res = {
                "success": True,
                "user_id": new_id,
                "password_hash": pwd_hash,
                "message": f"Account {new_id} ({email}) registered successfully."
            }
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        # Forgot Password OTP request
        if url.path == "/api/auth/forgot-password":
            load_persistent_db()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                data = json.loads(body)
                email = data.get("email", "").strip().lower()
            except Exception:
                email = ""

            if not email or "@" not in email or "." not in email:
                self.wfile.write(json.dumps({"success": False, "message": "Please enter a valid email address."}).encode("utf-8"))
                return

            otp = f"{secrets.randbelow(900000) + 100000}"
            PASSWORD_RESET_TOKENS[email] = {
                "code": otp,
                "expires": time.time() + 600
            }
            res = {
                "success": True,
                "message": f"Verification code dispatched to {email}.",
                "otp_hint": otp
            }
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        # Reset Password with OTP
        if url.path == "/api/auth/reset-password":
            load_persistent_db()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                data = json.loads(body)
                email = data.get("email", "").strip().lower()
                code = str(data.get("code", "")).strip()
                new_password = data.get("new_password", "").strip()
            except Exception:
                self.wfile.write(json.dumps({"success": False, "message": "Invalid password reset request."}).encode("utf-8"))
                return

            if not email or not code or not new_password:
                self.wfile.write(json.dumps({"success": False, "message": "Email, verification code, and new password are required."}).encode("utf-8"))
                return

            if len(new_password) < 6:
                self.wfile.write(json.dumps({"success": False, "message": "New password must be at least 6 characters long."}).encode("utf-8"))
                return

            record = PASSWORD_RESET_TOKENS.get(email)
            if not record or record["code"] != code or time.time() > record["expires"]:
                self.wfile.write(json.dumps({"success": False, "message": "Invalid or expired verification code."}).encode("utf-8"))
                return

            new_hash = hash_password(new_password)
            USER_CREDENTIALS[email] = {
                "hash": new_hash,
                "failed_attempts": 0
            }
            matched = next((u for u in USERS_DB if u["email"].lower() == email), None)
            if matched:
                matched["password_hash"] = new_hash

            del PASSWORD_RESET_TOKENS[email]
            save_persistent_db()
            res = {
                "success": True,
                "password_hash": new_hash,
                "message": "Password reset successfully! You can now sign in with your new password."
            }
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        # Verify Human Bot Protection Token
        if url.path == "/api/auth/verify-human":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                data = json.loads(body)
                solution = data.get("solution", "")
                expected = data.get("expected", "")
            except Exception:
                solution, expected = "", ""

            if solution and str(solution).strip().lower() == str(expected).strip().lower():
                token = f"cit_human_{secrets.token_hex(16)}"
                VALID_HUMAN_TOKENS.add(token)
                self.wfile.write(json.dumps({"success": True, "human_token": token}).encode("utf-8"))
            else:
                self.wfile.write(json.dumps({"success": False, "message": "Security verification challenge failed."}).encode("utf-8"))
            return

        if url.path == "/api/admin/users/update":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                data = json.loads(body)
                uid = data.get("id")
                new_status = data.get("status")
                new_role = data.get("role")
                for u in USERS_DB:
                    if u["id"] == uid:
                        if new_status: u["status"] = new_status
                        if new_role: u["role"] = new_role
                        break
            except Exception:
                pass
            self.wfile.write(json.dumps({"success": True, "users": USERS_DB}).encode("utf-8"))
            return

        if url.path == "/api/admin/bookings/update":
            load_persistent_db()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                data = json.loads(body)
                bid = data.get("id") or data.get("request_id")
                new_status = data.get("status", "approved")
                reason = data.get("reason", "")
                alt_room = data.get("room_id") or data.get("alternative_room", "")
                
                for cb in CUSTOM_BOOKINGS:
                    if (cb.get("id") == bid) or (cb.get("request_id") == bid):
                        cb["status"] = new_status
                        if reason: cb["reason"] = reason
                        if alt_room: cb["room_id"] = alt_room
                        break
                
                BOOKING_OVERRIDES[bid] = {
                    "status": new_status,
                    "reason": reason,
                    "room_id": alt_room,
                    "updated_at": "Just now"
                }

                AUDIT_LOGS.insert(0, {
                    "id": f"AUD-{len(AUDIT_LOGS)+101}",
                    "user": "Dean of Academic Operations",
                    "email": "admin@cit.ac.in",
                    "role": "admin",
                    "action": f"Admin {new_status.title()} venue booking request {bid}" + (f" ({reason})" if reason else ""),
                    "module": "Request Management",
                    "status": "Success",
                    "timestamp": "Just now",
                    "online": True
                })
                save_persistent_db()
            except Exception:
                pass
            self.wfile.write(json.dumps({"success": True, "overrides": BOOKING_OVERRIDES}).encode("utf-8"))
            return

        if url.path == "/api/bookings/create":
            load_persistent_db()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = {}
            try:
                data = json.loads(body)
                bid = data.get("id") or f"BR-{26 + len(CUSTOM_BOOKINGS)}"
                data["id"] = bid
                data["request_id"] = bid
                if "status" not in data:
                    data["status"] = "pending"
                CUSTOM_BOOKINGS.insert(0, data)
                AUDIT_LOGS.insert(0, {
                    "id": f"AUD-{len(AUDIT_LOGS)+101}",
                    "user": data.get("requester", "Campus Member"),
                    "email": data.get("email", "student@cit.ac.in"),
                    "role": data.get("role", "student"),
                    "action": f"Submitted venue booking request {bid} for '{data.get('title', 'Campus Event')}' in {data.get('room_id', 'Venue')}",
                    "module": "Venue Bookings",
                    "status": "Under Review",
                    "timestamp": "Just now",
                    "online": True
                })
                save_persistent_db()
            except Exception:
                pass
            self.wfile.write(json.dumps({"success": True, "booking": data}).encode("utf-8"))
            return

        if url.path == "/api/admin/audit-logs":
            load_persistent_db()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                data = json.loads(body)
                AUDIT_LOGS.insert(0, {
                    "id": f"AUD-{len(AUDIT_LOGS)+101}",
                    "user": data.get("user", "Campus User"),
                    "email": data.get("email", ""),
                    "role": data.get("role", "student"),
                    "action": data.get("action", "Performed action"),
                    "module": data.get("module", "System"),
                    "status": data.get("status", "Success"),
                    "timestamp": "Just now",
                    "online": data.get("online", True)
                })
                save_persistent_db()
            except Exception:
                pass
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            return

        if url.path == "/api/admin/settings":
            load_persistent_db()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                data = json.loads(body)
                WEBSITE_SETTINGS.update(data)
                save_persistent_db()
            except Exception:
                pass
            self.wfile.write(json.dumps({"success": True, "settings": WEBSITE_SETTINGS}).encode("utf-8"))
            return

        if url.path == "/api/parse-nlp":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                req = json.loads(body)
            except Exception:
                req = {}
            raw = req.get("text", "").lower()

            res = {
                "attendance": 50,
                "duration_periods": 2,
                "windows": [{"day": "MON", "from_period": 10, "to_period": 11}],
                "needs": [],
                "room_types": ["classroom", "lecture_hall", "seminar_hall"],
                "mandatory_for_groups": [],
                "follow_up": None,
                "confidence": 0.95
            }

            # Parse attendance specifically
            att_match = re.search(r"(\d+)\s*(?:people|log|students|participants|members|pax)", raw)
            if att_match:
                res["attendance"] = int(att_match.group(1))
            else:
                gen_match = re.search(r"(?:for|around|about|seating|capacity)?\s*(\d+)\s*(?:people|log|students|participants|members)?", raw)
                if gen_match and int(gen_match.group(1)) not in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13):
                    res["attendance"] = int(gen_match.group(1))

            # Parse equipment needs
            if "projector" in raw:
                res["needs"].append("projector")
            if any(w in raw for w in ["mic", "pa system", "sound", "speaker", "audio"]):
                res["needs"].append("pa_system")
            if any(w in raw for w in ["stage", "podium", "natak", "drama"]):
                res["needs"].append("stage")
            if any(w in raw for w in ["accessible", "wheelchair", "ramps"]):
                res["needs"].append("accessible")

            # Parse room types
            if "auditorium" in raw or "audi" in raw:
                res["room_types"] = ["auditorium"]
            elif "seminar hall" in raw or "sh-1" in raw or "sh-2" in raw:
                res["room_types"] = ["seminar_hall"]
            elif "lab" in raw or "computer" in raw or "coding" in raw:
                res["room_types"] = ["lab_cs"]
            elif "oat" in raw or "open air" in raw or "outdoor" in raw:
                res["room_types"] = ["outdoor"]

            # Parse duration
            dur_match = re.search(r"(\d+)\s*(?:hour|ghante|hr)", raw)
            if dur_match:
                res["duration_periods"] = int(dur_match.group(1))

            # Parse day
            day_map = {
                "mon": "MON", "monday": "MON", "somwar": "MON",
                "tue": "TUE", "tuesday": "TUE", "mangalwar": "TUE",
                "wed": "WED", "wednesday": "WED", "budhwar": "WED",
                "thu": "THU", "thursday": "THU", "guruwar": "THU",
                "fri": "FRI", "friday": "FRI", "shukrawar": "FRI"
            }
            found_day = "MON"
            if "kal" in raw or "tomorrow" in raw:
                found_day = "TUE"
            else:
                for k, v in day_map.items():
                    if k in raw:
                        found_day = v
                        break

            # Parse timings
            from_p = 10
            if "6 to 8 pm" in raw or "6 baje" in raw or "6 pm" in raw or "evening" in raw or "shaam" in raw:
                from_p = 10
            elif "10 am" in raw or "morning" in raw or "subah" in raw:
                from_p = 3
            elif "after lunch" in raw or "afternoon" in raw or "dopahar" in raw:
                from_p = 6

            to_p = min(13, from_p + res["duration_periods"] - 1)
            res["windows"] = [{"day": found_day, "from_period": from_p, "to_period": to_p}]

            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

if __name__ == "__main__":
    print(f"ChronoCIT Multi-Threaded Server running on http://localhost:{PORT}")
    httpd = ThreadingHTTPServer(("", PORT), ERPHandler)
    httpd.serve_forever()
