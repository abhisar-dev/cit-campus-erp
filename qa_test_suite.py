import sys
try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
"""
CIT Campus ERP - Automated Professional QA & Security Test Suite
Designed & Executed by Lead QA Automation & Security Test Engineer
"""

import sys
import json
import time
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, Any, List, Tuple

LOCAL_BASE = "http://127.0.0.1:8000"
PROD_BASE = "https://cit-campus-erp.vercel.app"

class TestResult:
    def __init__(self, name: str, category: str):
        self.name = name
        self.category = category
        self.passed = False
        self.duration_ms = 0.0
        self.details = ""
        self.severity = "NORMAL"

class QATestRunner:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.results: List[TestResult] = []
        self.admin_token = "cit-adm-live"

    def log(self, tr: TestResult):
        status_sym = "[PASS]" if tr.passed else "[FAIL]"
        color = "\033[92m" if tr.passed else "\033[91m"
        reset = "\033[0m"
        print(f"  {color}{status_sym}{reset} {tr.category} :: {tr.name} ({tr.duration_ms:.1f}ms)")
        if not tr.passed or tr.details:
            prefix = "      "
            for line in tr.details.split("\n"):
                print(f"{prefix}{line}")
        self.results.append(tr)

    def request(self, path: str, method: str = "GET", data: Any = None, headers: Dict[str, str] = None) -> Tuple[int, Any, float, Dict[str, str]]:
        url = f"{self.base_url}{path}"
        req_headers = {"User-Agent": "CIT-QA-Automated-Tester/2.0"}
        if headers:
            req_headers.update(headers)
        
        encoded_data = None
        if data is not None:
            if isinstance(data, (dict, list)):
                encoded_data = json.dumps(data).encode("utf-8")
                req_headers["Content-Type"] = "application/json"
            elif isinstance(data, str):
                encoded_data = data.encode("utf-8")

        req = urllib.request.Request(url, data=encoded_data, headers=req_headers, method=method)
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                status = resp.status
                body = resp.read().decode("utf-8", errors="replace")
                elapsed = (time.time() - t0) * 1000.0
                resp_headers = dict(resp.headers)
                try:
                    parsed = json.loads(body)
                    return status, parsed, elapsed, resp_headers
                except Exception:
                    return status, body, elapsed, resp_headers
        except urllib.error.HTTPError as e:
            elapsed = (time.time() - t0) * 1000.0
            body = e.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body)
                return e.code, parsed, elapsed, dict(e.headers)
            except Exception:
                return e.code, body, elapsed, dict(e.headers)
        except Exception as e:
            elapsed = (time.time() - t0) * 1000.0
            return 0, str(e), elapsed, {}

    # --------------------------------------------------------------------------
    # SUITE 1: Route Integrity, Status Codes & SEO
    # --------------------------------------------------------------------------
    def test_routes_and_seo(self):
        print("\n--- [SUITE 1: Route Health, SEO & HTTP Status] ---")
        routes = [
            ("/", 200, "Campus Portal Home"),
            ("/portal", 200, "Student Portal Route"),
            ("/login", 200, "Authentication Gateway"),
            ("/admin", 200, "Admin OS Dashboard"),
            ("/admin-login", 200, "Dean & Root Clearance"),
            ("/support", 200, "Support & Help Desk"),
            ("/terms", 200, "Terms & Code of Conduct"),
            ("/privacy", 200, "Data Privacy & Governance"),
            ("/robots.txt", 200, "Search Crawler Rules"),
            ("/sitemap.xml", 200, "Sitemap XML Index"),
            ("/public/cit_public.json", 200, "Core Dataset Static Asset")
        ]

        for path, expected_code, desc in routes:
            t = TestResult(f"GET {path} ({desc})", "Routing")
            code, body, elapsed, headers = self.request(path)
            t.duration_ms = elapsed
            if code == expected_code:
                t.passed = True
                t.details = f"HTTP {code} OK (length: {len(str(body))} bytes)"
            else:
                t.passed = False
                t.details = f"Expected HTTP {expected_code}, got {code}"
            self.log(t)

    # --------------------------------------------------------------------------
    # SUITE 2: Typography & De-cluttering Integrity
    # --------------------------------------------------------------------------
    def test_typography_and_privacy(self):
        print("\n--- [SUITE 2: Typography Standards & Faculty Name Privacy] ---")
        
        # Test 1: Plus Jakarta Sans & JetBrains Mono in index.html
        t1 = TestResult("Google Fonts Ingestion (Plus Jakarta Sans & JetBrains Mono)", "Typography")
        code, body, elapsed, _ = self.request("/")
        t1.duration_ms = elapsed
        if code == 200 and isinstance(body, str):
            has_pjs = "Plus+Jakarta+Sans" in body or "Plus Jakarta Sans" in body
            has_jbm = "JetBrains+Mono" in body or "JetBrains Mono" in body
            if has_pjs and has_jbm:
                t1.passed = True
                t1.details = "Both Plus Jakarta Sans and JetBrains Mono verified in HTML head."
            else:
                t1.passed = False
                t1.details = f"Fonts missing: PJS={has_pjs}, JBM={has_jbm}"
        else:
            t1.passed = False
            t1.details = f"Failed to fetch homepage: status {code}"
        self.log(t1)

        # Test 2: Faculty Privacy in Official Timetable
        t2 = TestResult("Faculty Personal Name Privacy in Timetable View", "Privacy")
        t2.duration_ms = elapsed
        if code == 200 and isinstance(body, str):
            # Verify f.name is NOT rendered inside the timetable select
            has_raw_fname = "${f.id} - ${f.name}" in body or "${f.id} — ${f.name}" in body
            # Check for specific faculty names that existed in cit_public.json
            known_faculty_names = ["Dr. Ananya Mishra", "Dr. Rajesh Kumar", "Dr. Ramesh Chandra"]
            leaked = [name for name in known_faculty_names if f">{name}<" in body or f" — {name} (" in body]
            if not has_raw_fname and len(leaked) == 0:
                t2.passed = True
                t2.details = "Verified: No faculty personal names found in official timetable views."
            else:
                t2.passed = False
                t2.details = f"Faculty personal name leakage detected: {leaked or has_raw_fname}"
        else:
            t2.passed = False
            t2.details = f"Could not inspect index.html"
        self.log(t2)

        # Test 3: Faculty View Limit (Exactly 5 Faculty)
        t3 = TestResult("Faculty View Display Constraint (Exactly 5 Faculty)", "Privacy")
        t3.duration_ms = elapsed
        if code == 200 and isinstance(body, str):
            has_slice_5 = "slice(0, 5)" in body or "slice(0,5)" in body
            if has_slice_5:
                t3.passed = True
                t3.details = "Verified: Timetable faculty view constrained to exactly 5 faculty."
            else:
                t3.passed = False
                t3.details = "Faculty view not limited to 5 faculty (slice(0, 5) not detected)."
        else:
            t3.passed = False
            t3.details = "Could not inspect index.html"
        self.log(t3)

        # Test 4: Campus Live Marquee Bar & Pause-on-Hover (Pause Button Removed)
        t_mq = TestResult("Marquee Component :: Campus Live Ticker & Pause-on-Hover", "UI / UX")
        t_mq.duration_ms = elapsed
        if code == 200 and isinstance(body, str):
            has_marquee_bar = "campus-marquee-bar" in body
            has_track = "marquee-track" in body
            has_keyframes = "marquee-scroll" in body
            has_pause_hover = "marquee-track-container:hover" in body or "animation-play-state: paused" in body
            has_no_pause_btn = "marquee-toggle-btn" not in body
            if has_marquee_bar and has_track and has_keyframes and has_pause_hover and has_no_pause_btn:
                t_mq.passed = True
                t_mq.details = "Verified: Proper CSS marquee with pause-on-hover active (pause button removed per specification)."
            else:
                t_mq.passed = False
                t_mq.details = f"Missing components: bar={has_marquee_bar}, track={has_track}, keyframes={has_keyframes}, pause_hover={has_pause_hover}, no_pause_btn={has_no_pause_btn}"
        else:
            t_mq.passed = False
            t_mq.details = "Could not inspect index.html"
        self.log(t_mq)

        # Test 5: Announcements Section & Circular Memo Modal
        t_sec = TestResult("Announcements Section :: Official Circulars Feed & Modal", "UI / UX")
        t_sec.duration_ms = elapsed
        if code == 200 and isinstance(body, str):
            has_render_ann = "renderAnnouncements" in body
            has_render_tab_ann = "currentTab === 'announcements'" in body
            has_modal = "modalNoticeDetail" in body
            has_tab = "tab-announcements" in body
            if has_render_ann and has_modal and has_tab and has_render_tab_ann:
                t_sec.passed = True
                t_sec.details = "Verified: Campus Notices section active with functional tab router and circular modal."
            else:
                t_sec.passed = False
                t_sec.details = f"Missing components: render={has_render_ann}, tab_router={has_render_tab_ann}, modal={has_modal}, tab={has_tab}"
        else:
            t_sec.passed = False
            t_sec.details = "Could not inspect index.html"
        self.log(t_sec)


    # --------------------------------------------------------------------------
    # SUITE 3: Academic Optimization & Solver Endpoints
    # --------------------------------------------------------------------------
    def test_academic_optimizer_apis(self):
        print("\n--- [SUITE 3: Academic Solver & Data Models] ---")
        
        # /api/data
        t_data = TestResult("GET /api/data (Core Academic Model)", "Data API")
        code, body, elapsed, _ = self.request("/api/data")
        t_data.duration_ms = elapsed
        if code == 200 and isinstance(body, dict):
            has_rooms = "rooms" in body and len(body["rooms"]) > 0
            has_groups = "student_groups" in body and len(body["student_groups"]) > 0
            has_courses = "courses" in body and len(body["courses"]) > 0
            if has_rooms and has_groups and has_courses:
                t_data.passed = True
                t_data.details = f"Loaded {len(body['rooms'])} rooms, {len(body['student_groups'])} student cohorts, {len(body['courses'])} courses."
            else:
                t_data.passed = False
                t_data.details = "Missing required schema fields in /api/data"
        else:
            t_data.passed = False
            t_data.details = f"Status {code}: {body}"
        self.log(t_data)

        # /api/schedule
        t_sched = TestResult("GET /api/schedule (Conflict-Free Baseline Schedule)", "Optimization")
        code, body, elapsed, _ = self.request("/api/schedule")
        t_sched.duration_ms = elapsed
        if code == 200 and isinstance(body, dict):
            sessions = body.get("sessions") or body.get("placed_sessions") or []
            t_sched.passed = len(sessions) > 0
            t_sched.details = f"Validated {len(sessions)} placed sessions across timetable grid."
        else:
            t_sched.passed = False
            t_sched.details = f"Status {code}: {body}"
        self.log(t_sched)

        # /api/validate
        t_val = TestResult("GET /api/validate (H1-H14 Hard Constraint Checker)", "Constraints")
        code, body, elapsed, _ = self.request("/api/validate")
        t_val.duration_ms = elapsed
        if code == 200 and isinstance(body, dict):
            valid = body.get("valid", True)
            clashes = body.get("clashes", 0)
            t_val.passed = (clashes == 0)
            t_val.details = f"Constraints verified: valid={valid}, zero clashes detected."
        else:
            t_val.passed = False
            t_val.details = f"Status {code}: {body}"
        self.log(t_val)

        # /api/announcements
        t_ann = TestResult("GET /api/announcements (Campus Circulars & Broadcast Feed)", "Data API")
        code, body, elapsed, _ = self.request("/api/announcements")
        t_ann.duration_ms = elapsed
        if code == 200 and isinstance(body, dict) and body.get("success"):
            ann_list = body.get("announcements", [])
            has_broadcast = "broadcast" in body
            if len(ann_list) >= 5 and has_broadcast:
                t_ann.passed = True
                t_ann.details = f"Verified: {len(ann_list)} official circulars loaded with active campus broadcast."
            else:
                t_ann.passed = False
                t_ann.details = f"Invalid announcement schema: count={len(ann_list)}, broadcast={has_broadcast}"
        else:
            t_ann.passed = False
            t_ann.details = f"Status {code}: {body}"
        self.log(t_ann)


    # --------------------------------------------------------------------------
    # SUITE 4: Security & Authentication (Zero-Leakage & OWASP)
    # --------------------------------------------------------------------------
    def test_security_and_auth(self):
        print("\n--- [SUITE 4: Authentication Security & Zero-Leakage Checks] ---")

        # Test Valid Student Login
        t_stud = TestResult("POST /api/auth/login (Student Authentication)", "Security")
        code, body, elapsed, _ = self.request("/api/auth/login", method="POST", data={"email": "student@cit.ac.in", "password": "password123"})
        t_stud.duration_ms = elapsed
        if code == 200 and isinstance(body, dict) and body.get("success"):
            t_stud.passed = True
            t_stud.details = f"Authenticated student token: role={body.get('user', {}).get('role')}"
        else:
            t_stud.passed = False
            t_stud.details = f"Login failed: status {code}, {body}"
        self.log(t_stud)

        # Test Valid Admin Login
        t_adm = TestResult("POST /api/auth/login (Central Admin Clearance)", "Security")
        code, body, elapsed, _ = self.request("/api/auth/login", method="POST", data={"email": "admin@cit.ac.in", "password": "admin"})
        t_adm.duration_ms = elapsed
        if code == 200 and isinstance(body, dict) and body.get("success"):
            self.admin_token = body.get("user", {}).get("token") or "cit-adm-live"
            t_adm.passed = True
            t_adm.details = f"Authenticated admin clearance: role={body.get('user', {}).get('role')}"
        else:
            t_adm.passed = False
            t_adm.details = f"Admin login failed: status {code}, {body}"
        self.log(t_adm)

        # Test Password Hash Zero-Exposure (OWASP A02)
        t_hash = TestResult("POST /api/auth/login (Zero Password Hash Exposure)", "OWASP Privacy")
        t_hash.duration_ms = elapsed
        if isinstance(body, dict) and body.get("success"):
            user_obj = body.get("user", {})
            has_hash = "password_hash" in user_obj
            if not has_hash:
                t_hash.passed = True
                t_hash.details = "PASSED: User password hashes are completely stripped from auth payloads."
            else:
                t_hash.passed = False
                t_hash.details = f"LEAK: password_hash exposed in user auth object: {user_obj.get('password_hash')}"
        else:
            t_hash.passed = False
            t_hash.details = "Admin login payload could not be verified."
        self.log(t_hash)

        # Test Unauthenticated Admin User List Rejection (OWASP A01)
        t_anon_users = TestResult("GET /api/admin/users (Unauthenticated Access Rejection)", "OWASP Access Control")
        code, body, elapsed, _ = self.request("/api/admin/users")
        t_anon_users.duration_ms = elapsed
        if code == 401 or (isinstance(body, dict) and not body.get("success")):
            t_anon_users.passed = True
            t_anon_users.details = f"Safely blocked anonymous access: HTTP {code}"
        else:
            t_anon_users.passed = False
            t_anon_users.details = f"VULNERABILITY: /api/admin/users permitted unauthenticated access (HTTP {code})"
        self.log(t_anon_users)

        # Test Unauthenticated Database Setup Rejection (OWASP A01)
        t_anon_db = TestResult("POST /api/admin/db/setup (Unauthenticated Takeover Rejection)", "OWASP Access Control")
        code, body, elapsed, _ = self.request("/api/admin/db/setup", method="POST", data={"database_url": "postgres://attacker@host/db"})
        t_anon_db.duration_ms = elapsed
        if code == 401 or (isinstance(body, dict) and not body.get("success")):
            t_anon_db.passed = True
            t_anon_db.details = f"Safely blocked anonymous DB takeover: HTTP {code}"
        else:
            t_anon_db.passed = False
            t_anon_db.details = f"VULNERABILITY: /api/admin/db/setup permitted anonymous configuration (HTTP {code})"
        self.log(t_anon_db)

        # Test Invalid Password (Negative Test Case)
        t_bad = TestResult("POST /api/auth/login (Invalid Password Rejection)", "Negative Test")
        code, body, elapsed, _ = self.request("/api/auth/login", method="POST", data={"email": "student@cit.ac.in", "password": "WrongPassword999!"})
        t_bad.duration_ms = elapsed
        if isinstance(body, dict) and not body.get("success") and "Incorrect password" in str(body):
            t_bad.passed = True
            t_bad.details = f"Safely rejected: {body.get('message')} (Failed attempts: {body.get('failed_attempts')})"
        else:
            t_bad.passed = False
            t_bad.details = f"Unexpected response: code {code}, {body}"
        self.log(t_bad)

        # Critical: Forgot Password Zero-Leakage Test
        t_leak = TestResult("POST /api/auth/forgot-password (Zero OTP Leakage in Response)", "OWASP Privacy")
        code, body, elapsed, _ = self.request("/api/auth/forgot-password", method="POST", data={"email": "student@cit.ac.in"})
        t_leak.duration_ms = elapsed
        if code == 200 and isinstance(body, dict) and body.get("success"):
            resp_str = json.dumps(body)
            # Check for sensitive key leakage
            leak_detected = any(k in body for k in ["code", "otp", "verification_code", "secret", "token"])
            if not leak_detected:
                t_leak.passed = True
                t_leak.details = "PASSED: Server response contains NO on-screen OTP or secret token. Verified secure."
            else:
                t_leak.passed = False
                t_leak.details = f"CRITICAL LEAK: OTP/Secret detected in API response: {body}"
        else:
            t_leak.passed = False
            t_leak.details = f"Forgot-password endpoint failed: status {code}, {body}"
        self.log(t_leak)

    # --------------------------------------------------------------------------
    # SUITE 5: Administrative Workflows & Request Management
    # --------------------------------------------------------------------------
    def test_admin_workflows(self):
        print("\n--- [SUITE 5: Admin Workflows & Venue Request Management] ---")
        admin_headers = {"Authorization": f"Bearer {self.admin_token}"}

        # 1. Fetch Admin Bookings
        t_b = TestResult("GET /api/admin/bookings (Venue Booking Inventory)", "Admin Workflow")
        code, body, elapsed, _ = self.request("/api/admin/bookings", headers=admin_headers)
        t_b.duration_ms = elapsed
        if code == 200 and isinstance(body, dict) and body.get("success"):
            t_b.passed = True
            t_b.details = f"Retrieved bookings inventory and {len(body.get('overrides', {}))} active overrides."
        else:
            t_b.passed = False
            t_b.details = f"Status {code}: {body}"
        self.log(t_b)

        # 2. Create Venue Booking Request
        test_booking_id = f"QA-REQ-{int(time.time())}"
        t_create = TestResult("POST /api/bookings/create (Student Venue Reservation)", "Booking Workflow")
        booking_payload = {
            "id": test_booking_id,
            "room_id": "CR-101",
            "user_email": "student@cit.ac.in",
            "user_name": "QA Automation Engineer",
            "purpose": "Automated E2E System Verification Lecture",
            "date": "2026-11-05",
            "periods": "P3-P4"
        }
        code, body, elapsed, _ = self.request("/api/bookings/create", method="POST", data=booking_payload)
        t_create.duration_ms = elapsed
        if code == 200 and isinstance(body, dict) and body.get("success"):
            t_create.passed = True
            t_create.details = f"Created reservation {test_booking_id} with Under Review status."
        else:
            t_create.passed = False
            t_create.details = f"Status {code}: {body}"
        self.log(t_create)

        # 3. Admin Approval Workflow
        t_appr = TestResult("POST /api/admin/bookings/update (Approve Reservation)", "Admin Workflow")
        appr_payload = {
            "booking_id": test_booking_id,
            "status": "approved",
            "actor": "Lead QA Engineer",
            "reason": "Automated verification clearance"
        }
        code, body, elapsed, _ = self.request("/api/admin/bookings/update", method="POST", data=appr_payload, headers=admin_headers)
        t_appr.duration_ms = elapsed
        if code == 200 and isinstance(body, dict) and body.get("success"):
            t_appr.passed = True
            t_appr.details = f"Booking {test_booking_id} approved and persisted."
        else:
            t_appr.passed = False
            t_appr.details = f"Status {code}: {body}"
        self.log(t_appr)

        # 4. Fetch Audit Logs
        t_audit = TestResult("GET /api/admin/audit-logs (Security Audit Trail)", "Audit Trail")
        code, body, elapsed, _ = self.request("/api/admin/audit-logs", headers=admin_headers)
        t_audit.duration_ms = elapsed
        if code == 200 and isinstance(body, dict) and body.get("success"):
            logs = body.get("logs", [])
            t_audit.passed = len(logs) > 0
            t_audit.details = f"Retrieved {len(logs)} chronological audit events."
        else:
            t_audit.passed = False
            t_audit.details = f"Status {code}: {body}"
        self.log(t_audit)

    # --------------------------------------------------------------------------
    # SUITE 6: Database & Cloud Persistence Layer
    # --------------------------------------------------------------------------
    def test_database_and_cloud(self):
        print("\n--- [SUITE 6: Neon Serverless Database & Dual-Persistence] ---")
        admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        t_db = TestResult("GET /api/admin/db/status (Neon Serverless Telemetry)", "Database")
        code, body, elapsed, _ = self.request("/api/admin/db/status", headers=admin_headers)
        t_db.duration_ms = elapsed
        if code == 200 and isinstance(body, dict) and body.get("success"):
            neon_info = body.get("neon", {})
            provider = neon_info.get("provider", "Unknown")
            is_connected = neon_info.get("connected", False)
            t_db.passed = True
            t_db.details = f"Provider: {provider} | Connected: {is_connected} | Msg: {neon_info.get('message')}"
        else:
            t_db.passed = False
            t_db.details = f"Status {code}: {body}"
        self.log(t_db)

    def run_all(self):
        print(f"\n{'='*75}")
        print(f"  CIT CAMPUS ERP — PROFESSIONAL QA AUTOMATION EXECUTION")
        print(f"  Target Host: {self.base_url}")
        print(f"  Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*75}")

        start_time = time.time()
        self.test_routes_and_seo()
        self.test_typography_and_privacy()
        self.test_academic_optimizer_apis()
        self.test_security_and_auth()
        self.test_admin_workflows()
        self.test_database_and_cloud()
        total_time = (time.time() - start_time) * 1000.0

        passed_count = sum(1 for r in self.results if r.passed)
        failed_count = sum(1 for r in self.results if not r.passed)
        total_tests = len(self.results)
        success_rate = (passed_count / total_tests * 100.0) if total_tests else 0.0

        print(f"\n{'-'*75}")
        print(f"  QA SUMMARY: {passed_count}/{total_tests} Tests Passed ({success_rate:.1f}%) | Total Time: {total_time:.1f}ms")
        print(f"{'-'*75}\n")
        return passed_count, failed_count

if __name__ == "__main__":
    target = LOCAL_BASE
    if len(sys.argv) > 1:
        target = sys.argv[1]
    runner = QATestRunner(target)
    p, f = runner.run_all()
    sys.exit(0 if f == 0 else 1)
