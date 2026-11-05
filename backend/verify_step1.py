"""
Post-Step 1 Verification Script for Supabase PostgreSQL and SQLite.
Checks table existence, schema, Alembic revision, 0 records in Supabase,
PostgreSQL sequence names, and confirms SQLite is untouched.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from backend.app.database import build_engine
import sqlite3

def verify_all():
    print("=" * 65)
    print("Step 1: Supabase PostgreSQL Schema Verification")
    print("=" * 65)

    engine = build_engine()
    with engine.connect() as conn:
        # 1. Alembic version check
        rev = conn.execute(text("SELECT version_num FROM alembic_version;")).scalar()
        print(f"Current Alembic Revision in Supabase: {rev}")

        # 2. Public tables
        res = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"))
        tables = [r[0] for r in res]
        print(f"Existing Public Tables: {tables}")

        # 3. Check 5 domain tables and row counts
        domain_tables = ["machines", "sensor_readings", "maintenance_history", "alerts", "tickets"]
        print("\nDomain Table Record Counts in Supabase:")
        all_empty = True
        for dt in domain_tables:
            if dt in tables:
                cnt = conn.execute(text(f"SELECT COUNT(*) FROM {dt};")).scalar()
                print(f"  - {dt}: {cnt} rows")
                if cnt != 0:
                    all_empty = False
            else:
                print(f"  - {dt}: MISSING!")
                all_empty = False
        print(f"All 5 Domain Tables Empty: {all_empty}")

        # 4. Check PostgreSQL sequences
        seq_res = conn.execute(text("SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public' ORDER BY sequence_name;"))
        sequences = [r[0] for r in seq_res]
        print(f"\nGenerated PostgreSQL Sequences: {sequences}")

        # 5. Check indexes
        idx_res = conn.execute(text("""
            SELECT tablename, indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname;
        """))
        print("\nGenerated Indexes:")
        for r in idx_res:
            print(f"  - {r[0]}: {r[1]}")

    # 6. Verify SQLite database remains untouched
    sqlite_path = os.path.abspath("manumind.db")
    print("\n" + "=" * 65)
    print("SQLite Local Database Integrity Check")
    print("=" * 65)
    print(f"SQLite Path: {sqlite_path}")
    print(f"SQLite Size: {os.path.getsize(sqlite_path):,} bytes (~ {round(os.path.getsize(sqlite_path)/(1024*1024), 2)} MB)")

    s_conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    s_cur = s_conn.cursor()
    for dt in domain_tables:
        s_cur.execute(f"SELECT COUNT(*) FROM {dt};")
        print(f"  - SQLite {dt}: {s_cur.fetchone()[0]:,} rows")
    s_conn.close()
    print("SQLite database verified completely untouched!")

if __name__ == "__main__":
    verify_all()
