"""
ManuMind AI — SQLite to Supabase PostgreSQL Migration Script (Corrected)
Safely transfers all 40,416 domain records from local SQLite (read-only)
to Supabase PostgreSQL using SQLAlchemy transactions and batching.

Safety Guarantees & Sequence Handling:
- SQLite opened strictly in read-only mode (file:manumind.db?mode=ro).
- Destination tables MUST be completely empty before inserting anything.
- All 40,416 domain records are inserted within a SINGLE atomic transaction.
- If ANY error occurs during data insertion, the entire transaction is rolled back.
- PostgreSQL sequence operations (setval/nextval) are non-transactional in PostgreSQL.
  Sequence synchronization is executed ONLY AFTER the data insertion has successfully committed.
- If sequence synchronization encounters an issue after data commit, the data is preserved
  (no records deleted or re-inserted) and a safe manual recovery procedure is provided.
- Database credentials are masked in all log outputs.
"""

import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime
from typing import Dict, Any, List

# Ensure parent directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from backend.app.config import settings
from backend.app.database import build_engine
from backend.app.models.machine import Machine
from backend.app.models.sensor_reading import SensorReading
from backend.app.models.maintenance_history import MaintenanceHistory
from backend.app.models.alert import Alert
from backend.app.models.ticket import Ticket


def mask_url(url: str) -> str:
    """Mask password credentials in connection string for safe display."""
    if not url:
        return "(empty)"
    return re.sub(r":([^/@:]+)@", ":********@", url)


def parse_datetime(val: Any) -> datetime | None:
    """Safely parse SQLite timestamp string to Python datetime."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    val_str = str(val).strip()
    try:
        return datetime.fromisoformat(val_str)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(val_str, fmt)
            except ValueError:
                pass
    raise ValueError(f"Unable to parse datetime string: '{val_str}'")


def parse_json(val: Any) -> Any:
    """Safely parse JSON field from string if needed."""
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            return val
    return val


def migrate(dry_run: bool = False):
    print("=" * 70)
    print("ManuMind AI — SQLite to Supabase Data Migration")
    print("=" * 70)

    # 1. Source and Destination Configuration
    sqlite_path = os.path.abspath(os.path.join(settings.BASE_PATH, "manumind.db"))
    if not os.path.exists(sqlite_path):
        raise FileNotFoundError(f"Source SQLite database not found at: {sqlite_path}")

    masked_target = mask_url(settings.DATABASE_URL)
    print(f"Source (SQLite - Read-Only): {sqlite_path}")
    print(f"Destination (Supabase):       {masked_target}")
    if dry_run:
        print("[DRY RUN MODE] Pre-flight checks only. No data will be transferred.")
    print("-" * 70)

    # 2. Connect to SQLite in STRICT Read-Only Mode
    sqlite_uri = f"file:{sqlite_path}?mode=ro"
    sqlite_conn = sqlite3.connect(sqlite_uri, uri=True)
    sqlite_cur = sqlite_conn.cursor()

    # Pre-count expected records in SQLite
    sqlite_counts = {}
    domain_tables = ["machines", "sensor_readings", "maintenance_history", "alerts", "tickets"]
    for t in domain_tables:
        sqlite_cur.execute(f"SELECT COUNT(*) FROM {t};")
        sqlite_counts[t] = sqlite_cur.fetchone()[0]

    print("Source SQLite Record Counts:")
    for t, c in sqlite_counts.items():
        print(f"  - {t:<22}: {c:>6,} records")
    total_source = sum(sqlite_counts.values())
    print(f"  Total Domain Records:   {total_source:>6,}")
    print("-" * 70)

    expected_totals = {
        "machines": 10,
        "sensor_readings": 40000,
        "maintenance_history": 400,
        "alerts": 5,
        "tickets": 1
    }
    for t, expected in expected_totals.items():
        if sqlite_counts[t] != expected:
            raise ValueError(f"SQLite table '{t}' count mismatch: expected {expected}, found {sqlite_counts[t]}. Aborting.")

    # 3. Connect to Supabase PostgreSQL Engine
    pg_engine = build_engine()

    with pg_engine.connect() as pg_conn:
        # 4. Strict Empty Destination Check
        print("Checking destination Supabase tables for emptiness...")
        for t in domain_tables:
            count = pg_conn.execute(text(f"SELECT COUNT(*) FROM {t};")).scalar()
            if count > 0:
                raise RuntimeError(
                    f"SAFETY ABORT: Destination table '{t}' already contains {count} records! "
                    "Migration requires all destination tables to be completely empty. "
                    "No data was transferred or modified."
                )
        print("All destination tables verified empty. Safe to proceed.")
        print("-" * 70)

        # Close autobegin transaction from pre-flight queries
        pg_conn.rollback()

        if dry_run:
            print("[DRY RUN] All pre-flight safety checks PASSED. Exiting without changes.")
            sqlite_conn.close()
            return

        # -------------------------------------------------------------
        # 5. ATOMIC DATA INSERTION TRANSACTION
        # All 40,416 records across all 5 tables are committed in one transaction.
        # If ANY batch or table fails, the entire transaction rolls back.
        # -------------------------------------------------------------
        start_time = time.time()
        print("Beginning atomic data insertion transaction...")

        with pg_conn.begin() as trans:
            try:
                # Acquire exclusive PostgreSQL transaction-level advisory lock to prevent concurrent migrations
                lock_id = 7429103
                lock_acquired = pg_conn.execute(text(f"SELECT pg_try_advisory_xact_lock({lock_id});")).scalar()
                if not lock_acquired:
                    raise RuntimeError(f"Concurrent migration prevented: Advisory lock {lock_id} is currently held by another session.")
                print(f"Exclusive transaction advisory lock acquired (lock_id={lock_id}).")

                # Step A: Migrate 'machines' (10 records)
                print("[1/5] Migrating 'machines' (10 records)...")
                sqlite_cur.execute("SELECT id, name, type, criticality, production_impact FROM machines ORDER BY id;")
                machine_rows = sqlite_cur.fetchall()
                machine_dicts = [
                    {
                        "id": r[0],
                        "name": r[1],
                        "type": r[2],
                        "criticality": int(r[3]),
                        "production_impact": int(r[4])
                    }
                    for r in machine_rows
                ]
                pg_conn.execute(Machine.__table__.insert(), machine_dicts)
                print(f"  -> Successfully inserted {len(machine_dicts)} machines.")

                # Step B: Migrate 'sensor_readings' (40,000 records in batches of 5,000)
                print("[2/5] Migrating 'sensor_readings' (40,000 records in batches of 5,000)...")
                sqlite_cur.execute(
                    "SELECT id, machine_id, timestamp, vibration, temperature, pressure, current, rpm "
                    "FROM sensor_readings ORDER BY id;"
                )
                batch_size = 5000
                total_inserted_sensors = 0

                while True:
                    rows = sqlite_cur.fetchmany(batch_size)
                    if not rows:
                        break
                    batch_dicts = [
                        {
                            "id": int(r[0]),
                            "machine_id": r[1],
                            "timestamp": parse_datetime(r[2]),
                            "vibration": float(r[3]),
                            "temperature": float(r[4]),
                            "pressure": float(r[5]),
                            "current": float(r[6]),
                            "rpm": float(r[7])
                        }
                        for r in rows
                    ]
                    pg_conn.execute(SensorReading.__table__.insert(), batch_dicts)
                    total_inserted_sensors += len(batch_dicts)
                    print(f"  -> Inserted {total_inserted_sensors:,} / 40,000 sensor readings...")

                if total_inserted_sensors != 40000:
                    raise ValueError(f"Sensor readings count mismatch: {total_inserted_sensors} != 40000")

                # Step C: Migrate 'maintenance_history' (400 records)
                print("[3/5] Migrating 'maintenance_history' (400 records)...")
                sqlite_cur.execute(
                    "SELECT id, machine_id, date, issue, action, outcome FROM maintenance_history ORDER BY id;"
                )
                maint_rows = sqlite_cur.fetchall()
                maint_dicts = [
                    {
                        "id": int(r[0]),
                        "machine_id": r[1],
                        "date": parse_datetime(r[2]),
                        "issue": r[3],
                        "action": r[4],
                        "outcome": r[5]
                    }
                    for r in maint_rows
                ]
                pg_conn.execute(MaintenanceHistory.__table__.insert(), maint_dicts)
                print(f"  -> Successfully inserted {len(maint_dicts)} maintenance history records.")

                # Step D: Migrate 'alerts' (5 records)
                print("[4/5] Migrating 'alerts' (5 records)...")
                sqlite_cur.execute(
                    "SELECT id, machine_id, risk, criticality, impact, priority_score, shap_json, sensor_contrib_json, status, created_at "
                    "FROM alerts ORDER BY created_at;"
                )
                alert_rows = sqlite_cur.fetchall()
                alert_dicts = [
                    {
                        "id": r[0],
                        "machine_id": r[1],
                        "risk": float(r[2]),
                        "criticality": int(r[3]),
                        "impact": int(r[4]),
                        "priority_score": float(r[5]),
                        "shap_json": parse_json(r[6]),
                        "sensor_contrib_json": parse_json(r[7]),
                        "status": r[8],
                        "created_at": parse_datetime(r[9])
                    }
                    for r in alert_rows
                ]
                pg_conn.execute(Alert.__table__.insert(), alert_dicts)
                print(f"  -> Successfully inserted {len(alert_dicts)} alerts.")

                # Step E: Migrate 'tickets' (1 record)
                print("[5/5] Migrating 'tickets' (1 record)...")
                sqlite_cur.execute(
                    "SELECT id, alert_id, recommendation, evidence, confidence, approval_status, approved_by, created_at "
                    "FROM tickets ORDER BY created_at;"
                )
                ticket_rows = sqlite_cur.fetchall()
                ticket_dicts = [
                    {
                        "id": r[0],
                        "alert_id": r[1],
                        "recommendation": r[2],
                        "evidence": parse_json(r[3]),
                        "confidence": float(r[4]),
                        "approval_status": r[5],
                        "approved_by": r[6],
                        "created_at": parse_datetime(r[7])
                    }
                    for r in ticket_rows
                ]
                pg_conn.execute(Ticket.__table__.insert(), ticket_dicts)
                print(f"  -> Successfully inserted {len(ticket_dicts)} tickets.")

                print("-" * 70)
                print("All 40,416 domain records successfully inserted. Committing transaction...")

            except Exception as e:
                print(f"\n[DATA INSERTION ERROR] Transaction failed: {e}")
                print("Rolling back transaction. No records were committed to Supabase.")
                trans.rollback()
                raise

        insert_elapsed = time.time() - start_time
        print(f"[COMMIT SUCCESS] All 40,416 records committed to Supabase in {insert_elapsed:.2f} seconds.")
        print("-" * 70)

        # -------------------------------------------------------------
        # 6. POSTGRESQL SEQUENCE SYNCHRONIZATION
        # Executed strictly AFTER successful commit of all inserted records.
        # PostgreSQL sequences are non-transactional (setval does not roll back).
        # -------------------------------------------------------------
        print("Synchronizing PostgreSQL autoincrement sequences...")
        try:
            with pg_conn.begin():
                # 1. sensor_readings_id_seq
                pg_conn.execute(text("""
                    SELECT setval(
                        'sensor_readings_id_seq',
                        COALESCE((SELECT MAX(id) FROM sensor_readings), 1),
                        EXISTS (SELECT 1 FROM sensor_readings)
                    );
                """))
                # 2. maintenance_history_id_seq
                pg_conn.execute(text("""
                    SELECT setval(
                        'maintenance_history_id_seq',
                        COALESCE((SELECT MAX(id) FROM maintenance_history), 1),
                        EXISTS (SELECT 1 FROM maintenance_history)
                    );
                """))

            # Read sequence state to verify
            seq_sr = pg_conn.execute(text("SELECT last_value, is_called FROM sensor_readings_id_seq;")).fetchone()
            seq_mh = pg_conn.execute(text("SELECT last_value, is_called FROM maintenance_history_id_seq;")).fetchone()

            print(f"  - 'sensor_readings_id_seq'      : last_value={seq_sr[0]}, is_called={seq_sr[1]} (Next ID: {seq_sr[0] + 1})")
            print(f"  - 'maintenance_history_id_seq'  : last_value={seq_mh[0]}, is_called={seq_mh[1]} (Next ID: {seq_mh[0] + 1})")
            print("Sequence synchronization verified successfully.")

        except Exception as seq_err:
            print(f"\n[SEQUENCE WARNING] Records were committed, but sequence synchronization encountered: {seq_err}")
            print("Safe Manual Recovery Procedure (run in Supabase SQL editor):")
            print("  SELECT setval('sensor_readings_id_seq', (SELECT MAX(id) FROM sensor_readings), true);")
            print("  SELECT setval('maintenance_history_id_seq', (SELECT MAX(id) FROM maintenance_history), true);")
            raise

        total_elapsed = time.time() - start_time
        print(f"\n[COMPLETE] SQLite to Supabase migration completed successfully in {total_elapsed:.2f} seconds!")
        print("=" * 70)

    sqlite_conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migrate SQLite records to Supabase PostgreSQL.")
    parser.add_argument("--dry-run", action="store_true", help="Perform pre-flight checks without inserting data")
    args = parser.parse_args()

    migrate(dry_run=args.dry_run)
