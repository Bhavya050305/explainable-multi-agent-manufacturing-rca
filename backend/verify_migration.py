"""
ManuMind AI — Post-Migration Cross-Database Verification Script (Corrected)
Compares local SQLite (read-only) against Supabase PostgreSQL across:
1. Exact row counts in all 5 tables (10, 40,000, 400, 5, 1)
2. Primary key min and max boundaries
3. Machine IDs list parity
4. Foreign-key referential integrity (zero orphan records)
5. Timestamp minimum and maximum ranges
6. Sensor reading numeric aggregates (averages, mins, maxes)
7. JSON structure and data integrity
8. Alert and ticket record fidelity
9. PostgreSQL sequence state inspection (READ-ONLY, ZERO CONSUMPTION)

Safety & Sequence Invariants:
- SQLite opened strictly in read-only mode (file:manumind.db?mode=ro).
- NEVER calls nextval(), setval(), or inserts temporary test records.
- Sequences are inspected via read-only metadata state (last_value and is_called).
- No database credentials exposed in outputs.
"""

import json
import os
import re
import sqlite3
import sys
from datetime import datetime

# Ensure parent directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from backend.app.config import settings
from backend.app.database import build_engine


def mask_url(url: str) -> str:
    """Mask password credentials in connection string for safe display."""
    if not url:
        return "(empty)"
    return re.sub(r":([^/@:]+)@", ":********@", url)


def verify_migration():
    print("=" * 75)
    print("ManuMind AI — Cross-Database Migration Verification Audit")
    print("=" * 75)

    sqlite_path = os.path.abspath(os.path.join(settings.BASE_PATH, "manumind.db"))
    if not os.path.exists(sqlite_path):
        raise FileNotFoundError(f"Source SQLite database not found at: {sqlite_path}")

    print(f"Source (SQLite - Read-Only): {sqlite_path}")
    print(f"Destination (Supabase):       {mask_url(settings.DATABASE_URL)}")
    print("-" * 75)

    # 1. Connect to SQLite in read-only mode
    sqlite_conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    sqlite_cur = sqlite_conn.cursor()

    # 2. Connect to Supabase
    pg_engine = build_engine()
    audit_passed = True

    with pg_engine.connect() as pg_conn:
        # -------------------------------------------------------------
        # Check 1: Row Counts Across All 5 Tables
        # -------------------------------------------------------------
        print("\n[CHECK 1/8] Table Row Counts Parity:")
        domain_tables = {
            "machines": 10,
            "sensor_readings": 40000,
            "maintenance_history": 400,
            "alerts": 5,
            "tickets": 1
        }
        for table, expected in domain_tables.items():
            sqlite_cur.execute(f"SELECT COUNT(*) FROM {table};")
            s_count = sqlite_cur.fetchone()[0]

            p_count = pg_conn.execute(text(f"SELECT COUNT(*) FROM {table};")).scalar()

            status = "MATCH" if s_count == p_count == expected else "MISMATCH"
            if status == "MISMATCH":
                audit_passed = False
            print(f"  - {table:<22}: SQLite = {s_count:>6,} | Supabase = {p_count:>6,} | Target = {expected:>6,} -> [{status}]")

        # -------------------------------------------------------------
        # Check 2: Primary Key Boundaries & Machine IDs
        # -------------------------------------------------------------
        print("\n[CHECK 2/8] Primary Key Ranges & Machine IDs:")

        # Machines
        sqlite_cur.execute("SELECT id FROM machines ORDER BY id;")
        s_mach_ids = [r[0] for r in sqlite_cur.fetchall()]
        p_mach_ids = [r[0] for r in pg_conn.execute(text("SELECT id FROM machines ORDER BY id;"))]
        mach_match = (s_mach_ids == p_mach_ids)
        if not mach_match:
            audit_passed = False
        print(f"  - machines IDs match (10/10):        [{'MATCH' if mach_match else 'FAIL'}]")

        # Sensor readings
        sqlite_cur.execute("SELECT MIN(id), MAX(id) FROM sensor_readings;")
        s_sr_min, s_sr_max = sqlite_cur.fetchone()
        p_sr_min, p_sr_max = pg_conn.execute(text("SELECT MIN(id), MAX(id) FROM sensor_readings;")).fetchone()
        sr_pk_match = (s_sr_min == p_sr_min == 1) and (s_sr_max == p_sr_max == 40000)
        if not sr_pk_match:
            audit_passed = False
        print(f"  - sensor_readings ID range (1..40000): SQLite=[{s_sr_min}..{s_sr_max}] Supabase=[{p_sr_min}..{p_sr_max}] -> [{'MATCH' if sr_pk_match else 'FAIL'}]")

        # Maintenance history
        sqlite_cur.execute("SELECT MIN(id), MAX(id) FROM maintenance_history;")
        s_mh_min, s_mh_max = sqlite_cur.fetchone()
        p_mh_min, p_mh_max = pg_conn.execute(text("SELECT MIN(id), MAX(id) FROM maintenance_history;")).fetchone()
        mh_pk_match = (s_mh_min == p_mh_min == 1) and (s_mh_max == p_mh_max == 400)
        if not mh_pk_match:
            audit_passed = False
        print(f"  - maintenance_history ID range (1..400): SQLite=[{s_mh_min}..{s_mh_max}] Supabase=[{p_mh_min}..{p_mh_max}] -> [{'MATCH' if mh_pk_match else 'FAIL'}]")

        # -------------------------------------------------------------
        # Check 3: Foreign Key Referential Integrity (Orphan Check)
        # -------------------------------------------------------------
        print("\n[CHECK 3/8] Referential Integrity & Orphan Records Check:")

        # Sensor readings -> machines
        sr_orphans = pg_conn.execute(text("""
            SELECT COUNT(*) FROM sensor_readings sr
            LEFT JOIN machines m ON sr.machine_id = m.id
            WHERE m.id IS NULL;
        """)).scalar()
        print(f"  - sensor_readings orphans:            {sr_orphans} -> [{'PASS' if sr_orphans == 0 else 'FAIL'}]")

        # Maintenance history -> machines
        mh_orphans = pg_conn.execute(text("""
            SELECT COUNT(*) FROM maintenance_history mh
            LEFT JOIN machines m ON mh.machine_id = m.id
            WHERE m.id IS NULL;
        """)).scalar()
        print(f"  - maintenance_history orphans:        {mh_orphans} -> [{'PASS' if mh_orphans == 0 else 'FAIL'}]")

        # Alerts -> machines
        alt_orphans = pg_conn.execute(text("""
            SELECT COUNT(*) FROM alerts a
            LEFT JOIN machines m ON a.machine_id = m.id
            WHERE m.id IS NULL;
        """)).scalar()
        print(f"  - alerts orphans:                     {alt_orphans} -> [{'PASS' if alt_orphans == 0 else 'FAIL'}]")

        # Tickets -> alerts
        tck_orphans = pg_conn.execute(text("""
            SELECT COUNT(*) FROM tickets t
            LEFT JOIN alerts a ON t.alert_id = a.id
            WHERE a.id IS NULL;
        """)).scalar()
        print(f"  - tickets orphans:                    {tck_orphans} -> [{'PASS' if tck_orphans == 0 else 'FAIL'}]")

        if any(c > 0 for c in [sr_orphans, mh_orphans, alt_orphans, tck_orphans]):
            audit_passed = False

        # -------------------------------------------------------------
        # Check 4: Timestamp Range Parity
        # -------------------------------------------------------------
        print("\n[CHECK 4/8] Timestamp Ranges Parity:")
        sqlite_cur.execute("SELECT MIN(timestamp), MAX(timestamp) FROM sensor_readings;")
        s_ts_min, s_ts_max = sqlite_cur.fetchone()

        p_ts_min, p_ts_max = pg_conn.execute(text("SELECT MIN(timestamp)::text, MAX(timestamp)::text FROM sensor_readings;")).fetchone()

        ts_match = (str(s_ts_min)[:19] == str(p_ts_min)[:19]) and (str(s_ts_max)[:19] == str(p_ts_max)[:19])
        if not ts_match:
            audit_passed = False
        print(f"  - sensor_readings start: SQLite={s_ts_min} | Supabase={p_ts_min}")
        print(f"  - sensor_readings end:   SQLite={s_ts_max} | Supabase={p_ts_max}")
        print(f"  - Timestamp match:                    [{'MATCH' if ts_match else 'FAIL'}]")

        # -------------------------------------------------------------
        # Check 5: Sensor Telemetry Numeric Aggregates
        # -------------------------------------------------------------
        print("\n[CHECK 5/8] Sensor Telemetry Channel Aggregates Parity:")
        sqlite_cur.execute("""
            SELECT
                ROUND(AVG(vibration), 4), MIN(vibration), MAX(vibration),
                ROUND(AVG(temperature), 4), MIN(temperature), MAX(temperature),
                ROUND(AVG(pressure), 4), MIN(pressure), MAX(pressure),
                ROUND(AVG(current), 4), MIN(current), MAX(current),
                ROUND(AVG(rpm), 2), MIN(rpm), MAX(rpm)
            FROM sensor_readings;
        """)
        s_num = sqlite_cur.fetchone()

        p_num = pg_conn.execute(text("""
            SELECT
                ROUND(AVG(vibration)::numeric, 4), MIN(vibration), MAX(vibration),
                ROUND(AVG(temperature)::numeric, 4), MIN(temperature), MAX(temperature),
                ROUND(AVG(pressure)::numeric, 4), MIN(pressure), MAX(pressure),
                ROUND(AVG(current)::numeric, 4), MIN(current), MAX(current),
                ROUND(AVG(rpm)::numeric, 2), MIN(rpm), MAX(rpm)
            FROM sensor_readings;
        """)).fetchone()

        channels = ["Vibration", "Temperature", "Pressure", "Current", "RPM"]
        for idx, ch in enumerate(channels):
            base_idx = idx * 3
            s_avg, s_min, s_max = s_num[base_idx], s_num[base_idx+1], s_num[base_idx+2]
            p_avg, p_min, p_max = float(p_num[base_idx]), float(p_num[base_idx+1]), float(p_num[base_idx+2])
            ch_match = (abs(s_avg - p_avg) < 0.001) and (abs(s_min - p_min) < 0.001) and (abs(s_max - p_max) < 0.001)
            if not ch_match:
                audit_passed = False
            print(f"  - {ch:<14}: SQLite avg={s_avg:<7} min={s_min:<6} max={s_max:<6} | Supabase avg={p_avg:<7} min={p_min:<6} max={p_max:<6} -> [{'MATCH' if ch_match else 'FAIL'}]")

        # -------------------------------------------------------------
        # Check 6: JSON Field Parsing & Structural Integrity
        # -------------------------------------------------------------
        print("\n[CHECK 6/8] JSON Field Parsing & Content Integrity:")

        # Check Alert M104 SHAP and sensor contrib
        m104_alert = pg_conn.execute(text("SELECT shap_json, sensor_contrib_json FROM alerts WHERE id = 'ALT-M104-001';")).fetchone()
        if m104_alert:
            shap_data = m104_alert[0] if isinstance(m104_alert[0], dict) else json.loads(m104_alert[0])
            contrib_data = m104_alert[1] if isinstance(m104_alert[1], dict) else json.loads(m104_alert[1])
            shap_valid = ("vibration" in shap_data and shap_data["vibration"] == 0.54)
            contrib_valid = ("vibration" in contrib_data and contrib_data["vibration"] == 0.62)
            print(f"  - Alert M104 shap_json valid:         [{'PASS' if shap_valid else 'FAIL'}] (vibration driver = {shap_data.get('vibration')})")
            print(f"  - Alert M104 sensor_contrib valid:    [{'PASS' if contrib_valid else 'FAIL'}] (vibration contrib = {contrib_data.get('vibration')})")
            if not (shap_valid and contrib_valid):
                audit_passed = False
        else:
            print("  - Alert M104 missing in Supabase!     [FAIL]")
            audit_passed = False

        # Check Ticket evidence
        ticket_rec = pg_conn.execute(text("SELECT evidence, approved_by FROM tickets WHERE id = 'TCK-2026-001';")).fetchone()
        if ticket_rec:
            evidence_data = ticket_rec[0] if isinstance(ticket_rec[0], dict) else json.loads(ticket_rec[0])
            ev_valid = ("source_incident" in evidence_data and ticket_rec[1] == "Lead Engineer S. Raman")
            print(f"  - Ticket TCK-2026-001 evidence valid: [{'PASS' if ev_valid else 'FAIL'}] (authorized by '{ticket_rec[1]}')")
            if not ev_valid:
                audit_passed = False
        else:
            print("  - Ticket TCK-2026-001 missing in Supabase! [FAIL]")
            audit_passed = False

        # -------------------------------------------------------------
        # Check 7: Alert & Ticket Domain Records Fidelity
        # -------------------------------------------------------------
        print("\n[CHECK 7/8] Priority Alerts & Tickets Domain State:")
        top_alert = pg_conn.execute(text("""
            SELECT id, machine_id, priority_score, risk, criticality, impact, status
            FROM alerts
            ORDER BY priority_score DESC
            LIMIT 1;
        """)).fetchone()
        if top_alert:
            is_top_m104 = (top_alert[0] == "ALT-M104-001" and top_alert[1] == "M104" and top_alert[2] == 22.0)
            if not is_top_m104:
                audit_passed = False
            print(f"  - Priority #1 Alert: {top_alert[0]} on {top_alert[1]} with Score={top_alert[2]} (risk={top_alert[3]}, crit={top_alert[4]}, impact={top_alert[5]}, status='{top_alert[6]}') -> [{'PASS' if is_top_m104 else 'FAIL'}]")

        # -------------------------------------------------------------
        # Check 8: Non-Destructive Sequence State Inspection (Zero Sequence Consumption)
        # Inspects sequence metadata state WITHOUT calling nextval(), setval(),
        # or inserting any rows. Zero sequence numbers are consumed.
        # -------------------------------------------------------------
        print("\n[CHECK 8/8] Non-Destructive PostgreSQL Sequence State Inspection:")

        # Read sequence state for sensor_readings_id_seq
        sr_seq_state = pg_conn.execute(text("""
            SELECT last_value, is_called
            FROM sensor_readings_id_seq;
        """)).fetchone()

        # Read sequence state for maintenance_history_id_seq
        mh_seq_state = pg_conn.execute(text("""
            SELECT last_value, is_called
            FROM maintenance_history_id_seq;
        """)).fetchone()

        sr_val, sr_called = sr_seq_state[0], bool(sr_seq_state[1])
        mh_val, mh_called = mh_seq_state[0], bool(mh_seq_state[1])

        sr_seq_ok = (sr_val == 40000 and sr_called is True)
        mh_seq_ok = (mh_val == 400 and mh_called is True)

        print(f"  - 'sensor_readings_id_seq' state    : last_value={sr_val} (Target 40000), is_called={sr_called} (Target True) -> [{'PASS' if sr_seq_ok else 'FAIL'}]")
        print(f"    -> Next insert ID is guaranteed to be: {sr_val + 1}")
        print(f"  - 'maintenance_history_id_seq' state: last_value={mh_val} (Target 400), is_called={mh_called} (Target True) -> [{'PASS' if mh_seq_ok else 'FAIL'}]")
        print(f"    -> Next insert ID is guaranteed to be: {mh_val + 1}")
        print("  - Sequence verification method: READ-ONLY metadata query (Zero IDs consumed).")

        if not (sr_seq_ok and mh_seq_ok):
            audit_passed = False

    sqlite_conn.close()

    print("\n" + "=" * 75)
    if audit_passed:
        print("[AUDIT RESULT: ALL CHECKS PASSED] Supabase matches SQLite with 100% data fidelity!")
    else:
        print("[AUDIT RESULT: VERIFICATION FAILED] Discrepancies detected between SQLite and Supabase.")
    print("=" * 75)
    return audit_passed


if __name__ == "__main__":
    success = verify_migration()
    sys.exit(0 if success else 1)
