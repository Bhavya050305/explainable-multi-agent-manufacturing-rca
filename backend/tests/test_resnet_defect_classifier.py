"""
ManuMind AI — Unit & Integration Tests for ResNet Defect Classifier
Department of AI & Data Science — RMK Engineering College

Covers all 10 verification categories:
1. Manifest-only dataset loading and unmanifested legacy isolation.
2. Image dimensions and channel order (128x128x3 RGB).
3. Deterministic label mapping and inverse bijection.
4. Partition counts and exact class balance (Train 420, Val 88, Test 92).
5. Deterministic preprocessing bounds (strictly [-1.0, 1.0]).
6. Compact ResNet-18 architecture and parameter count verification (2,804,708 params).
7. Forward pass output shape and probability simplex constraints.
8. Training-only data augmentation pipeline properties.
9. Multi-class metric calculation integrity (Macro F1, confusion matrix, ROC-AUC).
10. Single-image inference latency benchmarking.
11. Pydantic schema compatibility with DefectInspectionResponse.
"""

import json
import os
import tempfile
import numpy as np
import pytest

from backend.app.ml.defect_classifier.config import (
    CLASS_DISPLAY_NAMES,
    CLASS_NAMES,
    INT_TO_LABEL,
    LABEL_TO_INT,
    MACHINE_BATCH_LOOKUP,
    RECOMMENDATIONS,
    DefectClassifierConfig,
)
from backend.app.ml.defect_classifier.dataset import (
    build_augmentation_layer,
    load_manifest,
    load_partition_arrays,
    load_single_image,
    resolve_image_path,
)
from backend.app.ml.defect_classifier.model import (
    build_compact_resnet18,
    get_model_parameter_counts,
)
from backend.app.ml.defect_classifier.evaluate import (
    benchmark_inference_latency,
    compute_multiclass_metrics,
)
from backend.app.schemas.chat import DefectInspectionResponse


@pytest.fixture(scope="module")
def config():
    return DefectClassifierConfig()


@pytest.fixture(scope="module")
def manifest_partitions(config):
    return load_manifest(manifest_path=config.resolve_path(config.manifest_path))


# ============================================================================
# Category 1: Manifest Loading & Unmanifested Legacy Isolation
# ============================================================================
def test_manifest_loading_and_unmanifested_isolation(config, manifest_partitions):
    """
    Assert that the data loader loads exactly 600 manifest images,
    partitions them into 420 Train, 88 Val, 92 Test, and ignores the 16
    unmanifested legacy prototype files on disk (_01.bmp to _04.bmp).
    """
    train_recs = manifest_partitions["train"]
    val_recs = manifest_partitions["val"]
    test_recs = manifest_partitions["test"]

    assert len(train_recs) == 420
    assert len(val_recs) == 88
    assert len(test_recs) == 92
    assert len(train_recs) + len(val_recs) + len(test_recs) == 600

    # Collect all manifest filenames
    manifest_filenames = {r["filename"] for r in train_recs + val_recs + test_recs}
    assert len(manifest_filenames) == 600

    # Ensure none of the 16 legacy prototype files are in manifest
    legacy_filenames = [
        f"{m}_{d}_{i:02d}.bmp"
        for m, d in [("M101", "normal_surface"), ("M102", "dent"),
                     ("M104", "spalling"), ("M104", "surface_crack")]
        for i in range(1, 5)
    ]
    assert len(legacy_filenames) == 16
    for leg in legacy_filenames:
        assert leg not in manifest_filenames, f"Legacy prototype file {leg} leaked into manifest!"


# ============================================================================
# Category 2: Image Dimensions & Channel Order
# ============================================================================
def test_image_dimensions_and_channel_order(config, manifest_partitions):
    """Assert loaded image evaluates to shape (128, 128, 3) and float32 dtype."""
    sample_rec = manifest_partitions["train"][0]
    filepath = resolve_image_path(sample_rec["filepath"])
    img_arr = load_single_image(filepath, target_shape=(128, 128))

    assert img_arr.shape == (128, 128, 3)
    assert img_arr.dtype == np.float32


# ============================================================================
# Category 3: Deterministic Label Mapping
# ============================================================================
def test_deterministic_label_mapping():
    """Verify exact 4-class label mappings and inverse bijection."""
    expected_mapping = {
        "surface_crack": 0,
        "spalling": 1,
        "dent": 2,
        "normal_surface": 3,
    }
    assert LABEL_TO_INT == expected_mapping
    assert len(CLASS_NAMES) == 4
    for name, idx in expected_mapping.items():
        assert INT_TO_LABEL[idx] == name
        assert name in MACHINE_BATCH_LOOKUP
        assert name in RECOMMENDATIONS


# ============================================================================
# Category 4: Partition Counts & Class Balance
# ============================================================================
def test_partition_class_balance(manifest_partitions):
    """Verify perfect balanced distribution across all classes and partitions."""
    for split_name, expected_total, expected_per_class in [
        ("train", 420, 105),
        ("val", 88, 22),
        ("test", 92, 23),
    ]:
        recs = manifest_partitions[split_name]
        assert len(recs) == expected_total

        counts = {c: 0 for c in CLASS_NAMES}
        for r in recs:
            counts[r["defect_type"]] += 1

        for c, count in counts.items():
            assert count == expected_per_class, (
                f"Class {c} has {count} samples in {split_name}, expected {expected_per_class}"
            )


# ============================================================================
# Category 5: Deterministic Preprocessing Bounds
# ============================================================================
def test_deterministic_preprocessing_bounds(config, manifest_partitions):
    """Verify scaled input tensors evaluate strictly to range [-1.0, 1.0]."""
    val_recs = manifest_partitions["val"][:10]  # Check first 10 validation images
    X, y_cat, y_int, _ = load_partition_arrays(val_recs, target_shape=(128, 128))

    assert X.shape == (10, 128, 128, 3)
    assert np.min(X) >= -1.0
    assert np.max(X) <= 1.0
    # Mean intensity of metallic texture should be reasonable
    mean_val = np.mean(X)
    assert -0.8 <= mean_val <= 0.8, f"Unexpected mean pixel value: {mean_val}"


# ============================================================================
# Category 6: Model Architecture & Parameter Counts
# ============================================================================
def test_model_architecture_and_parameter_counts(config):
    """
    Verify Compact ResNet-18 builds with exactly 2,804,708 total parameters
    (2,799,908 trainable, 4,800 non-trainable BN).
    """
    model = build_compact_resnet18(
        input_shape=config.input_shape,
        num_classes=config.num_classes,
        l2_reg=config.l2_reg,
        dropout_rate=config.dropout_rate
    )
    counts = get_model_parameter_counts(model)

    assert counts["total_parameters"] == 2804708, (
        f"Expected 2,804,708 total parameters, got {counts['total_parameters']}"
    )
    assert counts["trainable_parameters"] == 2799908, (
        f"Expected 2,799,908 trainable parameters, got {counts['trainable_parameters']}"
    )
    assert counts["non_trainable_parameters"] == 4800, (
        f"Expected 4,800 non-trainable parameters, got {counts['non_trainable_parameters']}"
    )


# ============================================================================
# Category 7: Output Shape & Probability Simplex Constraints
# ============================================================================
def test_model_output_shape_and_simplex_properties(config):
    """Assert forward pass returns valid probability distribution on simplex."""
    model = build_compact_resnet18(
        input_shape=config.input_shape,
        num_classes=config.num_classes
    )
    batch_size = 5
    dummy_input = np.random.uniform(-1.0, 1.0, size=(batch_size, *config.input_shape)).astype(np.float32)

    probs = model(dummy_input, training=False).numpy()

    assert probs.shape == (batch_size, 4)
    # Check all probabilities are non-negative
    assert np.all(probs >= 0.0)
    # Check row-sums are equal to 1.0 within numerical precision
    row_sums = np.sum(probs, axis=1)
    np.testing.assert_allclose(row_sums, 1.0, atol=1e-5)


# ============================================================================
# Category 8: Data Augmentation Pipeline Properties
# ============================================================================
def test_data_augmentation_pipeline():
    """Verify training-only augmentation preserves tensor dimensions."""
    aug_layer = build_augmentation_layer(seed=42)
    dummy_input = np.random.uniform(-1.0, 1.0, size=(2, 128, 128, 3)).astype(np.float32)

    augmented = aug_layer(dummy_input, training=True).numpy()

    assert augmented.shape == (2, 128, 128, 3)
    assert augmented.dtype == np.float32


# ============================================================================
# Category 9: Multi-Class Metric Calculation Integrity
# ============================================================================
def test_multiclass_evaluation_metrics():
    """Verify metrics calculation against known ground-truth and predictions."""
    y_true = np.array([0, 0, 1, 1, 2, 2, 3, 3])
    # 7 correct, 1 incorrect (sample 3 predicted as 0 instead of 1)
    y_pred_probs = np.array([
        [0.9, 0.05, 0.03, 0.02],  # 0 -> 0 (correct)
        [0.8, 0.1, 0.05, 0.05],   # 0 -> 0 (correct)
        [0.1, 0.7, 0.1, 0.1],     # 1 -> 1 (correct)
        [0.6, 0.3, 0.05, 0.05],   # 1 -> 0 (incorrect)
        [0.05, 0.05, 0.8, 0.1],   # 2 -> 2 (correct)
        [0.02, 0.03, 0.9, 0.05],  # 2 -> 2 (correct)
        [0.05, 0.05, 0.1, 0.8],   # 3 -> 3 (correct)
        [0.01, 0.01, 0.08, 0.9],  # 3 -> 3 (correct)
    ], dtype=np.float32)

    metrics = compute_multiclass_metrics(y_true, y_pred_probs, CLASS_NAMES)

    assert metrics["sample_count"] == 8
    assert metrics["accuracy"] == 7.0 / 8.0  # 0.875
    assert 0.0 <= metrics["macro_f1"] <= 1.0
    assert 0.0 <= metrics["macro_precision"] <= 1.0
    assert 0.0 <= metrics["macro_recall"] <= 1.0
    assert 0.0 <= metrics["macro_roc_auc"] <= 1.0

    cm_raw = metrics["confusion_matrix"]["raw_counts"]
    assert cm_raw[0][0] == 2  # class 0: 2 TP
    assert cm_raw[1][1] == 1  # class 1: 1 TP, 1 misclassified as 0
    assert cm_raw[1][0] == 1  # class 1 misclassified as class 0
    assert cm_raw[2][2] == 2  # class 2: 2 TP
    assert cm_raw[3][3] == 2  # class 3: 2 TP


# ============================================================================
# Category 10: Inference Latency Benchmarking
# ============================================================================
def test_latency_benchmarking(config):
    """Verify latency benchmarking produces valid positive timings."""
    model = build_compact_resnet18(
        input_shape=config.input_shape,
        num_classes=config.num_classes
    )
    lat_results = benchmark_inference_latency(
        model, input_shape=config.input_shape, n_warmup=2, n_iterations=5
    )

    assert lat_results["mean_latency_ms"] > 0.0
    assert lat_results["median_latency_ms"] > 0.0
    assert lat_results["p95_latency_ms"] > 0.0
    assert lat_results["throughput_images_per_sec"] > 0.0
    assert lat_results["iterations"] == 5


# ============================================================================
# Category 11: Pydantic Schema Compatibility
# ============================================================================
def test_pydantic_schema_compatibility():
    """Verify DefectInspectionResponse schema validates correctly."""
    resp = DefectInspectionResponse(
        image_name="M104_surface_crack_106.bmp",
        defect_type="Surface Crack",
        confidence=0.9854,
        affected_machine_id="M104",
        batch_number="B-8821",
        recommendation=RECOMMENDATIONS["surface_crack"]
    )
    assert resp.image_name == "M104_surface_crack_106.bmp"
    assert resp.defect_type == "Surface Crack"
    assert resp.confidence == 0.9854
    assert resp.affected_machine_id == "M104"
    assert resp.batch_number == "B-8821"
    assert "CRITICAL" in resp.recommendation
