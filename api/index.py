import http.server
import json
import os
import urllib.parse
import urllib.request
import re
import secrets
import base64

GOOGLE_CLIENT_ID = "917818079741-c9a59ofsp34ko667atqmhf6hdvknbr9r.apps.googleusercontent.com"

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
    ".webmanifest": "application/manifest+json"
}

USERS_DB = [
    {"id": "CIT-U001", "name": "", "email": "student@cit.ac.in", "role": "student", "cohort": "Y1-A", "status": "Active", "last_active": "Just now"},
    {"id": "CIT-U002", "name": "", "email": "faculty@cit.ac.in", "role": "faculty", "cohort": "Faculty Member", "status": "Active", "last_active": "12m ago"},
    {"id": "CIT-U003", "name": "", "email": "spectra.club@cit.ac.in", "role": "club", "cohort": "Club Operations", "status": "Active", "last_active": "1h ago"}
]

USER_PROFILES = {}

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
            self.send_response(200)
            self.send_cors_headers("application/json; charset=utf-8")
            try:
                data = json.loads(body)
                email = data.get("email", "").strip()
            except Exception:
                email = "student@cit.ac.in"

            # Check if Administrator
            if "admin" in email.lower() or "dean" in email.lower():
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
            matched = next((u for u in USERS_DB if u["email"].lower() == email.lower()), None)
            if matched:
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
            else:
                role = "student"
                cohort = "Y1-A"
                if "faculty" in email:
                    role = "faculty"
                    cohort = "Faculty Member"
                elif "club" in email or "spectra" in email:
                    role = "club"
                    cohort = "Club Operations"

                new_id = f"CIT-U{len(USERS_DB)+1:03d}"
                new_user = {
                    "id": new_id,
                    "name": email.split("@")[0].replace(".", " ").title(),
                    "email": email,
                    "role": role,
                    "cohort": cohort,
                    "status": "Active",
                    "last_active": "Just now"
                }
                USERS_DB.append(new_user)
                res = {
                    "success": True,
                    "user": {
                        "id": new_id,
                        "name": new_user["name"],
                        "email": new_user["email"],
                        "role": new_user["role"],
                        "cohort": new_user["cohort"],
                        "token": f"cit-tok-{secrets.token_hex(16)}"
                    }
                }

            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        # Signup API
        if req_path.endswith("/api/auth/signup") or req_path.endswith("/auth/signup"):
            self.send_response(200)
            self.send_cors_headers("application/json; charset=utf-8")
            try:
                data = json.loads(body)
                name = data.get("name", "New CIT Member")
                email = data.get("email", "user@cit.ac.in")
                cohort = data.get("cohort", "Y1-A")
                role = data.get("role", "student")
            except Exception:
                name, email, cohort, role = "New CIT Member", "user@cit.ac.in", "Y1-A", "student"

            new_id = f"CIT-U{len(USERS_DB)+1:03d}"
            USERS_DB.append({
                "id": new_id,
                "name": name,
                "email": email,
                "role": role,
                "cohort": cohort,
                "status": "Active",
                "last_active": "Just registered"
            })
            res = {
                "success": True,
                "message": f"Account {new_id} ({email}) created successfully."
            }
            self.wfile.write(json.dumps(res).encode("utf-8"))
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
