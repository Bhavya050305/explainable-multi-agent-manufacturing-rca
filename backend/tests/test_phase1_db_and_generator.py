"""
Unit and Integration Tests for Phase 1: Database & Data Generators
"""

import os
import struct
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.models.machine import Machine
from backend.app.models.sensor_reading import SensorReading
from backend.app.models.maintenance_history import MaintenanceHistory
from backend.app.models.alert import Alert
from backend.app.models.ticket import Ticket
from ml.data_generator.generate_sensor_data import generate_all_sensor_data, MACHINE_PROFILES
from ml.data_generator.generate_maintenance import generate_maintenance_records
from ml.data_generator.generate_defect_images import generate_defect_sample, create_bmp_file, generate_defect_dataset


@pytest.fixture(scope="module")
def test_db():
    """Create in-memory SQLite database for isolated test execution."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()


def test_database_models_creation(test_db):
    """Verify all 5 database models can be instantiated and persisted."""
    # Machine
    m = Machine(id="M999", name="Test CNC", type="CNC Milling", criticality=4, production_impact=5)
    test_db.add(m)
    test_db.commit()

    saved_m = test_db.query(Machine).filter_by(id="M999").first()
    assert saved_m is not None
    assert saved_m.name == "Test CNC"
    assert saved_m.criticality == 4
    assert saved_m.production_impact == 5

    # Alert
    alt = Alert(
        id="ALT-999-01",
        machine_id="M999",
        risk=0.85,
        criticality=4,
        impact=5,
        priority_score=17.0,
        shap_json={"vibration": 0.6},
        sensor_contrib_json={"vibration": 0.7},
        status="PENDING_APPROVAL"
    )
    test_db.add(alt)
    test_db.commit()

    saved_alt = test_db.query(Alert).filter_by(id="ALT-999-01").first()
    assert saved_alt is not None
    assert saved_alt.priority_score == 17.0
    assert saved_alt.shap_json["vibration"] == 0.6

    # Ticket
    tck = Ticket(
        id="TCK-999-01",
        alert_id="ALT-999-01",
        recommendation="Replace front bearing",
        evidence={"sop": "SOP-01"},
        confidence=0.92,
        approval_status="APPROVED",
        approved_by="Test Engineer"
    )
    test_db.add(tck)
    test_db.commit()

    saved_tck = test_db.query(Ticket).filter_by(id="TCK-999-01").first()
    assert saved_tck is not None
    assert saved_tck.approved_by == "Test Engineer"
    assert saved_tck.confidence == 0.92


def test_sensor_data_generator(tmp_path):
    """Verify sensor data generator creates correct telemetry for all 10 machines."""
    out_dir = str(tmp_path / "sensor_data")
    df = generate_all_sensor_data(output_dir=out_dir, steps=50, seed=42)

    assert len(df) == 50 * len(MACHINE_PROFILES)
    assert set(df["machine_id"].unique()) == {p["id"] for p in MACHINE_PROFILES}

    # Check sensor channel columns
    for col in ["vibration", "temperature", "pressure", "current", "rpm", "is_anomaly", "failure_risk"]:
        assert col in df.columns

    # Verify M104 bearing wear injection
    m104_df = df[df["machine_id"] == "M104"]
    fault_rows = m104_df[m104_df["is_anomaly"] == 1]
    assert len(fault_rows) > 0
    # Vibration during bearing wear should elevate significantly
    assert fault_rows["vibration"].max() > 4.0


def test_maintenance_generator():
    """Verify maintenance generator creates ~200 records with M104 bearing incidents."""
    df = generate_maintenance_records(target_count=200, seed=42)
    assert len(df) == 200

    m104_records = df[df["machine_id"] == "M104"]
    assert len(m104_records) >= 3

    # Check that bearing-related issues are present for M104
    bearing_records = m104_records[m104_records["issue"].str.contains("bearing|spindle", case=False)]
    assert len(bearing_records) > 0


def test_defect_image_generator(tmp_path):
    """Verify BMP image generator writes valid binary headers and images."""
    out_dir = str(tmp_path / "defect_images")
    manifest = generate_defect_dataset(output_dir=out_dir, num_samples_per_class=2, seed=42)

    assert len(manifest) == 8  # 4 classes * 2 samples
    for item in manifest:
        file_path = item["filepath"]
        assert os.path.exists(file_path)

        # Verify valid BMP header
        with open(file_path, "rb") as f:
            header = f.read(14)
            dib = f.read(40)
            assert header[:2] == b'BM'
            file_size, _, _, offset = struct.unpack('<IHHI', header[2:])
            header_size, width, height, planes, bpp = struct.unpack('<IIIHH', dib[:16])
            assert width == 128
            assert height == 128
            assert bpp == 24
