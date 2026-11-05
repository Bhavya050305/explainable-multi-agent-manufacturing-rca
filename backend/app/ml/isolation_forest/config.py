"""
ManuMind AI — Isolation Forest Configuration
Department of AI & Data Science — RMK Engineering College
"""

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class IsolationForestConfig:
    """Hyperparameters, dataset paths, and output destinations for Isolation Forest."""

    # Sensor features
    feature_cols: List[str] = field(
        default_factory=lambda: ["vibration", "temperature", "pressure", "current", "rpm"]
    )

    # Model hyperparameters
    n_estimators: int = 200
    max_samples: int = 256
    contamination: str = "auto"
    random_state: int = 42
    n_jobs: int = -1

    # Data paths (using preprocessed & scaled datasets)
    train_data_path: str = "data/processed/scaled_sensor_train.csv"
    val_data_path: str = "data/processed/scaled_sensor_val.csv"
    test_data_path: str = "data/processed/scaled_sensor_test.csv"
    raw_test_data_path: str = "data/processed/sensor_test.csv"

    # Artifact paths
    model_save_path: str = "ml/models_store/isolation_forest.joblib"
    metadata_save_path: str = "ml/models_store/isolation_forest_metadata.json"
    predictions_save_path: str = "reports/phase2/isolation_forest/isolation_forest_predictions.csv"
    results_save_path: str = "reports/phase2/isolation_forest/isolation_forest_results.json"
    graphs_dir: str = "reports/phase2/isolation_forest/graphs"
    report_path: str = "reports/phase2/isolation_forest/isolation_forest_evaluation.md"
