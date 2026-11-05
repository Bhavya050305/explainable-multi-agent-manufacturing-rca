"""
ManuMind AI — LSTM Autoencoder Training Pipeline
Department of AI & Data Science — RMK Engineering College

Strict Rules:
1. Fit model ONLY on verified normal training sequences (N = 2,700).
2. Exclude all 80 anomalous training sequences.
3. Use validation data (normal sequences) for EarlyStopping.
4. Calibrate anomaly threshold exclusively on validation partition.
5. Never touch or observe test data during training or threshold selection.
6. Set fixed seeds for deterministic reproducibility.
"""

import json
import logging
import os
import random
import sys
from typing import Dict, Any, Tuple

import numpy as np
import tensorflow as tf
from sklearn.metrics import (
    precision_recall_curve,
    f1_score,
    precision_score,
    recall_score,
    accuracy_score,
    confusion_matrix
)

# Ensure project root is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app.ml.lstm_autoencoder.config import LSTMAutoencoderConfig
from backend.app.ml.lstm_autoencoder.model import build_lstm_autoencoder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("LSTMAutoencoderTrain")


def set_seed(seed: int = 42) -> None:
    """Sets global random seeds for deterministic execution across libraries."""
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)
    logger.info("Deterministic random seed set to %d across Python, NumPy, and TensorFlow.", seed)


def train_lstm_autoencoder(
    config: LSTMAutoencoderConfig = None
) -> Tuple[tf.keras.Model, float, Dict[str, Any]]:
    """
    Trains LSTM Autoencoder on healthy sequences and calibrates anomaly threshold on validation set.
    """
    if config is None:
        config = LSTMAutoencoderConfig()

    set_seed(config.random_seed)
    logger.info("Initializing LSTM Autoencoder training pipeline.")
    os.makedirs(os.path.dirname(config.model_save_path), exist_ok=True)

    # 1. Load Training Sequences
    if not os.path.exists(config.train_sequences_path):
        raise FileNotFoundError(f"Training sequences not found at: {config.train_sequences_path}")

    train_data = np.load(config.train_sequences_path)
    X_train_all = train_data["X"]
    y_train_all = train_data["is_anomaly"]

    logger.info(
        "Loaded training sequences: %s, total=%d (normal=%d, anomalous=%d)",
        X_train_all.shape, len(X_train_all), (y_train_all == 0).sum(), (y_train_all == 1).sum()
    )

    # 2. Strict Filter: Train ONLY on verified normal sequences
    normal_train_mask = (y_train_all == 0)
    X_train_normal = X_train_all[normal_train_mask]
    num_normal_train = len(X_train_normal)
    num_anomalies_excluded = len(X_train_all) - num_normal_train

    if num_normal_train != 2700:
        logger.warning("Expected 2,700 normal training sequences, found %d.", num_normal_train)

    logger.info(
        "Strict Normal Filter: %d normal training sequences retained for fitting (100.0%% normal baseline). "
        "Excluded %d anomalous sequences.",
        num_normal_train, num_anomalies_excluded
    )

    # 3. Load Validation Sequences
    if not os.path.exists(config.val_sequences_path):
        raise FileNotFoundError(f"Validation sequences not found at: {config.val_sequences_path}")

    val_data = np.load(config.val_sequences_path)
    X_val_all = val_data["X"]
    y_val_all = val_data["is_anomaly"]

    # For validation loss monitoring during training, monitor normal validation sequences
    normal_val_mask = (y_val_all == 0)
    X_val_normal = X_val_all[normal_val_mask]
    logger.info("Validation split: %d total (normal=%d, anomalous=%d).", len(X_val_all), len(X_val_normal), (y_val_all == 1).sum())

    # 4. Build Model
    input_shape = (config.window_size, config.n_features)
    model = build_lstm_autoencoder(
        input_shape=input_shape,
        encoder_units=config.encoder_units,
        decoder_units=config.decoder_units,
        learning_rate=config.learning_rate
    )
    logger.info("Built LSTM Autoencoder model architecture:\n%s", model.summary(print_fn=lambda x: None))

    # 5. Callbacks: EarlyStopping and ModelCheckpoint
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=config.patience,
            restore_best_weights=True,
            mode="min",
            verbose=1
        ),
        tf.keras.callbacks.ModelCheckpoint(
            filepath=config.model_save_path,
            monitor="val_loss",
            save_best_only=True,
            mode="min",
            verbose=1
        )
    ]

    # 6. Fit Autoencoder (X_train_normal -> X_train_normal)
    logger.info(
        "Starting model training for up to %d epochs (batch_size=%d, patience=%d)...",
        config.epochs, config.batch_size, config.patience
    )

    history = model.fit(
        X_train_normal,
        X_train_normal,
        epochs=config.epochs,
        batch_size=config.batch_size,
        validation_data=(X_val_normal, X_val_normal),
        callbacks=callbacks,
        shuffle=True,
        verbose=1
    )

    epochs_trained = len(history.history["loss"])
    final_train_loss = float(history.history["loss"][-1])
    best_val_loss = float(min(history.history["val_loss"]))
    logger.info(
        "Training finished after %d epochs. Final train loss: %.6f, Best val loss: %.6f",
        epochs_trained, final_train_loss, best_val_loss
    )

    # 7. Validation Threshold Calibration
    # A. Reconstruction errors on normal validation sequences
    X_val_norm_recon = model.predict(X_val_normal, batch_size=config.batch_size, verbose=0)
    val_errors_normal = np.mean(np.square(X_val_normal - X_val_norm_recon), axis=(1, 2))

    # B. Initial threshold: 99th percentile of normal validation reconstruction errors
    threshold_p99 = float(np.percentile(val_errors_normal, 99.0))
    threshold_p95 = float(np.percentile(val_errors_normal, 95.0))
    threshold_mean_3std = float(np.mean(val_errors_normal) + 3.0 * np.std(val_errors_normal))

    # C. Full validation set reconstruction errors
    X_val_all_recon = model.predict(X_val_all, batch_size=config.batch_size, verbose=0)
    val_errors_all = np.mean(np.square(X_val_all - X_val_all_recon), axis=(1, 2))

    # Evaluate 99th percentile threshold
    y_pred_val_p99 = (val_errors_all > threshold_p99).astype(int)
    cm_p99 = confusion_matrix(y_val_all, y_pred_val_p99)
    tn_p99, fp_p99, fn_p99, tp_p99 = [int(v) for v in cm_p99.ravel()]
    prec_p99 = float(precision_score(y_val_all, y_pred_val_p99, zero_division=0))
    rec_p99 = float(recall_score(y_val_all, y_pred_val_p99, zero_division=0))
    f1_p99 = float(f1_score(y_val_all, y_pred_val_p99, zero_division=0))
    acc_p99 = float(accuracy_score(y_val_all, y_pred_val_p99))
    spec_p99 = float(tn_p99 / (tn_p99 + fp_p99))
    fpr_p99 = float(fp_p99 / (tn_p99 + fp_p99))

    # D. Sweep threshold on validation PR curve to inspect maximum F1
    precisions, recalls, thresholds = precision_recall_curve(y_val_all, val_errors_all)
    f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-10)
    best_idx = int(np.argmax(f1_scores))
    threshold_best_f1 = float(thresholds[best_idx])
    best_val_f1 = float(f1_scores[best_idx])

    # Select threshold: Use 99th percentile as primary industrial standard, or best-F1 if justified
    # We adopt the 99th percentile threshold (threshold_p99) which guarantees <= 1% false alarms on baseline normal data
    selected_threshold = threshold_p99

    logger.info("Validation Threshold Calibration:")
    logger.info("  99th Percentile Normal Threshold: %.6f -> F1=%.4f, Prec=%.4f, Rec=%.4f, Spec=%.4f, FPR=%.4f",
                threshold_p99, f1_p99, prec_p99, rec_p99, spec_p99, fpr_p99)
    logger.info("  Max F1 Validation Threshold:      %.6f -> F1=%.4f", threshold_best_f1, best_val_f1)
    logger.info("  Selected Threshold for Inference:  %.6f", selected_threshold)

    # 8. Save Model Metadata
    metadata = {
        "model_type": "LSTMAutoencoder",
        "framework": "tensorflow.keras",
        "input_shape": list(input_shape),
        "architecture": {
            "encoder": config.encoder_units,
            "decoder": config.decoder_units,
            "latent_dim": config.encoder_units[-1]
        },
        "training_details": {
            "epochs_trained": epochs_trained,
            "batch_size": config.batch_size,
            "learning_rate": config.learning_rate,
            "normal_train_sequences": num_normal_train,
            "anomalies_excluded": num_anomalies_excluded,
            "final_train_loss": round(final_train_loss, 6),
            "best_val_loss": round(best_val_loss, 6),
            "random_seed": config.random_seed
        },
        "reconstruction_error_metric": "MSE = mean((X - X_pred)^2, axis=(1, 2))",
        "threshold_calibration": {
            "method": "99th percentile of normal validation reconstruction error",
            "selected_threshold": round(selected_threshold, 6),
            "threshold_p99_normal_val": round(threshold_p99, 6),
            "threshold_p95_normal_val": round(threshold_p95, 6),
            "threshold_mean_plus_3std": round(threshold_mean_3std, 6),
            "threshold_max_val_f1": round(threshold_best_f1, 6),
            "validation_performance_at_selected_threshold": {
                "accuracy": round(acc_p99, 4),
                "precision": round(prec_p99, 4),
                "recall": round(rec_p99, 4),
                "f1_score": round(f1_p99, 4),
                "specificity": round(spec_p99, 4),
                "false_positive_rate": round(fpr_p99, 4),
                "confusion_matrix": {
                    "tn": tn_p99,
                    "fp": fp_p99,
                    "fn": fn_p99,
                    "tp": tp_p99
                }
            }
        },
        "history": {
            "loss": [float(x) for x in history.history["loss"]],
            "val_loss": [float(x) for x in history.history["val_loss"]],
            "mae": [float(x) for x in history.history.get("mae", [])],
            "val_mae": [float(x) for x in history.history.get("val_mae", [])]
        }
    }

    with open(config.metadata_save_path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info("Saved LSTM Autoencoder metadata to: %s", config.metadata_save_path)

    return model, selected_threshold, metadata


if __name__ == "__main__":
    train_lstm_autoencoder()
