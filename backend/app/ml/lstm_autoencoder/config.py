"""
ManuMind AI — LSTM Autoencoder Configuration
Department of AI & Data Science — RMK Engineering College
"""

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class LSTMAutoencoderConfig:
    """Hyperparameters, dataset paths, and output destinations for LSTM Autoencoder."""

    # Time-series sequence specifications
    window_size: int = 30
    n_features: int = 5
    feature_cols: List[str] = field(
        default_factory=lambda: ["vibration", "temperature", "pressure", "current", "rpm"]
    )

    # Architecture & Training Hyperparameters
    encoder_units: List[int] = field(default_factory=lambda: [64, 32])
    decoder_units: List[int] = field(default_factory=lambda: [32, 64])
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 50
    patience: int = 8
    random_seed: int = 42

    # Sequence Data Paths
    train_sequences_path: str = "data/processed/sequences_train.npz"
    val_sequences_path: str = "data/processed/sequences_val.npz"
    test_sequences_path: str = "data/processed/sequences_test.npz"
    metadata_csv_path: str = "data/processed/clean_sensor_windows.csv"
    scaler_path: str = "ml/models_store/sensor_scaler.joblib"

    # Artifact Storage Destinations
    model_save_path: str = "ml/models_store/lstm_autoencoder.keras"
    metadata_save_path: str = "ml/models_store/lstm_autoencoder_metadata.json"
    predictions_save_path: str = "reports/phase2/lstm_autoencoder/lstm_predictions.csv"
    results_save_path: str = "reports/phase2/lstm_autoencoder/lstm_autoencoder_results.json"
    report_path: str = "reports/phase2/lstm_autoencoder/lstm_autoencoder_evaluation.md"
    graphs_dir: str = "reports/phase2/lstm_autoencoder/graphs"
