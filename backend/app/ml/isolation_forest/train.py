"""
ManuMind AI — Isolation Forest Training Pipeline
Department of AI & Data Science — RMK Engineering College

Strict Requirements:
1. Fit exclusively on verified healthy training readings (is_anomaly == 0).
2. Never include anomalous training samples during model fitting.
3. Use existing StandardScaler fitted only on training data.
4. Calibrate anomaly threshold exclusively on validation partition.
5. Keep the test set completely untouched until final evaluation.
6. Fixed random seed (42) for deterministic reproducibility.
"""

import json
import logging
import os
import sys
from typing import Dict, Any, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_recall_curve, roc_auc_score, average_precision_score

# Ensure project root is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app.ml.isolation_forest.config import IsolationForestConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("IsolationForestTrain")


def train_isolation_forest(
    config: IsolationForestConfig = None
) -> Tuple[IsolationForest, float, Dict[str, Any]]:
    """
    Trains Isolation Forest on healthy manufacturing telemetry and calibrates threshold on validation data.
    """
    if config is None:
        config = IsolationForestConfig()

    logger.info("Initializing Isolation Forest training pipeline.")
    os.makedirs(os.path.dirname(config.model_save_path), exist_ok=True)

    # 1. Load Training Data
    if not os.path.exists(config.train_data_path):
        raise FileNotFoundError(f"Training data not found at: {config.train_data_path}")

    train_df = pd.read_csv(config.train_data_path)
    logger.info("Loaded training data: %d rows across columns: %s", len(train_df), list(train_df.columns))

    # 2. Filter STRICTLY for healthy operational readings (is_anomaly == 0)
    healthy_train_df = train_df[train_df["is_anomaly"] == 0].reset_index(drop=True)
    num_healthy = len(healthy_train_df)
    num_anomalies_excluded = len(train_df) - num_healthy

    logger.info(
        "Strict Health Filter: %d healthy training rows retained (100.0%% normal baseline). "
        "Excluded %d early-onset anomaly readings from fitting.",
        num_healthy, num_anomalies_excluded
    )

    X_train_healthy = healthy_train_df[config.feature_cols].values.astype(np.float32)

    # 3. Initialize and fit IsolationForest
    # Note: contamination='auto' fits the baseline distribution
    # In scikit-learn, decision_function returns negative values for outliers and positive for inliers.
    # We define anomaly_score = -decision_function(X) so that HIGHER SCORE = MORE ANOMALOUS.
    model = IsolationForest(
        n_estimators=config.n_estimators,
        max_samples=config.max_samples,
        contamination=config.contamination,
        random_state=config.random_state,
        n_jobs=config.n_jobs
    )

    logger.info(
        "Fitting IsolationForest(n_estimators=%d, max_samples=%s, contamination=%s, random_state=%d)...",
        config.n_estimators, config.max_samples, config.contamination, config.random_state
    )
    model.fit(X_train_healthy)
    logger.info("Isolation Forest fitted successfully on %d healthy samples.", len(X_train_healthy))

    # 4. Calibrate Decision Threshold on Validation Partition
    if not os.path.exists(config.val_data_path):
        raise FileNotFoundError(f"Validation data not found at: {config.val_data_path}")

    val_df = pd.read_csv(config.val_data_path)
    X_val = val_df[config.feature_cols].values.astype(np.float32)
    y_val = val_df["is_anomaly"].values.astype(int)

    # Calculate anomaly scores on validation data: -decision_function
    val_raw_scores = -model.decision_function(X_val)

    # Calculate validation ranking metrics
    val_roc_auc = float(roc_auc_score(y_val, val_raw_scores))
    val_pr_auc = float(average_precision_score(y_val, val_raw_scores))

    logger.info("Validation Ranking Metrics: ROC-AUC=%.4f, PR-AUC=%.4f", val_roc_auc, val_pr_auc)

    # Sweep thresholds on validation PR curve to select optimal F1 threshold
    precisions, recalls, thresholds = precision_recall_curve(y_val, val_raw_scores)
    f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-10)
    best_idx = int(np.argmax(f1_scores))
    calibrated_threshold = float(thresholds[best_idx])
    best_val_f1 = float(f1_scores[best_idx])
    best_val_precision = float(precisions[best_idx])
    best_val_recall = float(recalls[best_idx])

    # Also evaluate default zero threshold (corresponding to decision_function < 0)
    default_pred = (val_raw_scores > 0.0).astype(int)
    from sklearn.metrics import f1_score as calc_f1, precision_score as calc_prec, recall_score as calc_rec
    default_f1 = float(calc_f1(y_val, default_pred))
    default_prec = float(calc_prec(y_val, default_pred))
    default_rec = float(calc_rec(y_val, default_pred))

    logger.info(
        "Validation Threshold Calibration: Selected threshold=%.4f (F1=%.4f, Prec=%.4f, Rec=%.4f) "
        "vs Default zero threshold (F1=%.4f, Prec=%.4f, Rec=%.4f)",
        calibrated_threshold, best_val_f1, best_val_precision, best_val_recall,
        default_f1, default_prec, default_rec
    )

    # 5. Save Trained Model Artifact
    joblib.dump(model, config.model_save_path)
    logger.info("Saved trained IsolationForest model to: %s", config.model_save_path)

    # 6. Save Metadata & Calibration Records
    metadata = {
        "model_type": "IsolationForest",
        "implementation": "scikit-learn",
        "features": config.feature_cols,
        "n_features": len(config.feature_cols),
        "hyperparameters": {
            "n_estimators": config.n_estimators,
            "max_samples": config.max_samples,
            "contamination": config.contamination,
            "random_state": config.random_state
        },
        "training_data_summary": {
            "source_file": config.train_data_path,
            "total_rows_available": len(train_df),
            "healthy_rows_used_for_fitting": num_healthy,
            "anomalous_rows_strictly_excluded": num_anomalies_excluded,
            "filtering_condition": "is_anomaly == 0"
        },
        "score_definition": {
            "formula": "anomaly_score = -decision_function(X)",
            "interpretation": "Higher score indicates higher anomaly likelihood / deviation from healthy baseline."
        },
        "validation_calibration": {
            "val_source_file": config.val_data_path,
            "val_sample_count": len(val_df),
            "val_normal_count": int((y_val == 0).sum()),
            "val_anomaly_count": int((y_val == 1).sum()),
            "val_roc_auc": round(val_roc_auc, 4),
            "val_pr_auc": round(val_pr_auc, 4),
            "calibrated_threshold": round(calibrated_threshold, 4),
            "calibrated_val_f1": round(best_val_f1, 4),
            "calibrated_val_precision": round(best_val_precision, 4),
            "calibrated_val_recall": round(best_val_recall, 4),
            "default_zero_threshold_f1": round(default_f1, 4),
            "default_zero_threshold_precision": round(default_prec, 4),
            "default_zero_threshold_recall": round(default_rec, 4),
            "rationale": (
                "Calibrated threshold was chosen on the validation partition to optimize F1-score "
                "and balance industrial false positive rate (precision) against defect escape (recall). "
                "Test data was strictly isolated and not observed."
            )
        }
    }

    with open(config.metadata_save_path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info("Saved model metadata to: %s", config.metadata_save_path)

    return model, calibrated_threshold, metadata


if __name__ == "__main__":
    train_isolation_forest()
