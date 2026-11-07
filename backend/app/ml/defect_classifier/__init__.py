"""
ManuMind AI — ResNet Vision Defect Classifier Package
Department of AI & Data Science — RMK Engineering College

Public API exports for Phase 2 Step 7: Manufacturing Defect Image Classification.
"""

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
    create_tf_dataset,
    load_manifest,
    load_partition_arrays,
    load_single_image,
)
from backend.app.ml.defect_classifier.model import (
    build_compact_resnet18,
    build_standard_resnet18,
    get_model_parameter_counts,
)
from backend.app.ml.defect_classifier.train import (
    set_determinism,
    train_defect_classifier,
)
from backend.app.ml.defect_classifier.evaluate import (
    benchmark_inference_latency,
    compute_multiclass_metrics,
    evaluate_model_pipeline,
)
from backend.app.ml.defect_classifier.visualize import (
    generate_all_visualizations,
    plot_confusion_matrix,
    plot_roc_curves,
    plot_sample_predictions_grid,
    plot_training_curves,
)
from backend.app.ml.defect_classifier.predict import (
    DefectClassifierInferenceService,
)

__all__ = [
    "CLASS_NAMES",
    "LABEL_TO_INT",
    "INT_TO_LABEL",
    "CLASS_DISPLAY_NAMES",
    "MACHINE_BATCH_LOOKUP",
    "RECOMMENDATIONS",
    "DefectClassifierConfig",
    "load_manifest",
    "load_single_image",
    "load_partition_arrays",
    "build_augmentation_layer",
    "create_tf_dataset",
    "build_compact_resnet18",
    "build_standard_resnet18",
    "get_model_parameter_counts",
    "set_determinism",
    "train_defect_classifier",
    "compute_multiclass_metrics",
    "benchmark_inference_latency",
    "evaluate_model_pipeline",
    "plot_training_curves",
    "plot_confusion_matrix",
    "plot_roc_curves",
    "plot_sample_predictions_grid",
    "generate_all_visualizations",
    "DefectClassifierInferenceService",
]
