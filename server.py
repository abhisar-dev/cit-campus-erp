import http.server
import socketserver
import json
import os
import subprocess
import urllib.parse
import re

PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

USERS_DB = [
    {"id": "CIT-U001", "name": "Aarav Sharma", "email": "student@cit.ac.in", "role": "student", "cohort": "Y1-A", "status": "Active", "last_active": "Just now"},
    {"id": "CIT-U002", "name": "Prof. S. R. Mohanty", "email": "faculty.f19@cit.ac.in", "role": "faculty", "cohort": "Faculty F19 (Physics)", "status": "Active", "last_active": "12m ago"},
    {"id": "CIT-U003", "name": "Rohan Jena (Spectra Lead)", "email": "spectra.club@cit.ac.in", "role": "club", "cohort": "Robotics & AI Club", "status": "Active", "last_active": "1h ago"},
    {"id": "CIT-U004", "name": "Priya Nair", "email": "priya.nair@cit.ac.in", "role": "student", "cohort": "CSE-2", "status": "Active", "last_active": "Yesterday"},
    {"id": "CIT-U005", "name": "Dr. K. Patnaik", "email": "faculty.f07@cit.ac.in", "role": "faculty", "cohort": "Faculty F07 (Leave/Disruption)", "status": "Medical Leave", "last_active": "3d ago"},
    {"id": "CIT-U006", "name": "Ananya Sen", "email": "ananya.sen@cit.ac.in", "role": "student", "cohort": "Y1-B", "status": "Active", "last_active": "4h ago"}
]

class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

class ERPHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
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

        return super().do_GET()

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        
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
                        "token": "cit-adm-sec-98124"
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
                        "token": f"cit-tok-{matched['id']}"
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
                        "token": f"cit-tok-{new_id}"
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
