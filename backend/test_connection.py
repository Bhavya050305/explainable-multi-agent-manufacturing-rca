"""
ManuMind AI - Database Connection Diagnostic Tool
Tests PostgreSQL / Supabase Session Pooler connectivity via SQLAlchemy.
Safely masks credentials in all outputs.
"""

import argparse
import os
import re
import sys
import time
from urllib.parse import urlparse, quote_plus
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, DBAPIError

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.config import settings
from backend.app.database import build_engine, get_normalized_database_url


def mask_url(url: str) -> str:
    """Mask password in connection URL for safe terminal display."""
    if not url:
        return "(empty)"
    return re.sub(r":([^/@:]+)@", ":********@", url)


def test_database_connection(custom_url: str | None = None, password_override: str | None = None) -> bool:
    """
    Test connectivity to PostgreSQL / Supabase database.
    Returns True if connection succeeds, False otherwise.
    """
    raw_url = custom_url or settings.DATABASE_URL

    if password_override:
        # URL encode password in case it contains special characters
        clean_pwd = password_override.strip().strip("[]")
        quoted_pwd = quote_plus(clean_pwd)
        raw_url = re.sub(r":([^/@:]+)@", f":{quoted_pwd}@", raw_url)

    # Ensure sslmode=require for Supabase pooler
    if "pooler.supabase.com" in raw_url and "sslmode" not in raw_url:
        sep = "&" if "?" in raw_url else "?"
        raw_url = f"{raw_url}{sep}sslmode=require"

    masked = mask_url(raw_url)

    print("=" * 65)
    print("ManuMind AI — Database Connection Diagnostic")
    print("=" * 65)
    print(f"Target Database URL: {masked}")

    # Parse components for diagnostic reporting
    try:
        match = re.search(r"@([^:/]+)(?::(\d+))?/(.+)$", raw_url)
        if match:
            host = match.group(1)
            port = match.group(2) or "5432"
            db_name = match.group(3).split("?")[0]
            print(f"Host:       {host}")
            print(f"Port:       {port}")
            print(f"Database:   {db_name}")
            print(f"Connection: Supabase Session Pooler (port {port})")
    except Exception:
        pass

    # Check for placeholder passwords (including Supabase dashboard [YOUR-PASSWORD])
    placeholders = [
        "YOUR_ACTUAL_PASSWORD", "[YOUR-PASSWORD]", "YOUR-PASSWORD",
        "[YOUR_PASSWORD]", "YOUR_PASSWORD", "<YOUR_PASSWORD>", "[YOUR_ACTUAL_PASSWORD]"
    ]
    if any(p in raw_url for p in placeholders):
        print("\n[DIAGNOSTIC NOTICE] Placeholder Password Detected:")
        print("  The DATABASE_URL in .env contains the Supabase placeholder '[YOUR-PASSWORD]'.")
        print("  This needs to be replaced with the database password you created in Supabase.")
        print("\n  Steps to fix:")
        print("    1. Open .env in your editor.")
        print("    2. Replace '[YOUR-PASSWORD]' with your real password (WITHOUT square brackets).")
        print("       Example format:")
        print("Set DATABASE_URL in your .env file using your Supabase connection string.")
        print("\n    3. Alternatively, test directly via CLI without editing .env:")
        print("       python backend/test_connection.py")
        print("-" * 65)
        print("Status: AWAITING_CREDENTIAL (Placeholder '[YOUR-PASSWORD]' still present)")
        return False

    # Check for empty password
    if re.search(r":@|:[^/@:]*@$", raw_url) or re.search(r"//[^:]+:@", raw_url):
        print("\n[DIAGNOSTIC NOTICE] Empty Password Detected:")
        print("  In .env, line 7 has no password between the colon ':' and '@'.")
        print("  Please paste your Supabase password right after the colon.")
        print("-" * 65)
        print("Status: NO_PASSWORD_SUPPLIED")
        return False

    # Check if real password has square brackets around it [password]
    bracket_match = re.search(r':(\[[^\]]+\])@', raw_url)
    if bracket_match:
        print("\n[WARNING] Password has literal square brackets '[...]' around it.")
        print("  Please remove the brackets '[' and ']' from your password in .env.")

    print("\nAttempting connection to Supabase...")
    start_time = time.time()

    try:
        engine = build_engine(raw_url)
        with engine.connect() as conn:
            probe_result = conn.execute(text("SELECT 1;")).scalar()
            version_result = conn.execute(text("SELECT version();")).scalar()
            latency = (time.time() - start_time) * 1000

        print("\n[SUCCESS] Connection Established Successfully!")
        print(f"  - Probe Check:        SELECT 1 => {probe_result}")
        print(f"  - PostgreSQL Version: {version_result.split(',')[0] if version_result else 'Unknown'}")
        print(f"  - Roundtrip Latency:  {latency:.2f} ms")
        print(f"  - Driver Dialect:     {engine.dialect.name} ({engine.dialect.driver})")
        print(f"  - Connection Pool:    QueuePool (size=10, recycle=300s)")
        print("=" * 65)
        return True

    except OperationalError as oe:
        err_msg = str(oe.orig) if hasattr(oe, "orig") else str(oe)
        err_msg_clean = mask_url(err_msg)
        print("\n[FAILED] Database Connection Failed:")
        print(f"  Error details: {err_msg_clean}")
        if "password authentication failed" in err_msg_clean.lower():
            print("\n  Hint: The database password was rejected by Supabase.")
            print("        If you forgot your password, you can reset it in Supabase:")
            print("        Supabase Dashboard -> Project Settings -> Database -> Database Password -> Reset Password.")
        elif "timeout" in err_msg_clean.lower() or "connection refused" in err_msg_clean.lower():
            print("\n  Hint: Network timeout or connection refused.")
            print("        Ensure your network allows outbound traffic on port 5432 and SSL is enabled.")
        print("=" * 65)
        return False

    except Exception as e:
        err_msg_clean = mask_url(str(e))
        print(f"\n[FAILED] Unexpected Connection Error: {err_msg_clean}")
        print("=" * 65)
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Supabase PostgreSQL connection.")
    parser.add_argument("--url", type=str, default=None, help="Explicit database URL to test")
    parser.add_argument("--password", type=str, default=None, help="Override database password for test")
    args = parser.parse_args()

    success = test_database_connection(custom_url=args.url, password_override=args.password)
    sys.exit(0 if success else 1)
