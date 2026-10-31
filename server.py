import http.server
import socketserver
import json
import os
import subprocess
import urllib.parse
import re
import secrets

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
