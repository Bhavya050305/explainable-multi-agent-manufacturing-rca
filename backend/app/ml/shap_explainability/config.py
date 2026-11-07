"""
ManuMind AI — Isolation Forest SHAP Explainability Configuration
Department of AI & Data Science — RMK Engineering College

Centralizes hyperparameters, feature definitions, background sampling specifications,
and output path configuration for Kernel SHAP anomaly explainability.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Verified production feature names and column order
FEATURE_COLUMNS: List[str] = [
    "vibration",
    "temperature",
    "pressure",
    "current",
    "rpm"
]

# Physical engineering units for domain context
FEATURE_UNITS: Dict[str, str] = {
    "vibration": "mm/s",
    "temperature": "°C",
    "pressure": "bar",
    "current": "A",
    "rpm": "RPM"
}

# Background sampling specifications
STRATIFIED_MACHINE_IDS: List[str] = [
    "M101", "M102", "M103", "M104", "M105",
    "M106", "M107", "M108", "M109", "M110"
]
SAMPLES_PER_MACHINE: int = 5
TOTAL_BACKGROUND_SAMPLES: int = len(STRATIFIED_MACHINE_IDS) * SAMPLES_PER_MACHINE  # 50
RANDOM_SEED: int = 42

# Coalition space for 5 features: 2^5 = 32
SHAP_NSAMPLES: int = 32

# Mathematical additivity tolerance (machine precision boundary)
ADDITIVITY_TOLERANCE: float = 1e-6

# Attribution measurement units
ATTRIBUTION_UNITS: str = "dimensionless_anomaly_score_delta"


@dataclass
class ShapExplainerConfig:
    """Master configuration for the Isolation Forest SHAP Explainer."""

    # Features
    feature_cols: List[str] = field(default_factory=lambda: list(FEATURE_COLUMNS))
    feature_units: Dict[str, str] = field(default_factory=lambda: dict(FEATURE_UNITS))
    n_features: int = 5

    # Sampling and background
    stratified_machines: List[str] = field(default_factory=lambda: list(STRATIFIED_MACHINE_IDS))
    samples_per_machine: int = SAMPLES_PER_MACHINE
    total_background_samples: int = TOTAL_BACKGROUND_SAMPLES
    random_seed: int = RANDOM_SEED
    shap_nsamples: int = SHAP_NSAMPLES
    additivity_tolerance: float = ADDITIVITY_TOLERANCE

    # Artifact paths
    model_path: str = "ml/models_store/isolation_forest.joblib"
    metadata_path: str = "ml/models_store/isolation_forest_metadata.json"
    scaler_path: str = "ml/models_store/sensor_scaler.joblib"

    # Dataset paths
    train_sensor_csv: str = "data/processed/scaled_sensor_train.csv"
    val_sensor_csv: str = "data/processed/scaled_sensor_val.csv"
    test_sensor_csv: str = "data/processed/scaled_sensor_test.csv"
    raw_sensor_csv: str = "data/raw/sensor_readings.csv"

    # Reporting and graph destinations
    graph_dir: str = "reports/phase2/shap_explainability/graphs"
    results_json_path: str = "reports/phase2/shap_explainability/shap_evaluation_results.json"
    report_md_path: str = "reports/phase2/shap_explainability_report.md"

    # Metadata
    explained_model_name: str = "isolation_forest"
    explained_output_name: str = "anomaly_intensity"
    explainer_method_name: str = "kernel_shap"
    attribution_units: str = ATTRIBUTION_UNITS
