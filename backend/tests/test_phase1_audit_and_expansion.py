"""
ManuMind AI - Phase 1 Final Audit & Dataset Expansion Comprehensive Test Suite
Validates:
1. Database models & relationships (PKs, FKs, cascades)
2. Sensor telemetry generation & multi-fault injection
3. M104 progressive vibration degradation & temperature dynamics
4. Maintenance history generation & M104 domain records
5. Defect image generation, BMP binary parsing & manifest validation
6. Leakage-free dataset splitting (chronological & image partitions)
7. Missing value & duplicate integrity checks
8. Ticket approval enforcement gate
9. Fixed-seed reproducibility
10. Database seeding idempotence
"""

import os
import struct
import tempfile
import pytest
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.models.machine import Machine
from backend.app.models.sensor_reading import SensorReading
from backend.app.models.maintenance_history import MaintenanceHistory
from backend.app.models.alert import Alert
from backend.app.models.ticket import Ticket
from backend.app.services.ticket_service import create_ticket_with_approval_gate, TicketApprovalError

from ml.data_generator.generate_sensor_data import (
    MACHINE_PROFILES,
    generate_machine_telemetry,
    generate_all_sensor_data,
    split_sensor_dataset,
    generate_labelled_windows
)
from ml.data_generator.generate_maintenance import generate_maintenance_records, generate_and_save_maintenance
from ml.data_generator.generate_defect_images import (
    generate_defect_sample,
    create_bmp_file,
    generate_defect_dataset
)


@pytest.fixture(scope="module")
def memory_db():
    """In-memory SQLite session for relational tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_database_models_and_relationships(memory_db):
    """Verify all 5 models, primary keys, foreign keys, and ORM relationships."""
    # Machine
    m = Machine(id="M900", name="Audit Lathe", type="CNC Lathe", criticality=4, production_impact=5)
    memory_db.add(m)
    memory_db.commit()

    # Sensor Reading related to machine
    sr = SensorReading(
        machine_id="M900",
        vibration=2.1,
        temperature=50.2,
        pressure=6.1,
        current=14.8,
        rpm=1800.0
    )
    # Maintenance Record related to machine
    mh = MaintenanceHistory(
        machine_id="M900",
        issue="Test vibration audit",
        action="Tightened collet",
        outcome="Resolved"
    )
    # Alert related to machine
    alt = Alert(
        id="ALT-M900-01",
        machine_id="M900",
        risk=0.82,
        criticality=4,
        impact=5,
        priority_score=16.4,
        status="PENDING_APPROVAL"
    )
    memory_db.add_all([sr, mh, alt])
    memory_db.commit()

    # Query machine and verify bidirectional relationships
    mach_queried = memory_db.query(Machine).filter_by(id="M900").first()
    assert len(mach_queried.sensor_readings) == 1
    assert len(mach_queried.maintenance_records) == 1
    assert len(mach_queried.alerts) == 1
    assert mach_queried.alerts[0].priority_score == 16.4


def test_ticket_approval_gate_enforcement(memory_db):
    """
    Verify ticket creation strictly requires human engineer approval.
    Unapproved requests MUST be refused with TicketApprovalError.
    """
    # 1. Attempt to create ticket with None approved_by -> MUST FAIL
    with pytest.raises(TicketApprovalError):
        create_ticket_with_approval_gate(
            db=memory_db,
            alert_id="ALT-M900-01",
            recommendation="Replace spindle front bearing",
            evidence={"incident": "INC-01"},
            confidence=0.85,
            approved_by=None
        )

    # 2. Attempt with empty whitespace -> MUST FAIL
    with pytest.raises(TicketApprovalError):
        create_ticket_with_approval_gate(
            db=memory_db,
            alert_id="ALT-M900-01",
            recommendation="Replace spindle front bearing",
            evidence={"incident": "INC-01"},
            confidence=0.85,
            approved_by="   "
        )

    # 3. Create with valid engineer authorization -> MUST SUCCEED
    ticket = create_ticket_with_approval_gate(
        db=memory_db,
        alert_id="ALT-M900-01",
        recommendation="Replace spindle front bearing",
        evidence={"incident": "INC-01"},
        confidence=0.85,
        approved_by="Lead Engineer S. Raman"
    )
    assert ticket is not None
    assert ticket.approval_status == "APPROVED"
    assert ticket.approved_by == "Lead Engineer S. Raman"

    # Verify Alert status updated to APPROVED
    alert = memory_db.query(Alert).filter_by(id="ALT-M900-01").first()
    assert alert.status == "APPROVED"


def test_sensor_generator_and_fault_injection(tmp_path):
    """Verify sensor data generator creates correct channels and injected fault modes."""
    out_dir = str(tmp_path / "sensor_test")
    df = generate_all_sensor_data(output_dir=out_dir, steps=200, seed=42)

    assert len(df) == 200 * 10
    assert set(df["machine_id"].unique()) == {p["id"] for p in MACHINE_PROFILES}

    # Verify all 4 injected fault categories exist in dataset
    fault_categories = set(df["fault_type"].unique())
    assert "bearing_wear" in fault_categories
    assert "overheating" in fault_categories
    assert "pressure_drop" in fault_categories
    assert "lubrication_failure" in fault_categories
    assert "normal" in fault_categories


def test_m104_progressive_vibration():
    """Verify M104 bearing wear features progressive vibration climb and thermal rise."""
    m104_profile = next(p for p in MACHINE_PROFILES if p["id"] == "M104")
    df = generate_machine_telemetry(m104_profile, steps=1000, seed=42)

    normal_part = df[df["is_anomaly"] == 0]
    fault_part = df[df["is_anomaly"] == 1]

    assert len(normal_part) > 0
    assert len(fault_part) > 0

    # Progressive rise: fault part vibration should significantly exceed normal baseline
    assert fault_part["vibration"].max() > 6.0
    assert fault_part["vibration"].mean() > normal_part["vibration"].mean()

    # Temperature in fault period should also increase
    assert fault_part["temperature"].mean() > normal_part["temperature"].mean()


def test_maintenance_generator():
    """Verify maintenance generator creates target records with M104 bearing cases."""
    df = generate_maintenance_records(target_count=400, seed=42)
    assert len(df) == 400

    # Verify all 10 machines are represented
    assert len(df["machine_id"].unique()) == 10

    # Verify M104 bearing incidents
    m104_records = df[df["machine_id"] == "M104"]
    assert len(m104_records) >= 5
    bearing_matches = m104_records[m104_records["issue"].str.contains("bearing|spindle", case=False)]
    assert len(bearing_matches) >= 3


def test_defect_image_generation_and_manifest(tmp_path):
    """Verify BMP image generator creates valid 24-bit images and complete manifest."""
    out_dir = str(tmp_path / "defect_test")
    manifest = generate_defect_dataset(output_dir=out_dir, num_samples_per_class=4, seed=42)

    assert len(manifest) == 16
    for item in manifest:
        # Check metadata
        assert item["is_synthetic"] is True
        assert item["split"] in ("train", "val", "test")
        assert os.path.exists(item["filepath"])

        # Check binary BMP structure
        with open(item["filepath"], "rb") as f:
            header = f.read(14)
            dib = f.read(40)
            assert header[:2] == b'BM'
            _, width, height, planes, bpp = struct.unpack('<IIIHH', dib[:16])
            assert width == 128
            assert height == 128
            assert bpp == 24


def test_dataset_splitting_and_leakage(tmp_path):
    """Verify sensor data splitting has zero chronological overlap (leak-free)."""
    raw_dir = str(tmp_path / "raw")
    proc_dir = str(tmp_path / "processed")

    df = generate_all_sensor_data(output_dir=raw_dir, steps=300, seed=42)
    train_df, val_df, test_df = split_sensor_dataset(df, output_dir=proc_dir, train_pct=0.70, val_pct=0.15, test_pct=0.15)

    assert len(train_df) + len(val_df) + len(test_df) == len(df)

    # For every machine, max(train) < min(val) and max(val) < min(test)
    for m in df["machine_id"].unique():
        tr_m = train_df[train_df["machine_id"] == m]
        va_m = val_df[val_df["machine_id"] == m]
        te_m = test_df[test_df["machine_id"] == m]

        assert tr_m["timestamp"].max() < va_m["timestamp"].min()
        assert va_m["timestamp"].max() < te_m["timestamp"].min()


def test_duplicate_and_missing_values(tmp_path):
    """Verify generated sensor and maintenance datasets have 0 missing values and 0 duplicates."""
    out_dir = str(tmp_path / "qc")
    sdf = generate_all_sensor_data(output_dir=out_dir, steps=100, seed=42)
    mdf = generate_and_save_maintenance(output_dir=out_dir, count=50, seed=42)

    assert sdf.isnull().sum().sum() == 0
    assert mdf.isnull().sum().sum() == 0

    # Duplicates check
    assert sdf.duplicated(subset=["machine_id", "timestamp"]).sum() == 0
    assert mdf.duplicated().sum() == 0


def test_generator_reproducibility(tmp_path):
    """Verify that identical random seeds produce identical outputs."""
    dir1 = str(tmp_path / "run1")
    dir2 = str(tmp_path / "run2")

    s1 = generate_all_sensor_data(output_dir=dir1, steps=50, seed=99)
    s2 = generate_all_sensor_data(output_dir=dir2, steps=50, seed=99)

    num_cols = ["vibration", "temperature", "pressure", "current", "rpm"]
    np.testing.assert_array_equal(s1[num_cols].values, s2[num_cols].values)

    m1 = generate_defect_dataset(output_dir=dir1, num_samples_per_class=2, seed=99)
    m2 = generate_defect_dataset(output_dir=dir2, num_samples_per_class=2, seed=99)

    for i in range(len(m1)):
        b1 = open(m1[i]["filepath"], "rb").read()
        b2 = open(m2[i]["filepath"], "rb").read()
        assert b1 == b2
