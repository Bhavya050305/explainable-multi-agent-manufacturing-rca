"""
ManuMind AI — ResNet Vision Defect Classifier Configuration
Department of AI & Data Science — RMK Engineering College

Centralized configuration, label mappings, and directory paths for
Phase 2 Step 7: Manufacturing Defect Image Classification.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# Canonical class names and mappings
CLASS_NAMES: List[str] = ["surface_crack", "spalling", "dent", "normal_surface"]

LABEL_TO_INT: Dict[str, int] = {
    "surface_crack": 0,
    "spalling": 1,
    "dent": 2,
    "normal_surface": 3,
}

INT_TO_LABEL: Dict[int, str] = {v: k for k, v in LABEL_TO_INT.items()}

# Display / Human-readable titles
CLASS_DISPLAY_NAMES: Dict[str, str] = {
    "surface_crack": "Surface Crack",
    "spalling": "Spalling",
    "dent": "Dent",
    "normal_surface": "Normal Surface",
}

# Confounded machine and batch associations established by data generator
MACHINE_BATCH_LOOKUP: Dict[str, Dict[str, str]] = {
    "surface_crack": {
        "machine_id": "M104",
        "batch_number": "B-8821",
        "description": "Spindle bearing raceway crack candidate",
    },
    "spalling": {
        "machine_id": "M104",
        "batch_number": "B-8821",
        "description": "Bearing roller fatigue spalling",
    },
    "dent": {
        "machine_id": "M102",
        "batch_number": "B-7740",
        "description": "Die impact indentation dent",
    },
    "normal_surface": {
        "machine_id": "M101",
        "batch_number": "B-9910",
        "description": "Nominal workpiece surface finish",
    },
}

# Recommended operational responses for manufacturing supervisory agents
RECOMMENDATIONS: Dict[str, str] = {
    "surface_crack": "CRITICAL: Surface crack detected on workpiece. Immediate spindle bearing raceway replacement required. Halt production on M104.",
    "spalling": "HIGH: Workpiece fatigue spalling detected. Schedule maintenance and roller assembly overhaul on machine M104.",
    "dent": "MEDIUM: Mechanical impact indentation observed. Inspect die alignment and stamping pressure calibration on machine M102.",
    "normal_surface": "NORMAL: Pristine surface finish. Workpiece meets quality control specifications.",
}


@dataclass
class DefectClassifierConfig:
    """Hyperparameters, dataset paths, and artifact destinations for ResNet Defect Classifier."""

    # Image geometry
    image_height: int = 128
    image_width: int = 128
    channels: int = 3
    num_classes: int = 4

    @property
    def input_shape(self) -> Tuple[int, int, int]:
        return (self.image_height, self.image_width, self.channels)

    # Architecture configuration: Compact ResNet-18
    # Stage channel widths: 32 -> 64 -> 128 -> 256
    # Exact parameter count: 2,804,708 (2,799,908 trainable)
    stage_channels: List[int] = field(default_factory=lambda: [32, 64, 128, 256])
    stage_blocks: List[int] = field(default_factory=lambda: [2, 2, 2, 2])
    stem_filters: int = 32
    dropout_rate: float = 0.35
    l2_reg: float = 1e-4
    bn_momentum: float = 0.85

    # Optimization & Regularization Hyperparameters
    learning_rate: float = 3e-4
    batch_size: int = 32
    epochs: int = 35
    label_smoothing: float = 0.05
    early_stopping_patience: int = 8
    reduce_lr_patience: int = 4
    reduce_lr_factor: float = 0.5
    min_lr: float = 1e-5
    random_seed: int = 42

    # Data Augmentation parameters (Training-only)
    enable_augmentation: bool = True
    rotation_factor: float = 15.0 / 360.0  # +/- 15 degrees
    brightness_factor: float = 0.08        # +/- 8%

    # Paths (relative to repository root)
    manifest_path: str = "data/defect_images/defect_manifest.json"
    images_dir: str = "data/defect_images"
    model_save_path: str = "ml/models_store/resnet_defect_classifier.keras"
    metadata_save_path: str = "ml/models_store/resnet_defect_classifier_metadata.json"
    results_save_path: str = "reports/phase2/defect_classifier/defect_classifier_results.json"
    predictions_save_path: str = "reports/phase2/defect_classifier/defect_predictions.csv"
    report_path: str = "reports/phase2/resnet_defect_classifier_report.md"
    graphs_dir: str = "reports/phase2/defect_classifier/graphs"

    def resolve_path(self, relative_path: str) -> str:
        """Resolve a path relative to the manumind-ai repository root."""
        # Find repository root
        current = os.path.abspath(os.path.dirname(__file__))
        while current and not os.path.exists(os.path.join(current, "data", "defect_images")):
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
        return os.path.normpath(os.path.join(current, relative_path))
