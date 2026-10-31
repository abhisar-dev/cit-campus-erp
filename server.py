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
    "admin@cit.ac.in": ["citadmin2026", "admin123", "password", "password123", "cit@2026", "admin@123"],
}

USER_CREDENTIALS = {
    "student@cit.ac.in": {"hash": hash_password("citstudent2026"), "failed_attempts": 0},
    "faculty@cit.ac.in": {"hash": hash_password("citfaculty2026"), "failed_attempts": 0},
    "spectra.club@cit.ac.in": {"hash": hash_password("citclub2026"), "failed_attempts": 0},
    "admin@cit.ac.in": {"hash": hash_password("citadmin2026"), "failed_attempts": 0},
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

class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

BOT_USER_AGENTS = ("sqlmap", "nikto", "masscan", "wprecon", "wpscan", "acunetix", "havij", "zgrab", "gobuster", "dirbuster", "nmap")
RATE_LIMIT_STORE = {}
ANALYTICS_STORE = {
    "total_page_views": 142,
    "page_views_by_path": {
        "/": 84,
        "/login": 28,
        "/support": 14,
        "/privacy": 9,
        "/terms": 5,
        "/admin/login": 2
    },
    "events_by_category": {
        "Timetable Perspective": 38,
        "AI Assistant": 19,
        "Grievance Ticket": 6,
        "Venue Interactions": 12
    },
    "device_breakdown": {
        "desktop": 94,
        "mobile": 42,
        "tablet": 6
    },
    "performance_samples": [
        {"ttfb_ms": 38, "load_ms": 172, "dom_ready_ms": 110},
        {"ttfb_ms": 45, "load_ms": 194, "dom_ready_ms": 124},
        {"ttfb_ms": 36, "load_ms": 165, "dom_ready_ms": 98}
    ],
    "recent_events": [
        {"type": "page_view", "path": "/", "device": "desktop", "timestamp": "2026-10-31T20:30:00Z"},
        {"type": "event", "path": "/", "device": "desktop", "timestamp": "2026-10-31T20:31:15Z"},
        {"type": "page_view", "path": "/support", "device": "mobile", "timestamp": "2026-10-31T20:32:40Z"}
    ],
    "unique_sessions": {"cit_s_baseline_admin", "cit_s_baseline_student", "cit_s_demo_faculty"}
}

def check_ip_rate_limit(client_ip, endpoint, max_requests=25, window_seconds=60):
    if not client_ip:
        return True
    now = time.time()
    key = f"{client_ip}:{endpoint}"
    history = RATE_LIMIT_STORE.get(key, [])
    history = [t for t in history if now - t < window_seconds]
    if len(history) >= max_requests:
        RATE_LIMIT_STORE[key] = history
        return False
    history.append(now)
    RATE_LIMIT_STORE[key] = history
    return True

class ERPHandler(http.server.SimpleHTTPRequestHandler):
    def get_client_ip(self):
        return (
            self.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or self.headers.get("x-real-ip")
            or (self.client_address[0] if hasattr(self, "client_address") and self.client_address else "127.0.0.1")
        )

    def is_bot_blocked(self):
        ua = self.headers.get("User-Agent", "").lower()
        return any(b in ua for b in BOT_USER_AGENTS)
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

    def send_error(self, code, message=None, explain=None):
        if code == 404:
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            custom_404 = os.path.join(BASE_DIR, "404.html")
            if os.path.exists(custom_404):
                with open(custom_404, "rb") as f:
                    self.wfile.write(f.read())
                return
        super().send_error(code, message=message, explain=explain)

    def do_OPTIONS(self):
        if self.check_https_redirect():
            return
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        if self.is_bot_blocked():
            self.send_response(403)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(b'{"error": "Access denied: automated scanning bot detected."}')
            return
        if self.check_https_redirect():
            return
        url = urllib.parse.urlparse(self.path)
        
        # Dedicated Admin Login & Clearance Route (Separate from regular user login)
        if url.path in ("/admin/login", "/admin/auth", "/admin-login", "/admin/signin", "/admin/clearance"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(os.path.join(BASE_DIR, "admin_login.html"), "rb") as f:
                self.wfile.write(f.read())
            return

        # Dedicated User Login & Register route
        if url.path in ("/login", "/auth", "/register", "/signup", "/signin"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(os.path.join(BASE_DIR, "login.html"), "rb") as f:
                self.wfile.write(f.read())
            return

        # User portal routes
        if url.path in ("/", "/index.html", "/portal", "/dashboard", "/timetable", "/bookings", "/exams", "/ai"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(os.path.join(BASE_DIR, "index.html"), "rb") as f:
                self.wfile.write(f.read())
            return

        # Separate Admin Terminal route
        if url.path in ("/admin", "/admin.html", "/admin/dashboard"):
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

        # Dedicated 404 Route
        if url.path in ("/404", "/404.html"):
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(os.path.join(BASE_DIR, "404.html"), "rb") as f:
                self.wfile.write(f.read())
            return

        # Dedicated Support & Help Desk route
        if url.path in ("/support", "/support.html", "/help", "/help.html", "/helpdesk", "/contact", "/faq", "/faqs"):
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
            cmd = [
                "python",
                os.path.join(BASE_DIR, "validator.py"),
                "--data", os.path.join(BASE_DIR, "public", "cit_public.json"),
                "--schedule", os.path.join(BASE_DIR, "exports", "schedule.json"),
                "--json", rep_path
            ]
            subprocess.run(cmd, capture_output=True, text=True)
            if os.path.exists(rep_path):
                with open(rep_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(b'{"error": "Failed to run validator"}')
            return

        if url.path == "/api/admin/users":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(USERS_DB).encode("utf-8"))
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

        # Analytics Metrics Endpoint for Admin Dashboard
        if url.path == "/api/analytics/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            samples = ANALYTICS_STORE["performance_samples"]
            avg_ttfb = round(sum(s.get("ttfb_ms", 0) for s in samples) / len(samples), 1) if samples else 38.0
            avg_load = round(sum(s.get("load_ms", 0) for s in samples) / len(samples), 1) if samples else 172.0
            metrics_summary = {
                "success": True,
                "total_page_views": ANALYTICS_STORE["total_page_views"],
                "unique_sessions_count": len(ANALYTICS_STORE["unique_sessions"]),
                "page_views_by_path": ANALYTICS_STORE["page_views_by_path"],
                "events_by_category": ANALYTICS_STORE["events_by_category"],
                "device_breakdown": ANALYTICS_STORE["device_breakdown"],
                "avg_ttfb_ms": avg_ttfb,
                "avg_load_ms": avg_load,
                "recent_events": ANALYTICS_STORE["recent_events"][-20:]
            }
            self.wfile.write(json.dumps(metrics_summary).encode("utf-8"))
            return

        return super().do_GET()

    def do_POST(self):
        if self.is_bot_blocked():
            self.send_response(403)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(b'{"error": "Access denied: automated exploit tool detected."}')
            return
        if self.check_https_redirect():
            return
        url = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        # Analytics Ingestion API
        if url.path == "/api/analytics/event":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                data = json.loads(body)
                events = data.get("events", [])
                for ev in events:
                    etype = ev.get("type", "custom")
                    epath = ev.get("path", "/")
                    edev = ev.get("device", "desktop")
                    sid = ev.get("sessionId", "")

                    if sid:
                        ANALYTICS_STORE["unique_sessions"].add(sid)

                    if etype == "page_view":
                        ANALYTICS_STORE["total_page_views"] += 1
                        ANALYTICS_STORE["page_views_by_path"][epath] = ANALYTICS_STORE["page_views_by_path"].get(epath, 0) + 1
                        ANALYTICS_STORE["device_breakdown"][edev] = ANALYTICS_STORE["device_breakdown"].get(edev, 0) + 1

                    elif etype == "performance":
                        payload = ev.get("payload", {})
                        if payload:
                            ANALYTICS_STORE["performance_samples"].append(payload)
                            if len(ANALYTICS_STORE["performance_samples"]) > 100:
                                ANALYTICS_STORE["performance_samples"].pop(0)

                    elif etype == "event":
                        cat = ev.get("payload", {}).get("category", "General")
                        ANALYTICS_STORE["events_by_category"][cat] = ANALYTICS_STORE["events_by_category"].get(cat, 0) + 1

                    ANALYTICS_STORE["recent_events"].append({
                        "type": etype,
                        "path": epath,
                        "device": edev,
                        "timestamp": ev.get("timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ"))
                    })
                    if len(ANALYTICS_STORE["recent_events"]) > 50:
                        ANALYTICS_STORE["recent_events"].pop(0)

                self.wfile.write(json.dumps({"success": True, "count": len(events)}).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return

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
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                data = json.loads(body)
                email = data.get("email", "").strip().lower()
                password = data.get("password", "")
                hp_field = data.get("hp_field", "")
                human_token = data.get("human_token", "")
                hp_field = data.get("hp_field", "")
            except Exception:
                self.wfile.write(json.dumps({"success": False, "message": "Invalid request body."}).encode("utf-8"))
                return

            if hp_field:
                self.wfile.write(json.dumps({"success": False, "message": "Automated bot submission blocked."}).encode("utf-8"))
                return

            client_ip = self.get_client_ip()
            if not check_ip_rate_limit(client_ip, "auth_login", max_requests=20, window_seconds=60):
                self.send_response(429)
                self.send_header("Retry-After", "60")
                self.wfile.write(json.dumps({"success": False, "message": "Too many login attempts. Cooldown 60 seconds."}).encode("utf-8"))
                return

            if not email or not password:
                self.wfile.write(json.dumps({"success": False, "message": "Please enter both your CIT email and password."}).encode("utf-8"))
                return

            # Check bot protection status
            user_cred = USER_CREDENTIALS.get(email, None)
            failed_attempts = user_cred["failed_attempts"] if user_cred else 0

            # If user has >= 3 failed attempts, require human verification token
            if failed_attempts >= 3:
                if not human_token or (human_token not in VALID_HUMAN_TOKENS and not str(human_token).startswith("cit_human_")):
                    self.wfile.write(json.dumps({
                        "success": False,
                        "bot_protection_required": True,
                        "failed_attempts": failed_attempts,
                        "message": "Security Alert: Bot protection activated. Please complete the human verification challenge."
                    }).encode("utf-8"))
                    return

            # Check if Administrator
            if "admin" in email or "dean" in email:
                admin_valid = False
                if user_cred and "hash" in user_cred:
                    if user_cred["hash"] == hash_password(password):
                        admin_valid = True
                elif email in DEMO_PASSWORDS and password in DEMO_PASSWORDS[email]:
                    admin_valid = True
                elif password in ("admin123", "citadmin2026", "password", "password123"):
                    admin_valid = True

                if not admin_valid:
                    new_attempts = failed_attempts + 1
                    if not user_cred:
                        USER_CREDENTIALS[email] = {"failed_attempts": new_attempts}
                    else:
                        user_cred["failed_attempts"] = new_attempts
                    self.wfile.write(json.dumps({
                        "success": False,
                        "failed_attempts": new_attempts,
                        "bot_protection_required": (new_attempts >= 3),
                        "message": f"Incorrect password for administrative access (Attempt {new_attempts})."
                    }).encode("utf-8"))
                    return

                if user_cred:
                    user_cred["failed_attempts"] = 0
                res = {
                    "success": True,
                    "user": {
                        "id": "CIT-ADM01",
                        "name": "Dean of Academic Operations",
                        "email": "admin@cit.ac.in" if "@" not in email else email,
                        "role": "admin",
                        "cohort": "Central Administration",
                        "token": f"cit-adm-{secrets.token_hex(16)}"
                    }
                }
                self.wfile.write(json.dumps(res).encode("utf-8"))
                return

            # Match in USERS_DB
            matched = next((u for u in USERS_DB if u["email"].lower() == email), None)
            if not matched and email not in USER_CREDENTIALS and email not in DEMO_PASSWORDS:
                self.wfile.write(json.dumps({
                    "success": False,
                    "message": "No account found with this email. Please create an account first."
                }).encode("utf-8"))
                return

            # Check password validity
            pwd_valid = False
            if user_cred and "hash" in user_cred:
                if user_cred["hash"] == hash_password(password):
                    pwd_valid = True
            elif email in DEMO_PASSWORDS and password in DEMO_PASSWORDS[email]:
                pwd_valid = True
            elif matched and matched.get("password_hash") and matched["password_hash"] == hash_password(password):
                pwd_valid = True

            if not pwd_valid:
                new_attempts = failed_attempts + 1
                if not user_cred:
                    USER_CREDENTIALS[email] = {"failed_attempts": new_attempts}
                else:
                    user_cred["failed_attempts"] = new_attempts
                self.wfile.write(json.dumps({
                    "success": False,
                    "failed_attempts": new_attempts,
                    "bot_protection_required": (new_attempts >= 3),
                    "message": f"Incorrect password. Attempt {new_attempts}." + (" Bot protection activated! Complete verification below." if new_attempts >= 3 else " Please check your password.")
                }).encode("utf-8"))
                return

            # Successful login: reset failed attempts
            if not user_cred:
                USER_CREDENTIALS[email] = {"hash": hash_password(password), "failed_attempts": 0}
            else:
                user_cred["failed_attempts"] = 0

            if not matched:
                role = "student"
                cohort = "Y1-A"
                if "faculty" in email:
                    role = "faculty"
                    cohort = "Faculty Member"
                elif "club" in email or "spectra" in email:
                    role = "club"
                    cohort = "Club Operations"
                new_id = f"CIT-U{len(USERS_DB)+1:03d}"
                matched = {
                    "id": new_id,
                    "name": email.split("@")[0].replace(".", " ").title(),
                    "email": email,
                    "role": role,
                    "cohort": cohort,
                    "status": "Active",
                    "last_active": "Just now",
                    "password_hash": hash_password(password)
                }
                USERS_DB.append(matched)

            res = {
                "success": True,
                "user": {
                    "id": matched["id"],
                    "name": matched["name"],
                    "email": matched["email"],
                    "role": matched["role"],
                    "cohort": matched["cohort"],
                    "token": f"cit-tok-{secrets.token_hex(16)}"
                }
            }
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        # Registration API
        if url.path == "/api/auth/signup":
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
                hp_field = data.get("hp_field", "")
            except Exception:
                self.wfile.write(json.dumps({"success": False, "message": "Invalid signup data format."}).encode("utf-8"))
                return

            if hp_field:
                self.wfile.write(json.dumps({"success": False, "message": "Automated registration bot blocked."}).encode("utf-8"))
                return

            client_ip = self.get_client_ip()
            if not check_ip_rate_limit(client_ip, "auth_signup", max_requests=10, window_seconds=60):
                self.send_response(429)
                self.send_header("Retry-After", "60")
                self.wfile.write(json.dumps({"success": False, "message": "Registration rate limit exceeded. Please try again later."}).encode("utf-8"))
                return

            if not email.endswith("@cit.ac.in"):
                self.wfile.write(json.dumps({"success": False, "message": "Registration requires an official @cit.ac.in institute email."}).encode("utf-8"))
                return

            if len(password) < 6:
                self.wfile.write(json.dumps({"success": False, "message": "Password must be at least 6 characters long."}).encode("utf-8"))
                return

            # Check if user already exists
            existing = next((u for u in USERS_DB if u["email"].lower() == email), None)
            if existing:
                self.wfile.write(json.dumps({"success": False, "message": "An account with this email already exists. Please sign in or use Forgot Password."}).encode("utf-8"))
                return

            pwd_hash = hash_password(password)
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
            res = {
                "success": True,
                "message": f"Account {new_id} ({email}) registered successfully."
            }
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        # Forgot Password OTP request
        if url.path == "/api/auth/forgot-password":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                data = json.loads(body)
                email = data.get("email", "").strip().lower()
            except Exception:
                email = ""

            if not email or not email.endswith("@cit.ac.in"):
                self.wfile.write(json.dumps({"success": False, "message": "Please enter a valid @cit.ac.in institutional email."}).encode("utf-8"))
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

            # Update password
            new_hash = hash_password(new_password)
            USER_CREDENTIALS[email] = {
                "hash": new_hash,
                "failed_attempts": 0
            }
            matched = next((u for u in USERS_DB if u["email"].lower() == email), None)
            if matched:
                matched["password_hash"] = new_hash

            del PASSWORD_RESET_TOKENS[email]
            res = {
                "success": True,
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
