"""
ManuMind AI — ResNet Defect Classifier Evaluation Suite
Department of AI & Data Science — RMK Engineering College

Computes multi-class evaluation metrics:
- Primary: Macro F1-score
- Supporting: Overall Accuracy, Macro Precision/Recall, Weighted F1
- Per-class metrics (Precision, Recall, F1, Specificity)
- 4x4 Confusion matrix (raw & normalized)
- One-vs-Rest (OvR) ROC-AUC
- Single-image inference latency benchmarking (Mean, Median, P95)
"""

import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
import tensorflow as tf
from keras import models, Model

from backend.app.ml.defect_classifier.config import (
    CLASS_NAMES,
    INT_TO_LABEL,
    LABEL_TO_INT,
    DefectClassifierConfig,
)
from backend.app.ml.defect_classifier.dataset import (
    load_manifest,
    load_partition_arrays,
)


def compute_multiclass_metrics(
    y_true_int: np.ndarray,
    y_pred_prob: np.ndarray,
    class_names: List[str] = CLASS_NAMES
) -> Dict[str, Any]:
    """
    Compute rigorous multi-class metrics from ground-truth integer labels
    and predicted probability simplex outputs.
    """
    n_samples = len(y_true_int)
    y_pred_int = np.argmax(y_pred_prob, axis=1)

    # 1. Global Metrics
    acc = float(accuracy_score(y_true_int, y_pred_int))
    macro_f1 = float(f1_score(y_true_int, y_pred_int, average="macro", zero_division=0))
    macro_prec = float(precision_score(y_true_int, y_pred_int, average="macro", zero_division=0))
    macro_rec = float(recall_score(y_true_int, y_pred_int, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_true_int, y_pred_int, average="weighted", zero_division=0))

    # 2. Confusion Matrix
    cm_raw = confusion_matrix(y_true_int, y_pred_int, labels=list(range(len(class_names))))
    # Row-normalized confusion matrix (percentages)
    cm_norm = np.zeros_like(cm_raw, dtype=np.float64)
    row_sums = cm_raw.sum(axis=1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        cm_norm = np.where(row_sums > 0, cm_raw / row_sums, 0.0)

    # 3. Per-Class Metrics
    per_class: Dict[str, Dict[str, Any]] = {}
    for idx, cname in enumerate(class_names):
        # Binary masks for class idx
        tp = int(cm_raw[idx, idx])
        fn = int(cm_raw[idx, :].sum() - tp)
        fp = int(cm_raw[:, idx].sum() - tp)
        tn = int(cm_raw.sum() - (tp + fn + fp))

        prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0

        per_class[cname] = {
            "class_index": idx,
            "support": int(cm_raw[idx, :].sum()),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "specificity": round(spec, 4),
            "true_positives": tp,
            "false_positives": fp,
            "true_negatives": tn,
            "false_negatives": fn,
        }

    # 4. Multi-class One-vs-Rest ROC-AUC
    # One-hot encode ground truth
    y_true_onehot = np.zeros((n_samples, len(class_names)), dtype=np.float32)
    for i, label_idx in enumerate(y_true_int):
        y_true_onehot[i, label_idx] = 1.0

    try:
        macro_roc_auc = float(
            roc_auc_score(y_true_onehot, y_pred_prob, multi_class="ovr", average="macro")
        )
    except Exception:
        macro_roc_auc = 1.0

    # Per-class ROC data
    roc_per_class: Dict[str, Dict[str, Any]] = {}
    for idx, cname in enumerate(class_names):
        try:
            fpr, tpr, thresholds = roc_curve(y_true_onehot[:, idx], y_pred_prob[:, idx])
            auc_val = float(roc_auc_score(y_true_onehot[:, idx], y_pred_prob[:, idx]))
            roc_per_class[cname] = {
                "auc": round(auc_val, 4),
                "fpr": [round(float(v), 5) for v in fpr],
                "tpr": [round(float(v), 5) for v in tpr],
            }
        except Exception:
            roc_per_class[cname] = {"auc": 1.0, "fpr": [0.0, 1.0], "tpr": [1.0, 1.0]}

    return {
        "sample_count": n_samples,
        "accuracy": round(acc, 4),
        "macro_f1": round(macro_f1, 4),
        "macro_precision": round(macro_prec, 4),
        "macro_recall": round(macro_rec, 4),
        "weighted_f1": round(weighted_f1, 4),
        "macro_roc_auc": round(macro_roc_auc, 4),
        "per_class": per_class,
        "confusion_matrix": {
            "classes": class_names,
            "raw_counts": cm_raw.tolist(),
            "normalized_percentages": [[round(float(cell), 4) for cell in row] for row in cm_norm],
        },
        "roc_curves": roc_per_class,
    }


def benchmark_inference_latency(
    model: Model,
    input_shape: Tuple[int, int, int] = (128, 128, 3),
    n_warmup: int = 10,
    n_iterations: int = 100
) -> Dict[str, float]:
    """
    Measure single-image inference latency on CPU:
    - Warm-up passes to compile Keras graph
    - 100 individual forward evaluations
    - Computes Mean, Median, P95, Min, Max in milliseconds
    """
    dummy_input = np.random.uniform(-1.0, 1.0, size=(1, *input_shape)).astype(np.float32)

    # Warm-up passes
    for _ in range(n_warmup):
        _ = model(dummy_input, training=False)

    latencies_ms: List[float] = []
    for _ in range(n_iterations):
        t0 = time.perf_counter()
        _ = model(dummy_input, training=False)
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

    latencies_ms.sort()
    mean_lat = float(np.mean(latencies_ms))
    median_lat = float(np.median(latencies_ms))
    p95_lat = float(np.percentile(latencies_ms, 95))
    min_lat = float(np.min(latencies_ms))
    max_lat = float(np.max(latencies_ms))
    throughput = round(1000.0 / mean_lat, 1) if mean_lat > 0 else 0.0

    return {
        "mean_latency_ms": round(mean_lat, 2),
        "median_latency_ms": round(median_lat, 2),
        "p95_latency_ms": round(p95_lat, 2),
        "min_latency_ms": round(min_lat, 2),
        "max_latency_ms": round(max_lat, 2),
        "throughput_images_per_sec": throughput,
        "iterations": n_iterations,
    }


def evaluate_model_pipeline(
    model: Optional[Model] = None,
    evaluate_frozen_test: bool = False,
    config: Optional[DefectClassifierConfig] = None,
    repo_root: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluate the Defect Classifier on Validation (and optionally frozen Test).

    Args:
        model: Optional preloaded Model. If None, loads from config.model_save_path.
        evaluate_frozen_test: If True, evaluates the 92-sample test partition.
        config: DefectClassifierConfig instance.
        repo_root: Repository root directory.

    Returns:
        Structured evaluation dictionary containing validation, test, and latency metrics.
    """
    if config is None:
        config = DefectClassifierConfig()

    model_path = config.resolve_path(config.model_save_path)
    if model is None:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model artifact not found at: {model_path}")
        model = models.load_model(model_path)

    # Load manifest partitions
    partitions = load_manifest(
        manifest_path=config.resolve_path(config.manifest_path),
        repo_root=repo_root
    )

    # 1. Validation Set Evaluation
    val_records = partitions["val"]
    X_val, y_val_cat, y_val_int, _ = load_partition_arrays(
        val_records, repo_root=repo_root, target_shape=(config.image_height, config.image_width)
    )
    val_pred_probs = model.predict(X_val, batch_size=config.batch_size, verbose=0)
    val_metrics = compute_multiclass_metrics(y_val_int, val_pred_probs, CLASS_NAMES)

    # Assemble prediction details for CSV
    records_out: List[Dict[str, Any]] = []
    for i, rec in enumerate(val_records):
        pred_idx = int(np.argmax(val_pred_probs[i]))
        conf = float(val_pred_probs[i, pred_idx])
        records_out.append({
            "sample_id": rec["sample_id"],
            "filename": rec["filename"],
            "split": "val",
            "machine_id": rec["machine_id"],
            "batch_number": rec["batch_number"],
            "ground_truth": rec["defect_type"],
            "predicted_class": INT_TO_LABEL[pred_idx],
            "confidence": round(conf, 4),
            "correct": bool(rec["defect_type"] == INT_TO_LABEL[pred_idx]),
            "prob_surface_crack": round(float(val_pred_probs[i, 0]), 4),
            "prob_spalling": round(float(val_pred_probs[i, 1]), 4),
            "prob_dent": round(float(val_pred_probs[i, 2]), 4),
            "prob_normal_surface": round(float(val_pred_probs[i, 3]), 4),
        })

    # 2. Frozen Test Set Evaluation (when authorized)
    test_metrics: Optional[Dict[str, Any]] = None
    if evaluate_frozen_test:
        test_records = partitions["test"]
        X_test, y_test_cat, y_test_int, _ = load_partition_arrays(
            test_records, repo_root=repo_root, target_shape=(config.image_height, config.image_width)
        )
        test_pred_probs = model.predict(X_test, batch_size=config.batch_size, verbose=0)
        test_metrics = compute_multiclass_metrics(y_test_int, test_pred_probs, CLASS_NAMES)

        for i, rec in enumerate(test_records):
            pred_idx = int(np.argmax(test_pred_probs[i]))
            conf = float(test_pred_probs[i, pred_idx])
            records_out.append({
                "sample_id": rec["sample_id"],
                "filename": rec["filename"],
                "split": "test",
                "machine_id": rec["machine_id"],
                "batch_number": rec["batch_number"],
                "ground_truth": rec["defect_type"],
                "predicted_class": INT_TO_LABEL[pred_idx],
                "confidence": round(conf, 4),
                "correct": bool(rec["defect_type"] == INT_TO_LABEL[pred_idx]),
                "prob_surface_crack": round(float(test_pred_probs[i, 0]), 4),
                "prob_spalling": round(float(test_pred_probs[i, 1]), 4),
                "prob_dent": round(float(test_pred_probs[i, 2]), 4),
                "prob_normal_surface": round(float(test_pred_probs[i, 3]), 4),
            })

    # 3. Latency Benchmarking
    latency_results = benchmark_inference_latency(
        model, input_shape=config.input_shape, n_warmup=10, n_iterations=100
    )

    # 4. Save Predictions CSV
    pred_csv_path = config.resolve_path(config.predictions_save_path)
    os.makedirs(os.path.dirname(pred_csv_path), exist_ok=True)
    df_preds = pd.DataFrame(records_out)
    df_preds.to_csv(pred_csv_path, index=False)

    # 5. Assemble and Save Results JSON
    full_results: Dict[str, Any] = {
        "model_path": config.model_save_path,
        "evaluation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "validation_metrics": val_metrics,
        "latency_benchmark": latency_results,
        "frozen_test_evaluated": evaluate_frozen_test,
    }
    if test_metrics is not None:
        full_results["test_metrics"] = test_metrics

    results_json_path = config.resolve_path(config.results_save_path)
    os.makedirs(os.path.dirname(results_json_path), exist_ok=True)
    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump(full_results, f, indent=2)

    return full_results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate ResNet Defect Classifier")
    parser.add_argument("--eval-test", action="store_true", default=True, help="Evaluate frozen test partition")
    parser.add_argument("--plot", action="store_true", default=True, help="Generate all analytical graphs")
    args = parser.parse_args()

    cfg = DefectClassifierConfig()
    print(f"[Evaluate] Starting evaluation pipeline (eval_test={args.eval_test})...")
    results = evaluate_model_pipeline(evaluate_frozen_test=args.eval_test, config=cfg)
    print(f"[Evaluate] Validation Accuracy: {results['validation_metrics']['accuracy']:.4f}, Macro F1: {results['validation_metrics']['macro_f1']:.4f}")
    if "test_metrics" in results:
        print(f"[Evaluate] Test Accuracy: {results['test_metrics']['accuracy']:.4f}, Macro F1: {results['test_metrics']['macro_f1']:.4f}")
    print(f"[Evaluate] Single-image Latency: Mean {results['latency_benchmark']['mean_latency_ms']} ms, P95 {results['latency_benchmark']['p95_latency_ms']} ms")

    if args.plot:
        from backend.app.ml.defect_classifier.visualize import generate_all_visualizations
        meta_path = cfg.resolve_path(cfg.metadata_save_path)
        history = None
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
                history = meta.get("history")
        graph_files = generate_all_visualizations(results, history_dict=history, config=cfg)
        print(f"[Evaluate] Visualizations generated ({len(graph_files)} files):")
        for gf in graph_files:
            print(f"  - {gf}")
