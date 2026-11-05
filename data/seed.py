"""
ManuMind AI - Enhanced Database Seeding Script
Initializes database schema, populates machines (M101-M110), sensor readings,
maintenance history, baseline priority alerts, and tickets.
Supports full dataset expansion (30,000–50,000 sensor readings, ~400 maintenance logs, ~600 defect images).
"""

import argparse
import os
import sys
from datetime import datetime, timedelta

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.config import settings
from backend.app.database import engine, SessionLocal, init_db
from backend.app.models.machine import Machine
from backend.app.models.sensor_reading import SensorReading
from backend.app.models.maintenance_history import MaintenanceHistory
from backend.app.models.alert import Alert
from backend.app.models.ticket import Ticket
from ml.data_generator.generate_sensor_data import (
    MACHINE_PROFILES,
    generate_all_sensor_data,
    split_sensor_dataset,
    generate_labelled_windows
)
from ml.data_generator.generate_maintenance import generate_and_save_maintenance
from ml.data_generator.generate_defect_images import generate_defect_dataset


def seed_database(steps_per_machine: int = 4000, maintenance_count: int = 400, defect_per_class: int = 150, seed: int = 42):
    """
    Seed entire database with expanded high-quality synthetic datasets:
    - 10 Machines
    - Sensor readings (4,000 steps/machine = 40,000 records)
    - Chronological Train / Val / Test sensor splits (70% / 15% / 15%)
    - Labelled sliding windows
    - 400 Maintenance logs across 24 months
    - Top-5 priority alerts (M104 critical bearing wear priority score = 22.0)
    - Seeded historical approved ticket TCK-2026-001
    - 600 defect images across 4 classes with metadata manifest
    """
    print("=" * 70)
    print("ManuMind AI - Database Seeding & Dataset Generation")
    print(f"Target Database: {settings.DATABASE_URL}")
    print(f"Config: {steps_per_machine} steps/mach ({steps_per_machine*10} total), {maintenance_count} maint records, {defect_per_class*4} defect images")
    print("=" * 70)

    # 1. Initialize tables
    print("[1/7] Initializing database schema...")
    init_db()

    db = SessionLocal()
    try:
        # Clean existing records for clean seed
        print("[2/7] Purging existing records for fresh seed...")
        db.query(Ticket).delete()
        db.query(Alert).delete()
        db.query(SensorReading).delete()
        db.query(MaintenanceHistory).delete()
        db.query(Machine).delete()
        db.commit()

        # 2. Seed Machines
        print("[3/7] Seeding Machines (M101-M110)...")
        for p in MACHINE_PROFILES:
            mach = Machine(
                id=p["id"],
                name=p["name"],
                type=p["type"],
                criticality=p["criticality"],
                production_impact=p["production_impact"]
            )
            db.add(mach)
        db.commit()
        print(f"  -> Successfully registered {len(MACHINE_PROFILES)} machines.")

        # 3. Generate Sensor Telemetry
        print(f"[4/7] Generating sensor telemetry ({steps_per_machine} steps x 10 machines = {steps_per_machine*10} records)...")
        df_sensors = generate_all_sensor_data(output_dir="data/raw", steps=steps_per_machine, seed=seed)

        # Partition datasets
        split_sensor_dataset(df_sensors, output_dir="data/processed", train_pct=0.70, val_pct=0.15, test_pct=0.15)
        generate_labelled_windows(df_sensors, output_dir="data/processed", window_size=30, stride=10)

        # Bulk insert sensor readings into database
        sensor_entities = []
        for _, row in df_sensors.iterrows():
            ts = row["timestamp"]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            elif hasattr(ts, "to_pydatetime"):
                ts = ts.to_pydatetime()

            reading = SensorReading(
                machine_id=row["machine_id"],
                timestamp=ts,
                vibration=float(row["vibration"]),
                temperature=float(row["temperature"]),
                pressure=float(row["pressure"]),
                current=float(row["current"]),
                rpm=float(row["rpm"])
            )
            sensor_entities.append(reading)

        db.bulk_save_objects(sensor_entities)
        db.commit()
        print(f"  -> Inserted {len(sensor_entities)} sensor telemetry records into database.")

        # 4. Generate & Seed Maintenance History
        print(f"[5/7] Generating maintenance records ({maintenance_count} records)...")
        df_maint = generate_and_save_maintenance(output_dir="data/raw", count=maintenance_count, seed=seed)

        maint_entities = []
        for _, row in df_maint.iterrows():
            rec_date = row["date"]
            if isinstance(rec_date, str):
                rec_date = datetime.fromisoformat(rec_date)
            elif hasattr(rec_date, "to_pydatetime"):
                rec_date = rec_date.to_pydatetime()

            m = MaintenanceHistory(
                machine_id=row["machine_id"],
                date=rec_date,
                issue=row["issue"],
                action=row["action"],
                outcome=row["outcome"]
            )
            maint_entities.append(m)

        db.bulk_save_objects(maint_entities)
        db.commit()
        print(f"  -> Inserted {len(maint_entities)} maintenance logs into database.")

        # 5. Seed Realistic Priority Alerts
        print("[6/7] Seeding baseline industrial alerts...")
        now = datetime.utcnow()

        # M104 Alert (Priority #1: Bearing wear - The primary viva demo target!)
        # Priority Score = risk (0.88) * criticality (5) * impact (5) = 22.0
        alert_m104 = Alert(
            id="ALT-M104-001",
            machine_id="M104",
            risk=0.88,
            criticality=5,
            impact=5,
            priority_score=round(0.88 * 5 * 5, 2),  # 22.0
            shap_json={
                "vibration": 0.54,
                "temperature": 0.22,
                "rpm": -0.15,
                "current": 0.08,
                "pressure": 0.01
            },
            sensor_contrib_json={
                "vibration": 0.62,
                "temperature": 0.20,
                "rpm": 0.11,
                "current": 0.05,
                "pressure": 0.02
            },
            status="PENDING_APPROVAL",
            created_at=now - timedelta(minutes=14)
        )

        # M109 Alert (Priority #2: Gearbox lubrication failure)
        alert_m109 = Alert(
            id="ALT-M109-001",
            machine_id="M109",
            risk=0.72,
            criticality=5,
            impact=4,
            priority_score=round(0.72 * 5 * 4, 2),  # 14.4
            shap_json={
                "current": 0.45,
                "temperature": 0.32,
                "vibration": 0.18,
                "pressure": -0.05,
                "rpm": -0.02
            },
            sensor_contrib_json={
                "current": 0.48,
                "temperature": 0.35,
                "vibration": 0.12,
                "rpm": 0.03,
                "pressure": 0.02
            },
            status="PENDING_APPROVAL",
            created_at=now - timedelta(minutes=45)
        )

        # M107 Alert (Priority #3: Compressor seal pressure drop)
        alert_m107 = Alert(
            id="ALT-M107-001",
            machine_id="M107",
            risk=0.68,
            criticality=4,
            impact=5,
            priority_score=round(0.68 * 4 * 5, 2),  # 13.6
            shap_json={
                "pressure": -0.52,
                "current": 0.28,
                "temperature": 0.12,
                "vibration": 0.05,
                "rpm": 0.01
            },
            sensor_contrib_json={
                "pressure": 0.58,
                "current": 0.25,
                "temperature": 0.10,
                "vibration": 0.04,
                "rpm": 0.03
            },
            status="PENDING_APPROVAL",
            created_at=now - timedelta(hours=2)
        )

        # M102 Alert (Priority #4: Hydraulic press overheating)
        alert_m102 = Alert(
            id="ALT-M102-001",
            machine_id="M102",
            risk=0.75,
            criticality=4,
            impact=4,
            priority_score=round(0.75 * 4 * 4, 2),  # 12.0
            shap_json={
                "temperature": 0.58,
                "pressure": 0.22,
                "current": 0.10,
                "vibration": 0.04,
                "rpm": 0.02
            },
            sensor_contrib_json={
                "temperature": 0.65,
                "pressure": 0.20,
                "current": 0.08,
                "vibration": 0.04,
                "rpm": 0.03
            },
            status="PENDING_APPROVAL",
            created_at=now - timedelta(hours=3, minutes=15)
        )

        # M105 Alert (Priority #5: Robotic Welder minor watch)
        alert_m105 = Alert(
            id="ALT-M105-001",
            machine_id="M105",
            risk=0.35,
            criticality=3,
            impact=4,
            priority_score=round(0.35 * 3 * 4, 2),  # 4.2
            shap_json={
                "current": 0.25,
                "vibration": 0.15,
                "temperature": 0.05,
                "rpm": -0.02,
                "pressure": 0.01
            },
            sensor_contrib_json={
                "current": 0.40,
                "vibration": 0.30,
                "temperature": 0.15,
                "rpm": 0.10,
                "pressure": 0.05
            },
            status="INVESTIGATING",
            created_at=now - timedelta(hours=5)
        )

        db.add_all([alert_m104, alert_m109, alert_m107, alert_m102, alert_m105])
        db.commit()

        # Seed sample historical approved ticket for M105
        ticket_hist = Ticket(
            id="TCK-2026-001",
            alert_id="ALT-M105-001",
            recommendation="Inspect Axis 3 servo cable assembly and clean robot torch nozzle contacts.",
            evidence={
                "source_incident": "INC-2025-089",
                "matched_sop": "SOP-WELDER-03",
                "confidence": 0.88,
                "summary": "Similar periodic current anomaly observed in Nov 2025 resolved by cable harness tightening."
            },
            confidence=0.88,
            approval_status="APPROVED",
            approved_by="Lead Engineer S. Raman",
            created_at=now - timedelta(hours=4)
        )
        db.add(ticket_hist)
        db.commit()
        print("  -> Created top-5 ranked alerts (M104 priority #1 = 22.0) and historical approved ticket TCK-2026-001.")

        # 6. Generate Defect Images
        print(f"[7/7] Generating defect inspection image dataset ({defect_per_class} per class x 4 classes = {defect_per_class*4} images)...")
        generate_defect_dataset(output_dir="data/defect_images", num_samples_per_class=defect_per_class, seed=seed)

        print("=" * 70)
        print("ManuMind AI - Database Seeding & Dataset Generation Completed!")
        print("=" * 70)

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed database with synthetic industrial data.")
    parser.add_argument("--steps", type=int, default=4000, help="Sensor steps per machine (default: 4000 -> 40,000 readings)")
    parser.add_argument("--maint", type=int, default=400, help="Maintenance records count (default: 400)")
    parser.add_argument("--defect-per-class", type=int, default=150, help="Defect images per class (default: 150 -> 600 total)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    seed_database(
        steps_per_machine=args.steps,
        maintenance_count=args.maint,
        defect_per_class=args.defect_per_class,
        seed=args.seed
    )
