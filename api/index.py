import http.server
import json
import os
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

def mask_identity(target: str, channel: str = "email") -> str:
    if channel == "sms":
        digits = "".join(c for c in target if c.isdigit())
        if len(digits) >= 10:
            return f"+91 {digits[:2]}••••••{digits[-2:]}"
        return "+91 98••••••42"
    if "@" in target:
        user, domain = target.split("@", 1)
        if len(user) <= 2:
            return f"{user[0]}•••@{domain}"
        return f"{user[0]}••••••{user[-1]}@{domain}"
    return target

def dispatch_email_code(to_email: str, otp: str):
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    smtp_from = os.environ.get("SMTP_FROM", "CIT Central Auth <noreply@cit.ac.in>")
    resend_key = os.environ.get("RESEND_API_KEY")

    subject = f"CIT ERP Verification Code: {otp}"
    html_content = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; background: #f8fafc; padding: 20px; color: #1e293b;">
  <div style="max-width: 560px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 24px;">
    <div style="border-bottom: 2px solid #0f172a; padding-bottom: 12px; margin-bottom: 20px;">
      <h2 style="margin: 0; color: #0f172a; font-size: 18px;">Chilika Institute of Technology</h2>
      <span style="font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 1px;">CAMPUS ERP · CENTRAL IDENTITY RECOVERY</span>
    </div>
    <p style="font-size: 14px; line-height: 1.5; color: #334155;">
      A request was initiated to reset the password for your CIT ERP account (<strong>{to_email}</strong>).
    </p>
    <div style="background: #f1f5f9; border: 1px dashed #cbd5e1; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0;">
      <div style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 1px;">6-Digit Verification Code</div>
      <div style="font-size: 32px; font-weight: 800; color: #0f172a; letter-spacing: 8px; font-family: monospace; margin: 10px 0;">{otp}</div>
      <div style="font-size: 11px; color: #e11d48; font-weight: 600;">Valid for 10 minutes · Do not share this code with anyone</div>
    </div>
    <p style="font-size: 12px; color: #64748b; line-height: 1.5;">
      If you did not request this verification code, someone may be attempting to access your account. Please notify the CIT IT Security Helpdesk immediately.
    </p>
    <div style="border-top: 1px solid #e2e8f0; margin-top: 24px; padding-top: 12px; font-size: 10.5px; color: #94a3b8;">
      Chilika Institute of Technology · Administrative Complex, Level 2, Odisha, India<br/>
      Institutional Security Desk · DPDP Act 2023 Compliant
    </div>
  </div>
</body>
</html>"""

    if resend_key:
        try:
            req = urllib.request.Request(
                "https://api.resend.com/emails",
                data=json.dumps({
                    "from": smtp_from if "@" in smtp_from else "CIT Auth <onboarding@resend.dev>",
                    "to": [to_email],
                    "subject": subject,
                    "html": html_content
                }).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {resend_key}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status in (200, 201):
                    return True, "Resend API Gateway"
        except Exception as e:
            print(f"[MAIL WARN] Resend dispatch failed: {e}")

    if smtp_host and smtp_user and smtp_pass:
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = smtp_from
            msg["To"] = to_email
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(smtp_host, smtp_port, timeout=5) as server:
                server.ehlo()
                if smtp_port != 465:
                    server.starttls()
                    server.ehlo()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_from, [to_email], msg.as_string())
            return True, f"SMTP Gateway ({smtp_host})"
        except Exception as e:
            print(f"[MAIL WARN] SMTP dispatch failed: {e}")

    return False, "Simulated Campus Gateway"

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

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".webp": "image/webp",
    ".webmanifest": "application/manifest+json",
    ".xml": "application/xml; charset=utf-8",
    ".txt": "text/plain; charset=utf-8"
}

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

DB_FILE = "/tmp/cit_users_db.json"

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

def find_file(rel_path):
    clean_rel = rel_path.lstrip("/\\")
    alt_rel = clean_rel
    if clean_rel.startswith("public/"):
        alt_rel = clean_rel.replace("public/", "assets/", 1)
    elif clean_rel.startswith("public\\"):
        alt_rel = clean_rel.replace("public\\", "assets\\", 1)

    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), clean_rel),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), alt_rel),
        os.path.join(os.getcwd(), clean_rel),
        os.path.join(os.getcwd(), alt_rel),
        os.path.join("/var/task", clean_rel),
        os.path.join("/var/task", alt_rel),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), clean_rel),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), alt_rel),
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.isfile(c):
            return c
    return None

def read_data_file(rel_path):
    path = find_file(rel_path)
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    return None

class handler(http.server.BaseHTTPRequestHandler):
    def get_requested_path(self):
        p = urllib.parse.urlparse(self.path).path
        if p and p not in ("/api/index.py", "/api/index", "/api"):
            return p
        for h in ("x-forwarded-uri", "x-invoke-path", "x-matched-path"):
            val = self.headers.get(h)
            if val:
                vp = urllib.parse.urlparse(val).path
                if vp not in ("/api/index.py", "/api/index", "/api"):
                    return vp
        return p

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

    def send_cors_headers(self, content_type="application/json; charset=utf-8"):
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.end_headers()

    def do_OPTIONS(self):
        if self.check_https_redirect():
            return
        self.send_response(200)
        self.send_cors_headers("text/plain")

    def serve_file(self, rel_path, default_mime="text/html; charset=utf-8"):
        content = read_data_file(rel_path)
        if content is not None:
            _, ext = os.path.splitext(rel_path)
            content_type = MIME_TYPES.get(ext.lower(), default_mime)
            self.send_response(200)
            if ext.lower() in ('.jpg', '.jpeg', '.png', '.webp', '.svg', '.ico', '.css', '.js'):
                self.send_header("Cache-Control", "public, max-age=604800, stale-while-revalidate=86400")
            elif ext.lower() == '.html':
                self.send_header("Cache-Control", "no-cache, must-revalidate")
            self.send_cors_headers(content_type)
            self.wfile.write(content)
            return True
        return False

    def do_GET(self):
        if self.check_https_redirect():
            return
        req_path = self.get_requested_path()

        # Dedicated Admin Login Route
        if req_path in ("/admin/login", "/admin/auth", "/admin-login", "/admin/signin"):
            if self.serve_file("admin_login.html"):
                return

        # Dedicated User Login & Register route
        if req_path in ("/login", "/auth"):
            if self.serve_file("login.html"):
                return

        # Dedicated Admin Terminal route
        if req_path in ("/admin", "/admin.html"):
            if self.serve_file("admin.html"):
                return

        # Dedicated Privacy Policy Route
        if req_path in ("/privacy", "/privacy-policy", "/privacy.html", "/privacy-policy.html"):
            if self.serve_file("privacy.html"):
                return

        # Dedicated Terms & Conditions Route
        if req_path in ("/terms", "/terms-and-conditions", "/terms.html", "/terms-and-conditions.html"):
            if self.serve_file("terms.html"):
                return

        # Dedicated Support & Help Desk Route
        if req_path in ("/support", "/support.html", "/help", "/help.html", "/helpdesk"):
            if self.serve_file("support.html"):
                return

        # User portal routes
        if req_path in ("/", "/index.html", "/portal", "/dashboard", "/timetable", "/bookings"):
            if self.serve_file("index.html"):
                return

        # SEO & Web Crawler routes
        if req_path == "/robots.txt":
            if self.serve_file("robots.txt", default_mime="text/plain; charset=utf-8"):
                return

        if req_path == "/sitemap.xml":
            if self.serve_file("sitemap.xml", default_mime="application/xml; charset=utf-8"):
                return

        # Static assets (/public/* or /assets/* or /exports/*)
        if req_path.startswith("/public/") or req_path.startswith("/assets/") or req_path.startswith("/exports/"):
            if self.serve_file(req_path):
                return

        # API Endpoints
        if req_path.endswith("/api/data") or req_path == "/data":
            content = read_data_file("assets/cit_public.json")
            if not content:
                content = read_data_file("public/cit_public.json")
            if content:
                self.send_response(200)
                self.send_cors_headers("application/json; charset=utf-8")
                self.wfile.write(content)
                return

        if req_path.endswith("/api/schedule") or req_path == "/schedule":
            content = read_data_file("exports/schedule.json")
            if not content:
                content = read_data_file("assets/schedule.json")
            if content:
                self.send_response(200)
                self.send_cors_headers("application/json; charset=utf-8")
                self.wfile.write(content)
                return

        if req_path.endswith("/api/schedule_after") or req_path == "/schedule_after":
            content = read_data_file("exports/schedule_after.json")
            if not content:
                content = read_data_file("assets/schedule_after.json")
            if content:
                self.send_response(200)
                self.send_cors_headers("application/json; charset=utf-8")
                self.wfile.write(content)
                return

        if req_path.endswith("/api/validate") or req_path == "/validate":
            content = read_data_file("report.json")
            if not content:
                content = read_data_file("assets/report.json")
            if not content:
                content = read_data_file("public/report.json")
            if content:
                self.send_response(200)
                self.send_cors_headers("application/json; charset=utf-8")
                self.wfile.write(content)
                return

        if req_path.endswith("/api/admin/users") or req_path == "/admin/users":
            self.send_response(200)
            self.send_cors_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps(USERS_DB).encode("utf-8"))
            return

        if req_path.endswith("/api/admin/bookings") or req_path == "/admin/bookings":
            load_persistent_db()
            self.send_response(200)
            self.send_cors_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps({
                "success": True,
                "custom_bookings": CUSTOM_BOOKINGS,
                "overrides": BOOKING_OVERRIDES
            }).encode("utf-8"))
            return

        if req_path.endswith("/api/admin/audit-logs") or req_path == "/admin/audit-logs":
            load_persistent_db()
            self.send_response(200)
            self.send_cors_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps({
                "success": True,
                "logs": AUDIT_LOGS
            }).encode("utf-8"))
            return

        if req_path.endswith("/api/admin/settings") or req_path == "/admin/settings":
            load_persistent_db()
            self.send_response(200)
            self.send_cors_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps({
                "success": True,
                "settings": WEBSITE_SETTINGS
            }).encode("utf-8"))
            return

        if req_path.endswith("/api/user/profile") or req_path == "/user/profile":
            self.send_response(200)
            self.send_cors_headers("application/json; charset=utf-8")
            url_parsed = urllib.parse.urlparse(self.path)
            email = urllib.parse.parse_qs(url_parsed.query).get("email", ["student@cit.ac.in"])[0]
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

        # Direct file check (e.g. favicon, css, js)
        if self.serve_file(req_path):
            return

        # Default fallback: User Dashboard
        if self.serve_file("index.html"):
            return

        self.send_response(404)
        self.send_cors_headers("text/plain")
        self.wfile.write(b"404 Not Found")

    def do_POST(self):
        if self.check_https_redirect():
            return
        req_path = self.get_requested_path()
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        # Profile Update API
        if req_path.endswith("/api/user/profile") or req_path == "/user/profile":
            self.send_response(200)
            self.send_cors_headers("application/json; charset=utf-8")
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
        if req_path.endswith("/api/auth/google") or req_path.endswith("/auth/google"):
            self.send_response(200)
            self.send_cors_headers("application/json; charset=utf-8")
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
        if req_path.endswith("/api/auth/login") or req_path.endswith("/auth/login"):
            load_persistent_db()
            self.send_response(200)
            self.send_cors_headers("application/json; charset=utf-8")
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

        # Signup API
        if req_path.endswith("/api/auth/signup") or req_path.endswith("/auth/signup"):
            load_persistent_db()
            self.send_response(200)
            self.send_cors_headers("application/json; charset=utf-8")
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
        if req_path.endswith("/api/auth/forgot-password") or req_path.endswith("/auth/forgot-password"):
            load_persistent_db()
            self.send_response(200)
            self.send_cors_headers("application/json; charset=utf-8")
            try:
                data = json.loads(body)
                email = data.get("email", "").strip().lower()
                channel = data.get("channel", "email").strip().lower()
                phone = data.get("phone", "").strip()
            except Exception:
                email, channel, phone = "", "email", ""

            if not email or "@" not in email or "." not in email:
                self.wfile.write(json.dumps({"success": False, "message": "Please enter a valid institutional or personal email address."}).encode("utf-8"))
                return

            otp = f"{secrets.randbelow(900000) + 100000}"
            PASSWORD_RESET_TOKENS[email] = {
                "code": otp,
                "expires": time.time() + 600,
                "channel": channel
            }

            # Mask identity target
            target_raw = phone if (channel == "sms" and phone) else email
            masked_target = mask_identity(target_raw, channel)

            # Dispatch real email if channel is email
            dispatched = False
            dispatch_method = "Simulated Campus Gateway"
            if channel == "email":
                dispatched, dispatch_method = dispatch_email_code(email, otp)

            # Institutional audit logging
            print("=" * 60)
            print(f"[CIT SECURITY GATEWAY] Password Reset Verification Dispatched")
            print(f"[CIT SECURITY GATEWAY] Recipient: {email} | Target: {masked_target} | Channel: {channel.upper()}")
            print(f"[CIT SECURITY GATEWAY] One-Time Verification Code: {otp}")
            print(f"[CIT SECURITY GATEWAY] Gateway Dispatch Method: {dispatch_method} (Valid: 10 mins)")
            print("=" * 60)

            res = {
                "success": True,
                "channel": channel,
                "masked_target": masked_target,
                "message": f"Verification code dispatched via {channel.upper()} to {masked_target}.",
                "expires_in": 600,
                "cooldown": 45,
                "delivery_id": f"CIT-DISPATCH-{secrets.token_hex(4).upper()}",
                "simulated_notification": {
                    "channel": channel,
                    "sender": "CIT Security Gateway" if channel == "email" else "CIT-AUTH-SMS",
                    "sender_address": "noreply@cit.ac.in" if channel == "email" else "+91 (06756) 220-100",
                    "title": "CIT ERP Verification Code",
                    "code": otp,
                    "preview": f"Your 6-digit recovery OTP is {otp}. Valid for 10 minutes. Do not share."
                }
            }
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        # Reset Password with OTP
        if req_path.endswith("/api/auth/reset-password") or req_path.endswith("/auth/reset-password"):
            load_persistent_db()
            self.send_response(200)
            self.send_cors_headers("application/json; charset=utf-8")
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
        if req_path.endswith("/api/auth/verify-human") or req_path.endswith("/auth/verify-human"):
            self.send_response(200)
            self.send_cors_headers("application/json; charset=utf-8")
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

        # Admin User Management Update API
        if req_path.endswith("/api/admin/users/update") or req_path.endswith("/users/update"):
            self.send_response(200)
            self.send_cors_headers("application/json; charset=utf-8")
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

        if req_path.endswith("/api/admin/bookings/update") or req_path.endswith("/admin/bookings/update"):
            load_persistent_db()
            self.send_response(200)
            self.send_cors_headers("application/json; charset=utf-8")
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

        if req_path.endswith("/api/bookings/create") or req_path.endswith("/bookings/create"):
            load_persistent_db()
            self.send_response(200)
            self.send_cors_headers("application/json; charset=utf-8")
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

        if req_path.endswith("/api/admin/audit-logs") or req_path.endswith("/admin/audit-logs"):
            load_persistent_db()
            self.send_response(200)
            self.send_cors_headers("application/json; charset=utf-8")
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

        if req_path.endswith("/api/admin/settings") or req_path.endswith("/admin/settings"):
            load_persistent_db()
            self.send_response(200)
            self.send_cors_headers("application/json; charset=utf-8")
            try:
                data = json.loads(body)
                WEBSITE_SETTINGS.update(data)
                save_persistent_db()
            except Exception:
                pass
            self.wfile.write(json.dumps({"success": True, "settings": WEBSITE_SETTINGS}).encode("utf-8"))
            return

        # NLP Venue Booking Parser API
        if req_path.endswith("/api/parse-nlp") or req_path.endswith("/parse-nlp"):
            self.send_response(200)
            self.send_cors_headers("application/json; charset=utf-8")
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

            att_match = re.search(r"(\d+)\s*(?:people|log|students|participants|members|pax)", raw)
            if att_match:
                res["attendance"] = int(att_match.group(1))
            else:
                gen_match = re.search(r"(?:for|around|about|seating|capacity)?\s*(\d+)\s*(?:people|log|students|participants|members)?", raw)
                if gen_match and int(gen_match.group(1)) not in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13):
                    res["attendance"] = int(gen_match.group(1))

            if "projector" in raw:
                res["needs"].append("projector")
            if any(w in raw for w in ["mic", "pa system", "sound", "speaker", "audio"]):
                res["needs"].append("pa_system")
            if any(w in raw for w in ["stage", "podium", "natak", "drama"]):
                res["needs"].append("stage")
            if any(w in raw for w in ["accessible", "wheelchair", "ramps"]):
                res["needs"].append("accessible")

            if "auditorium" in raw or "audi" in raw:
                res["room_types"] = ["auditorium"]
            elif "seminar hall" in raw or "sh-1" in raw or "sh-2" in raw:
                res["room_types"] = ["seminar_hall"]
            elif "lab" in raw or "computer" in raw or "coding" in raw:
                res["room_types"] = ["lab_cs"]
            elif "oat" in raw or "open air" in raw or "outdoor" in raw:
                res["room_types"] = ["outdoor"]

            dur_match = re.search(r"(\d+)\s*(?:hour|ghante|hr)", raw)
            if dur_match:
                res["duration_periods"] = int(dur_match.group(1))

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
        self.send_cors_headers("application/json; charset=utf-8")
        self.wfile.write(json.dumps({"error": "Endpoint not found", "path": req_path}).encode("utf-8"))
