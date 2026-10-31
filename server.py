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
                # Determine role from email heuristics
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

        if url.path == "/api/auth/signup":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
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
