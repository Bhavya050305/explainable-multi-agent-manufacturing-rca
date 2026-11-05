"""
ManuMind AI — Sensor-Level Anomaly Attribution Configuration
Department of AI & Data Science — RMK Engineering College

Defines paths, feature definitions, synthetic fault mechanisms, and attribution settings.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any


FEATURE_COLUMNS: List[str] = ["vibration", "temperature", "pressure", "current", "rpm"]

# Physical units for engineering interpretation
FEATURE_UNITS: Dict[str, str] = {
    "vibration": "mm/s",
    "temperature": "°C",
    "pressure": "bar",
    "current": "A",
    "rpm": "RPM"
}

# Known synthetic fault mechanisms directly from generate_sensor_data.py
SYNTHETIC_FAULT_MAPPING: Dict[str, Dict[str, Any]] = {
    "M102": {
        "name": "Hydraulic Stamping Press 02",
        "fault": "overheating",
        "primary_expected": "temperature",
        "secondary_expected": "pressure",
        "expected_direction": {"temperature": "positive", "pressure": "positive"},
        "mechanism": "Hydraulic oil radiator clogging and cooling fan failure causes severe temperature runaway (+37.5σ) and moderate hydraulic pressure rise (+15.8σ)."
    },
    "M104": {
        "name": "High-Speed Spindle Center 04",
        "fault": "bearing_wear",
        "primary_expected": "vibration",
        "secondary_expected": "temperature",
        "expected_direction": {"vibration": "positive", "temperature": "positive", "rpm": "negative"},
        "mechanism": "Inner race fatigue spalling triggers severe vibration surge (+39.0σ) and cage chatter, accompanied by friction heating (+7.5σ) and spindle drag."
    },
    "M107": {
        "name": "Centrifugal Compressor 07",
        "fault": "pressure_drop",
        "primary_expected": "pressure",
        "secondary_expected": "current",
        "expected_direction": {"pressure": "negative", "current": "positive"},
        "mechanism": "Pneumatic manifold seal rupture causes severe delivery pressure drop (-31.7σ, negative residual), with motor current ramping (+9.3σ) to maintain head."
    },
    "M109": {
        "name": "Heavy Industrial Gearbox 09",
        "fault": "lubrication_failure",
        "primary_expected": "current",
        "secondary_expected": "vibration",
        "co_candidates": ["current", "vibration", "temperature"],
        "expected_direction": {"current": "positive", "vibration": "positive", "temperature": "positive"},
        "mechanism": "Boundary dry friction induces motor stator torque surge (+21.8σ, primary), gear tooth chatter vibration (+18.5σ, secondary), and housing thermal heating (+14.6σ, tertiary)."
    }
}


@dataclass
class SensorAttributionConfig:
    """Master configuration for Sensor-Level Anomaly Attribution."""

    # Features
    feature_cols: List[str] = field(default_factory=lambda: list(FEATURE_COLUMNS))
    window_size: int = 30
    n_features: int = 5

    # Artifact paths
    scaler_path: str = "ml/models_store/sensor_scaler.joblib"
    if_model_path: str = "ml/models_store/isolation_forest.joblib"
    if_metadata_path: str = "ml/models_store/isolation_forest_metadata.json"
    lstm_model_path: str = "ml/models_store/lstm_autoencoder.keras"
    lstm_metadata_path: str = "ml/models_store/lstm_autoencoder_metadata.json"

    # Dataset paths
    train_sequences_path: str = "data/processed/sequences_train.npz"
    val_sequences_path: str = "data/processed/sequences_val.npz"
    test_sequences_path: str = "data/processed/sequences_test.npz"
    train_sensor_csv: str = "data/processed/sensor_train.csv"
    val_sensor_csv: str = "data/processed/sensor_val.csv"
    test_sensor_csv: str = "data/processed/sensor_test.csv"

    # Output directories
    output_dir: str = "reports/phase2/sensor_attribution"
    figures_dir: str = "reports/phase2/sensor_attribution/graphs"

    # Attribution settings
    epsilon: float = 1e-12
    batch_size: int = 64
