#!/usr/bin/env python3
"""
CIT Campus ERP - Database Management Utility (CLI)
===================================================
Authoritative tool to inspect, maintain, sanitize, and reset the CIT database
across both the local persistent store (users_store.json) and Neon PostgreSQL.

Usage:
  python manage_db.py status                # View current database telemetry & counts
  python manage_db.py clear-bookings        # Remove all custom / test venue reservations
  python manage_db.py reset-attempts        # Reset failed login attempt counters & unlock accounts
  python manage_db.py purge-test-users      # Purge temporary/test user registrations
  python manage_db.py reset-audit-logs      # Reset audit trail to institutional baseline
  python manage_db.py reset-baseline        # Complete factory reset to pristine institutional baseline
  python manage_db.py sync-neon             # Push current local store state into Neon PostgreSQL
"""

import sys
import os
import json
import argparse
from pathlib import Path

# Fix Windows console UTF-8 output if possible
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "users_store.json"

# Import Neon DB connector if available
try:
    import neon_db
except ImportError:
    neon_db = None

# Factory baseline configuration
BASELINE_DATA = {
    "users": [
        {
            "id": "CIT-U001",
            "name": "Arjun Sharma",
            "email": "student@cit.ac.in",
            "role": "student",
            "cohort": "Y1-A",
            "status": "Active",
            "last_active": "Just now",
            "password_hash": "23e21208d30e97958088e25f82a22ef740f35a398b60c839f1eb353e25f9f76b"
        },
        {
            "id": "CIT-U002",
            "name": "Dr. Priya Nair",
            "email": "faculty@cit.ac.in",
            "role": "faculty",
            "cohort": "Faculty Member",
            "status": "Active",
            "last_active": "12m ago"
        },
        {
            "id": "CIT-U003",
            "name": "Spectra Tech Club",
            "email": "spectra.club@cit.ac.in",
            "role": "club",
            "cohort": "Club Operations",
            "status": "Active",
            "last_active": "1h ago"
        }
    ],
    "credentials": {
        "student@cit.ac.in": {
            "hash": "23e21208d30e97958088e25f82a22ef740f35a398b60c839f1eb353e25f9f76b",
            "failed_attempts": 0
        },
        "faculty@cit.ac.in": {
            "hash": "39366e5e5571fd1ead76f031c344a4149d00605a1c62cd622a90e08ba485b17e",
            "failed_attempts": 0
        },
        "spectra.club@cit.ac.in": {
            "hash": "729de5c0d6e39af4f7bec0ace4dad4903ba2f0772a47e967d7fc6b74c1b31720",
            "failed_attempts": 0
        },
        "admin@cit.ac.in": {
            "hash": "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9",
            "failed_attempts": 0
        },
        "admin": {
            "hash": "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9",
            "failed_attempts": 0
        }
    },
    "profiles": {},
    "custom_bookings": [],
    "booking_overrides": {},
    "audit_logs": [
        {
            "id": "AUD-101",
            "user": "Dean of Academic Operations",
            "email": "admin@cit.ac.in",
            "role": "admin",
            "action": "Initialized CIT Admin OS Root Telemetry",
            "module": "System",
            "status": "Success",
            "timestamp": "12m ago",
            "online": True
        },
        {
            "id": "AUD-102",
            "user": "Spectra Tech Club",
            "email": "spectra.club@cit.ac.in",
            "role": "club",
            "action": "Submitted venue booking request BR-26 for RoboCIT Autonomous Challenge",
            "module": "Venue Bookings",
            "status": "Under Review",
            "timestamp": "18m ago",
            "online": True
        },
        {
            "id": "AUD-103",
            "user": "Student Representative",
            "email": "student@cit.ac.in",
            "role": "student",
            "action": "Viewed Friday conflict-free timetable for Cohort Y1-A",
            "module": "Timetable",
            "status": "Success",
            "timestamp": "25m ago",
            "online": True
        },
        {
            "id": "AUD-104",
            "user": "Faculty Member",
            "email": "faculty@cit.ac.in",
            "role": "faculty",
            "action": "Logged in via Institutional Google Workspace SSO",
            "module": "Authentication",
            "status": "Success",
            "timestamp": "34m ago",
            "online": False
        },
        {
            "id": "AUD-105",
            "user": "Cultural Committee",
            "email": "cultural@cit.ac.in",
            "role": "club",
            "action": "Requested Audi-1 for Spectra Fest Cultural Night (BR-01)",
            "module": "Venue Bookings",
            "status": "Approved",
            "timestamp": "1h ago",
            "online": False
        },
        {
            "id": "AUD-106",
            "user": "Office of Academic Affairs",
            "email": "admin@cit.ac.in",
            "role": "admin",
            "action": "Executed OR-Tools CP-SAT solver constraint validation (0 hard violations)",
            "module": "Academic Engine",
            "status": "Success",
            "timestamp": "2h ago",
            "online": True
        }
    ],
    "settings": {
        "announcement": "Welcome to Chilika Institute of Technology (CIT) Campus ERP · Conflict-Free Timetable & Venue Services Active",
        "maintenance": False,
        "allow_signup": True,
        "ai_assistant": True
    }
}

STANDARD_EMAILS = {"student@cit.ac.in", "faculty@cit.ac.in", "spectra.club@cit.ac.in", "admin@cit.ac.in", "admin"}

def load_data():
    """Load database from users_store.json."""
    if not DB_FILE.exists():
        return json.loads(json.dumps(BASELINE_DATA))
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] Error loading {DB_FILE}: {e}")
        return json.loads(json.dumps(BASELINE_DATA))

def save_data(data):
    """Save database to users_store.json and Neon if configured."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[✓] Saved database state to {DB_FILE.name}")

    if neon_db and neon_db.is_neon_configured():
        try:
            ok = neon_db.save_state_to_neon(data)
            if ok:
                print("[✓] Synchronized state to Neon Serverless PostgreSQL")
            else:
                print("[!] Neon sync returned False")
        except Exception as e:
            print(f"[!] Neon sync error: {e}")
    else:
        print("[i] Neon Serverless PostgreSQL: Local Standby Fallback mode")

def cmd_status():
    """Print comprehensive telemetry and status of the database."""
    data = load_data()
    users = data.get("users", [])
    creds = data.get("credentials", {})
    bookings = data.get("custom_bookings", [])
    logs = data.get("audit_logs", [])
    overrides = data.get("booking_overrides", {})
    settings = data.get("settings", {})

    print("\n" + "=" * 60)
    print("       CIT CAMPUS ERP - DATABASE TELEMETRY & STATUS")
    print("=" * 60)

    print(f"\n[1] Institutional Users: {len(users)}")
    for u in users:
        print(f"    - {u.get('name', 'N/A')} ({u.get('email')}) [{u.get('role', 'user')}] Status: {u.get('status', 'Active')}")

    print(f"\n[2] Authentication Credentials: {len(creds)}")
    locked_count = 0
    for email, cred in creds.items():
        fails = cred.get("failed_attempts", 0)
        status_tag = f"LOCKED ({fails} failed attempts)" if fails >= 5 else (f"{fails} failed attempts" if fails > 0 else "OK")
        if fails > 0:
            locked_count += 1
        print(f"    - {email:<30} -> {status_tag}")
    if locked_count == 0:
        print("    ✓ All accounts clear with 0 failed attempt counters.")

    print(f"\n[3] Custom / Dynamic Venue Bookings: {len(bookings)}")
    if bookings:
        for b in bookings[:10]:
            print(f"    - {b.get('id', 'N/A')}: {b.get('event', 'Unnamed')} by {b.get('applicant', 'Unknown')} [{b.get('status', 'pending')}]")
        if len(bookings) > 10:
            print(f"    ... and {len(bookings) - 10} more")
    else:
        print("    ✓ No custom venue reservations (clean baseline).")

    print(f"\n[4] Booking Overrides: {len(overrides)}")
    for k, v in overrides.items():
        print(f"    - {k}: {v}")

    print(f"\n[5] System Audit Logs: {len(logs)}")
    for log in logs[:5]:
        print(f"    - [{log.get('id')}] {log.get('timestamp')}: {log.get('action')} ({log.get('status')})")
    if len(logs) > 5:
        print(f"    ... and {len(logs) - 5} earlier log events")

    print(f"\n[6] Cloud Persistence (Neon PostgreSQL):")
    if neon_db:
        st = neon_db.test_neon_status()
        print(f"    - Configured: {st.get('configured')}")
        print(f"    - Connected:  {st.get('connected')}")
        print(f"    - Provider:   {st.get('provider')}")
        print(f"    - Host:       {st.get('host')}")
        print(f"    - Database:   {st.get('database')}")
        print(f"    - Message:    {st.get('message')}")
    else:
        print("    - Neon module not loaded.")

    print("=" * 60 + "\n")

def cmd_clear_bookings():
    """Purge all custom venue bookings and overrides."""
    data = load_data()
    count = len(data.get("custom_bookings", []))
    data["custom_bookings"] = []
    data["booking_overrides"] = {}
    save_data(data)
    print(f"[✓] Successfully purged {count} custom venue reservation(s) and reset overrides.")

def cmd_reset_attempts():
    """Reset all failed login attempt counters."""
    data = load_data()
    creds = data.get("credentials", {})
    reset_count = 0
    for email, cred in creds.items():
        if cred.get("failed_attempts", 0) > 0:
            cred["failed_attempts"] = 0
            reset_count += 1
    save_data(data)
    print(f"[✓] Successfully reset failed attempt counters on {reset_count} account(s).")

def cmd_purge_test_users():
    """Remove test users and temporary registrations."""
    data = load_data()
    initial_user_count = len(data.get("users", []))
    data["users"] = [u for u in data.get("users", []) if u.get("email") in STANDARD_EMAILS]

    initial_cred_count = len(data.get("credentials", {}))
    data["credentials"] = {k: v for k, v in data.get("credentials", {}).items() if k in STANDARD_EMAILS}

    # Reset failed attempts for remaining accounts
    for cred in data["credentials"].values():
        cred["failed_attempts"] = 0

    save_data(data)
    removed_users = initial_user_count - len(data["users"])
    removed_creds = initial_cred_count - len(data["credentials"])
    print(f"[✓] Purged {removed_users} non-standard user(s) and {removed_creds} test credential(s).")

def cmd_reset_audit_logs():
    """Reset audit trail to standard institutional logs."""
    data = load_data()
    data["audit_logs"] = list(BASELINE_DATA["audit_logs"])
    save_data(data)
    print(f"[✓] Reset audit trail to {len(BASELINE_DATA['audit_logs'])} pristine baseline events.")

def cmd_reset_baseline():
    """Complete factory reset of all data structures to baseline state."""
    clean = json.loads(json.dumps(BASELINE_DATA))
    save_data(clean)
    print("[✓] Complete database reset to institutional baseline successfully executed.")

def cmd_sync_neon():
    """Force push local store to Neon PostgreSQL."""
    data = load_data()
    if not (neon_db and neon_db.is_neon_configured()):
        print("[!] Neon connection string is not configured. Set DATABASE_URL or run setup_neon.py first.")
        return
    ok = neon_db.save_state_to_neon(data)
    if ok:
        print("[✓] Neon Serverless PostgreSQL successfully synchronized with local state.")
    else:
        print("[!] Neon synchronization failed.")

def main():
    parser = argparse.ArgumentParser(
        description="CIT Campus ERP - Database Management Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python manage_db.py status\n"
               "  python manage_db.py clear-bookings\n"
               "  python manage_db.py reset-baseline\n"
    )
    parser.add_argument(
        "action",
        nargs="?",
        default="status",
        choices=["status", "clear-bookings", "reset-attempts", "purge-test-users", "reset-audit-logs", "reset-baseline", "sync-neon"],
        help="Management operation to execute"
    )
    parser.add_argument("--status", action="store_true", help="Display database status")
    parser.add_argument("--clear-bookings", action="store_true", help="Purge custom bookings")
    parser.add_argument("--reset-attempts", action="store_true", help="Reset failed login counters")
    parser.add_argument("--purge-test-users", action="store_true", help="Purge non-standard test users")
    parser.add_argument("--reset-audit-logs", action="store_true", help="Reset audit logs")
    parser.add_argument("--reset-baseline", action="store_true", help="Factory reset database to baseline")
    parser.add_argument("--sync-neon", action="store_true", help="Sync state to Neon PostgreSQL")

    args = parser.parse_args()

    # Flag overrides
    if args.reset_baseline:
        cmd_reset_baseline()
    elif args.clear_bookings:
        cmd_clear_bookings()
    elif args.reset_attempts:
        cmd_reset_attempts()
    elif args.purge_test_users:
        cmd_purge_test_users()
    elif args.reset_audit_logs:
        cmd_reset_audit_logs()
    elif args.sync_neon:
        cmd_sync_neon()
    else:
        # Match positional action
        action_map = {
            "status": cmd_status,
            "clear-bookings": cmd_clear_bookings,
            "reset-attempts": cmd_reset_attempts,
            "purge-test-users": cmd_purge_test_users,
            "reset-audit-logs": cmd_reset_audit_logs,
            "reset-baseline": cmd_reset_baseline,
            "sync-neon": cmd_sync_neon,
        }
        action_map.get(args.action, cmd_status)()

if __name__ == "__main__":
    main()
