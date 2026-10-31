#!/usr/bin/env python3
"""
Neon Serverless PostgreSQL Database Migration & Setup CLI.
Usage:
    python setup_neon.py "postgresql://user:password@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require"
"""

import sys
import os
import json

def setup_neon_database(db_url: str):
    if not db_url or not (db_url.startswith("postgres://") or db_url.startswith("postgresql://")):
        print("[ERROR] Please provide a valid Neon PostgreSQL connection string.")
        print("Example: python setup_neon.py \"postgresql://user:pass@ep-cool-resonance.us-east-2.aws.neon.tech/neondb?sslmode=require\"")
        sys.exit(1)

    print("=" * 60)
    print("CIT Campus ERP · Neon Serverless PostgreSQL Setup")
    print("=" * 60)

    # 1. Save to .env
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip().startswith("DATABASE_URL=") and not line.strip().startswith("NEON_DATABASE_URL="):
                    lines.append(line)
    lines.append(f"DATABASE_URL={db_url}\n")
    lines.append(f"NEON_DATABASE_URL={db_url}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"[1/4] Saved connection string to {env_path}")

    # Set in current runtime environment
    os.environ["DATABASE_URL"] = db_url
    os.environ["NEON_DATABASE_URL"] = db_url

    # 2. Test Connection & Init Tables
    import neon_db
    print("[2/4] Initializing Neon database schema & tables...")
    success = neon_db.init_neon_tables()
    if not success:
        print("[ERROR] Failed to initialize Neon tables. Please verify your credentials & internet connectivity.")
        sys.exit(1)

    # 3. Migrate Local users_store.json to Neon
    print("[3/4] Migrating local data from users_store.json to Neon...")
    store_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users_store.json")
    if os.path.exists(store_path):
        try:
            with open(store_path, "r", encoding="utf-8") as f:
                local_data = json.load(f)
            neon_db.save_state_to_neon(local_data)
            print(f"[3/4] Successfully migrated {len(local_data.get('users', []))} users and {len(local_data.get('custom_bookings', []))} bookings to Neon!")
        except Exception as e:
            print(f"[WARNING] Migration partial error: {e}")
    else:
        print("[3/4] No local users_store.json found. Creating initial seed data.")

    # 4. Final verification
    status = neon_db.test_neon_status()
    print("=" * 60)
    print("[4/4] NEON POSTGRESQL SETUP COMPLETE!")
    print(f"Host:     {status.get('host')}")
    print(f"Database: {status.get('database')}")
    print(f"Version:  {status.get('version')}")
    print(f"Stats:    {status.get('stats')}")
    print("=" * 60)
    print("Your CIT ERP server is now permanently backed by Neon Serverless PostgreSQL!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        setup_neon_database(sys.argv[1].strip())
    else:
        # Check if already in environment
        url = os.environ.get("DATABASE_URL") or os.environ.get("NEON_DATABASE_URL")
        if url:
            setup_neon_database(url.strip())
        else:
            print("Please provide your Neon connection string:")
            print("python setup_neon.py \"postgresql://user:pass@ep-cool.us-east-2.aws.neon.tech/neondb?sslmode=require\"")
